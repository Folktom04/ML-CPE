"""Small async SNMP client (GET + bulk WALK) on top of pysnmp 7, plus a mock client.

Values are converted to plain Python: OctetString -> bytes, integers/counters/ticks
-> int, OIDs and IP addresses -> str, "no such object / end of MIB" -> None.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "discovery.json"


class SnmpError(RuntimeError):
    pass


class SnmpTimeout(SnmpError):
    """No answer: host down, SNMP not enabled, wrong community/credentials, or blocked by ACL."""


@dataclass
class SnmpCredentials:
    version: str = "2c"                 # "2c" or "3"
    community: str | None = None
    user: str | None = None
    auth_key: str | None = None
    priv_key: str | None = None
    auth_proto: str = "SHA"
    priv_proto: str = "AES"
    port: int = 161
    timeout: float = 2.0
    retries: int = 1

    def describe(self) -> str:
        if self.version == "3":
            level = "authPriv" if self.priv_key else ("authNoPriv" if self.auth_key else "noAuthNoPriv")
            return f"SNMPv3 user={self.user} {level} {self.auth_proto}/{self.priv_proto if self.priv_key else '-'}"
        return "SNMPv2c"


def _convert(value: Any) -> Any:
    name = type(value).__name__
    if name == "ObjectIdentity":          # MIB-resolved OID -> numeric dotted string
        return str(value.getOid())
    if name in ("NoSuchObject", "NoSuchInstance", "EndOfMibView", "Null"):
        return None
    if name == "OctetString" or name in ("Opaque", "Bits"):
        return bytes(value.asOctets())
    if name in ("ObjectIdentifier", "ObjectName"):
        return str(value)
    if name == "IpAddress":
        return ".".join(str(b) for b in value.asOctets())
    try:
        return int(value)
    except (TypeError, ValueError):
        return value.prettyPrint()


class PysnmpClient:
    """One instance is shared by all concurrent queries (one SNMP engine)."""

    AUTH = {"MD5": "usmHMACMD5AuthProtocol", "SHA": "usmHMACSHAAuthProtocol",
            "SHA224": "usmHMAC128SHA224AuthProtocol", "SHA256": "usmHMAC192SHA256AuthProtocol",
            "SHA384": "usmHMAC256SHA384AuthProtocol", "SHA512": "usmHMAC384SHA512AuthProtocol"}
    PRIV = {"DES": "usmDESPrivProtocol", "AES": "usmAesCfb128Protocol", "AES128": "usmAesCfb128Protocol",
            "AES192": "usmAesCfb192Protocol", "AES256": "usmAesCfb256Protocol"}

    def __init__(self, creds: SnmpCredentials):
        try:
            from pysnmp.hlapi.v3arch import asyncio as hl
        except ImportError as exc:
            raise SnmpError("pysnmp is not installed: pip install pysnmp") from exc
        self.hl = hl
        self.creds = creds
        self.engine = hl.SnmpEngine()
        if creds.version == "3":
            if not creds.user:
                raise SnmpError("SNMPv3 needs a user name")
            auth_name = self.AUTH.get(creds.auth_proto.upper())
            priv_name = self.PRIV.get(creds.priv_proto.upper())
            if creds.auth_key and not auth_name:
                raise SnmpError(f"unknown auth protocol {creds.auth_proto} (use {', '.join(self.AUTH)})")
            if creds.priv_key and not priv_name:
                raise SnmpError(f"unknown privacy protocol {creds.priv_proto} (use {', '.join(self.PRIV)})")
            kwargs: dict[str, Any] = {}
            if creds.auth_key:
                kwargs.update(authKey=creds.auth_key, authProtocol=getattr(hl, auth_name))
            if creds.priv_key:
                kwargs.update(privKey=creds.priv_key, privProtocol=getattr(hl, priv_name))
            self.auth = hl.UsmUserData(creds.user, **kwargs)
        else:
            if not creds.community:
                raise SnmpError("SNMPv2c needs a community string")
            self.auth = hl.CommunityData(creds.community, mpModel=1)

    async def _target(self, host: str):
        return await self.hl.UdpTransportTarget.create((host, self.creds.port), timeout=self.creds.timeout,
                                                       retries=self.creds.retries)

    @staticmethod
    def _raise(host: str, error_indication: Any, error_status: Any) -> None:
        if error_indication:
            text = str(error_indication)
            if "timeout" in text.lower() or "no snmp response" in text.lower():
                raise SnmpTimeout(f"{host}: no SNMP response")
            raise SnmpError(f"{host}: {text}")
        if error_status:
            raise SnmpError(f"{host}: {error_status.prettyPrint()}")

    async def get(self, host: str, oids: list[str]) -> dict[str, Any]:
        hl = self.hl
        objs = [hl.ObjectType(hl.ObjectIdentity(o)) for o in oids]
        ei, es, _idx, var_binds = await hl.get_cmd(self.engine, self.auth, await self._target(host),
                                                    hl.ContextData(), *objs, lookupMib=False)
        self._raise(host, ei, es)
        return {str(name): _convert(val) for name, val in var_binds}

    async def walk(self, host: str, oid: str, max_rows: int = 5000) -> list[tuple[str, Any]]:
        hl = self.hl
        rows: list[tuple[str, Any]] = []
        prefix = oid + "."
        async for ei, es, _idx, var_binds in hl.bulk_walk_cmd(
                self.engine, self.auth, await self._target(host), hl.ContextData(), 0, 25,
                hl.ObjectType(hl.ObjectIdentity(oid)), lexicographicMode=False, lookupMib=False):
            self._raise(host, ei, es)
            for name, val in var_binds:
                name = str(name)
                if not name.startswith(prefix):
                    return rows
                converted = _convert(val)
                if converted is not None:
                    rows.append((name, converted))
            if len(rows) >= max_rows:
                break
        return rows

    def close(self) -> None:
        try:
            self.engine.close_dispatcher()
        except Exception:
            pass


def _decode_fixture_value(value: Any) -> Any:
    if isinstance(value, str):
        if value.startswith("hex:"):
            return bytes.fromhex(value[4:])
        if value.startswith("oid:"):
            return value[4:]
        return value.encode()
    return value


class MockSnmpClient:
    """Answers from fixtures/discovery.json: hosts not listed behave like 'no SNMP response'."""

    def __init__(self, creds: SnmpCredentials | None = None, path: Path = FIXTURE):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.agents = data.get("agents", {})
        self.ping_alive = set(data.get("ping_alive", []))
        self.local_neighbors = data.get("local_neighbors", [])

    def _agent(self, host: str) -> dict[str, Any]:
        agent = self.agents.get(host)
        if agent is None:
            raise SnmpTimeout(f"{host}: no SNMP response")
        if "same_as" in agent:            # same device answering on another IP (e.g. an SVI)
            agent = self.agents[agent["same_as"]]
        if "error" in agent:
            raise SnmpError(f"{host}: {agent['error']}")
        return agent

    async def get(self, host: str, oids: list[str]) -> dict[str, Any]:
        values = self._agent(host).get("get", {})
        return {o: _decode_fixture_value(values[o]) if o in values else None for o in oids}

    async def walk(self, host: str, oid: str, max_rows: int = 5000) -> list[tuple[str, Any]]:
        agent = self._agent(host)
        walks = agent.get("walk", {})
        rows = [(o, _decode_fixture_value(v)) for o, v in walks.get(oid, [])]
        if not rows:   # allow walking a whole table whose columns are stored separately
            prefix = oid + "."
            for base, items in walks.items():
                if base.startswith(prefix) or base == oid:
                    rows += [(o, _decode_fixture_value(v)) for o, v in items]
        return rows[:max_rows]

    def close(self) -> None:
        return None
