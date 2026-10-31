"""Scores how much the collected events threaten one user's location."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from .geo import Gazetteer, default_gazetteer, haversine_km
from .pipeline import Event

# How far (km) each event type's effects typically reach: supply chains,
# road closures, refugees, airspace. Used as the decay scale.
REACH_KM = {"protest": 15, "riot": 40, "terrorism": 40, "coup": 250, "armed_conflict": 150}
RECENCY_HOURS = 36  # older news counts less
# Even a severe, confirmed event in your own city disrupts daily life (food,
# water, transport) only part of the time; this caps one event's weight.
IMPACT_SCALE = 0.5
TOP_EVENTS = 5

# (upper score bound, key, Thai name, stockpile days, colour emoji)
LEVELS = [
    (0.20, "green", "ปกติ", 3, "🟢"),
    (0.45, "yellow", "เฝ้าระวัง", 7, "🟡"),
    (0.70, "orange", "เตรียมพร้อม", 14, "🟠"),
    (1.01, "red", "วิกฤต", 30, "🔴"),
]


@dataclass
class Threat:
    event: Event
    distance_km: float | None
    contribution: float


@dataclass
class Assessment:
    score: float
    level: str
    level_th: str
    emoji: str
    stockpile_days: int
    user_country: str | None
    threats: list[Threat]
    upcoming: list[Threat]

    def to_dict(self) -> dict:
        def t(x: Threat) -> dict:
            e = x.event
            return {"title": e.title, "type": e.label, "severity": round(e.severity, 1),
                    "place": e.place.name if e.place else None,
                    "distance_km": None if x.distance_km is None else round(x.distance_km),
                    "planned": e.planned, "sources": e.n_sources,
                    "contribution": round(x.contribution, 3), "url": e.urls[0] if e.urls else ""}
        return {"score": round(self.score, 3), "level": self.level, "level_th": self.level_th,
                "stockpile_days": self.stockpile_days,
                "user_country": self.user_country,
                "threats": [t(x) for x in self.threats], "upcoming": [t(x) for x in self.upcoming]}


def level_for(score: float) -> tuple:
    for bound, *rest in LEVELS:
        if score < bound:
            return rest
    return LEVELS[-1][1:]


def _proximity(event: Event, lat: float, lon: float, user_country: str | None) -> tuple[float, float | None]:
    if event.place is None:
        return 0.0, None
    p = event.place
    dist = haversine_km(lat, lon, p.lat, p.lon)
    same_country = user_country is not None and p.country == user_country
    if p.kind == "country" and same_country:
        # Only the country is named: it could be anywhere in it.
        prox = 0.8 if event.label == "coup" else 0.25
        return prox, None
    edge = max(0.0, dist - p.radius_km)  # inside the area -> 0
    prox = math.exp(-edge / REACH_KM[event.label])
    if same_country and event.label == "coup":
        prox = max(prox, 0.8)  # a coup affects the whole country
    elif same_country:
        prox = max(prox, 0.1)
    return prox, dist


def assess(events: list[Event], lat: float, lon: float, now: datetime | None = None,
           gazetteer: Gazetteer | None = None) -> Assessment:
    now = now or datetime.now(timezone.utc)
    gaz = gazetteer or default_gazetteer()
    country = gaz.country_of(lat, lon)
    threats = []
    for e in events:
        prox, dist = _proximity(e, lat, lon, country)
        age_h = max(0.0, (now - e.published).total_seconds() / 3600)
        recency = 1.0 if e.planned else math.exp(-age_h / RECENCY_HOURS)
        corroboration = min(1.0, 0.6 + 0.2 * e.n_sources)
        c = IMPACT_SCALE * (e.severity / 5) * prox * recency * e.confidence * corroboration
        threats.append(Threat(e, dist, c))
    threats.sort(key=lambda t: -t.contribution)
    # Combine only the strongest few events, so hundreds of far-away stories
    # can't add up to a crisis on their own.
    score = 1 - math.prod(1 - min(0.95, t.contribution) for t in threats[:TOP_EVENTS])
    key, name, days, emoji = level_for(score)
    upcoming = [t for t in threats if t.event.planned and t.contribution > 0.01]
    return Assessment(score, key, name, emoji, days, country,
                      [t for t in threats if t.contribution > 0.005], upcoming)
