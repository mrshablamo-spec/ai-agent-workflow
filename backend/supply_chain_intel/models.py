from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class FilingMetadata:
    ticker: str
    company_name: str
    cik: str
    accession_number: str
    filing_date: str
    primary_document: str
    filing_url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SupplierSignal:
    supplier: str
    relationship: str
    evidence: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GeographySignal:
    geography: str
    context: str
    mention_count: int
    risk_score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RiskSignal:
    title: str
    category: str
    severity: float
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NewsSignal:
    title: str
    source: str
    published: str
    link: str
    summary: str
    matched_entities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
