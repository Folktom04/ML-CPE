"""Simulated SNMP agents (v2c + v3 authPriv) built on the pysnmp command responder.

One SNMP engine per lab IP address; each answers GET / GETNEXT / GETBULK from the
device's OID table, so real SNMP tools (netcollect discover, snmpwalk, PRTG, Zabbix,
LibreNMS ...) can query the lab like real devices.
"""
from __future__ import annotations

import bisect
from typing import Any

from .model import Lab, LabDevice


def _value(v2c: Any, kind: str, value: Any) -> Any:
    if kind == "str":
        return v2c.OctetString(str(value).encode("utf-8"))
    if kind == "bytes":
        return v2c.OctetString(value)
    if kind == "int":
        return v2c.Integer(int(value))
    if kind == "ticks":
        return v2c.TimeTicks(int(value))
    if kind == "oid":
        return v2c.ObjectIdentifier(tuple(int(x) for x in str(value).split(".")))
    raise ValueError(kind)


def _controller(device: LabDevice):
    from pysnmp.proto.api import v2c
    from pysnmp.smi import instrum

    data = {o: _value(v2c, k, v) for o, (k, v) in device.snmp.items()}
    keys = sorted(data)

    class Controller(instrum.AbstractMibInstrumController):
        def read_variables(self, *var_binds, **context):
            return [(o, data.get(tuple(o), v2c.NoSuchObject())) for o, _ in var_binds]

        def read_next_variables(self, *var_binds, **context):
            out = []
            for o, _ in var_binds:
                i = bisect.bisect_right(keys, tuple(o))
                if i < len(keys):
                    out.append((v2c.ObjectIdentifier(keys[i]), data[keys[i]]))
                else:
                    out.append((o, v2c.EndOfMibView()))
            return out

    return Controller()


def start_snmp_agents(lab: Lab) -> list[Any]:
    """Start one agent per address on the running asyncio loop. Returns the engines."""
    from pysnmp.carrier.asyncio.dgram import udp
    from pysnmp.entity import config, engine
    from pysnmp.entity.rfc3413 import cmdrsp, context
    from pysnmp.proto.api import v2c

    s = lab.settings.get("snmp", {}) or {}
    port = int(s.get("port", 1161))
    engines = []
    for device in lab.devices:
        if not device.runs_snmp:
            continue
        for ip in [device.ip, *device.extra_ips]:
            e = engine.SnmpEngine()
            config.add_transport(e, udp.DOMAIN_NAME, udp.UdpAsyncioTransport().open_server_mode((ip, port)))
            config.add_v1_system(e, "lab-area", s.get("community", "lab-community"))
            config.add_vacm_user(e, 2, "lab-area", "noAuthNoPriv", (1,), ())
            config.add_v3_user(e, s.get("v3_user", "labuser"),
                               config.USM_AUTH_HMAC96_SHA, s.get("v3_auth_pass", "lab-auth-pass"),
                               config.USM_PRIV_CFB128_AES, s.get("v3_priv_pass", "lab-priv-pass"))
            config.add_vacm_user(e, 3, s.get("v3_user", "labuser"), "authPriv", (1,), ())
            ctx = context.SnmpContext(e)
            ctx.unregister_context_name(v2c.OctetString(""))
            ctx.register_context_name(v2c.OctetString(""), _controller(device))
            cmdrsp.GetCommandResponder(e, ctx)
            cmdrsp.NextCommandResponder(e, ctx)
            cmdrsp.BulkCommandResponder(e, ctx)
            engines.append(e)
    return engines


def stop_snmp_agents(engines: list[Any]) -> None:
    for e in engines:
        try:
            e.close_dispatcher()
        except Exception:
            pass
