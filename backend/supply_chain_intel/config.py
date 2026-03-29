from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    sec_contact_email: str = os.getenv("SEC_CONTACT_EMAIL", "research@example.com")
    sec_contact_name: str = os.getenv("SEC_CONTACT_NAME", "MiniPalantirResearchBot")
    sec_rate_limit_per_second: float = float(os.getenv("SEC_RATE_LIMIT_PER_SECOND", "2.0"))
    cache_dir: Path = Path(os.getenv("SUPPLY_CHAIN_CACHE_DIR", Path(__file__).resolve().parents[2] / ".cache" / "supply_chain"))
    max_news_items: int = int(os.getenv("MAX_NEWS_ITEMS", "8"))

    @property
    def sec_user_agent(self) -> str:
        return f"{self.sec_contact_name} {self.sec_contact_email}"


settings = Settings()
settings.cache_dir.mkdir(parents=True, exist_ok=True)
