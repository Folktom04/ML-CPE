"""Turns raw articles into deduplicated, located, scored events."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .collector import Article
from .geo import Gazetteer, Place, default_gazetteer
from .model import UnrestClassifier

SAME_EVENT_SIMILARITY = 0.35


@dataclass
class Event:
    title: str
    label: str
    confidence: float
    severity: float
    planned: bool
    place: Place | None
    published: datetime
    sources: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    headlines: list[str] = field(default_factory=list)

    @property
    def n_sources(self) -> int:
        return len(set(self.sources)) or 1


def _cluster(titles: list[str], places: list[Place | None],
             labels: list[str]) -> list[list[int]]:
    """Group headlines about the same story.

    Same place + same event type = one situation (this also joins Thai and
    English reports of it). Otherwise headlines must be very similar.
    """
    if len(titles) < 2:
        return [[i] for i in range(len(titles))]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
    sim = cosine_similarity(vec.fit_transform(titles))
    groups: list[list[int]] = []
    assigned = [False] * len(titles)
    for i in range(len(titles)):
        if assigned[i]:
            continue
        group = [i]
        assigned[i] = True
        for j in range(i + 1, len(titles)):
            if assigned[j]:
                continue
            same_place = places[i] is not None and places[i] == places[j]
            if (same_place and labels[i] == labels[j]) or sim[i, j] >= SAME_EVENT_SIMILARITY + 0.25:
                group.append(j)
                assigned[j] = True
        groups.append(group)
    return groups


def build_events(articles: list[Article], model: UnrestClassifier | None = None,
                 gazetteer: Gazetteer | None = None) -> tuple[list[Event], int]:
    """Returns (events, number_of_articles_filtered_out_as_noise)."""
    model = model or UnrestClassifier().fit()
    gaz = gazetteer or default_gazetteer()
    preds = model.predict([a.title for a in articles])
    kept = [(a, p) for a, p in zip(articles, preds) if p.relevant]
    dropped = len(articles) - len(kept)
    places = [gaz.locate(a.title) for a, _ in kept]
    events = []
    for group in _cluster([a.title for a, _ in kept], places, [p.label for _, p in kept]):
        members = [kept[i] for i in group]
        lead_a, lead_p = max(members, key=lambda m: (m[1].severity, m[1].confidence))
        place = next((places[i] for i in group if places[i] is not None), None)
        events.append(Event(
            title=lead_a.title,
            label=lead_p.label,
            confidence=max(p.confidence for _, p in members),
            severity=max(p.severity for _, p in members),
            planned=sum(p.planned for _, p in members) * 2 > len(members),  # most reports say it's upcoming
            place=place,
            published=max(a.published for a, _ in members),
            sources=[a.source for a, _ in members],
            urls=[a.url for a, _ in members],
            headlines=[a.title for a, _ in members],
        ))
    events.sort(key=lambda e: (-e.severity, -e.n_sources))
    return events, dropped
