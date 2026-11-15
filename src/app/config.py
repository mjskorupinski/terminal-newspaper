from pathlib import Path
from dataclasses import dataclass
from urllib.parse import urlparse

from src.utils import load_json_list, save_json_list

import json

SETTINGS_DIR = Path("settings")
SOURCES_FILE = SETTINGS_DIR / "sources.json"
TOPICS_FILE = SETTINGS_DIR / "topics.json"

@dataclass(frozen=True)
class SourceEntry:
    name: str
    url: str

class AppConfig:
    def __init__(self, sources_path: Path = SOURCES_FILE, 
                 topics_path: Path = TOPICS_FILE) -> None:
        self._sources_path = sources_path
        self._topics_path = topics_path
        self.sources: list[SourceEntry] = self._load_sources()
        self.topics: list[str] = load_json_list(self._topics_path, "topics")

    @property
    def source_urls(self) -> list[str]:
        return [s.url for s in self.sources]

    def has_source_url(self, url: str) -> bool:
        return any(s.url == url for s in self.sources)

    def add_source(self, name: str, url: str) -> None:
        self.sources.append(SourceEntry(name=name, url=url))
        self._save_sources()

    def remove_source(self, url: str) -> None:
        self.sources = [s for s in self.sources if s.url != url]
        self._save_sources()

    def add_topic(self, topic: str) -> None:
        self.topics.append(topic)
        save_json_list(self.topics, self._topics_path, "topics")

    def remove_topic(self, topic: str) -> None:
        self.topics.remove(topic)
        save_json_list(self.topics, self._topics_path, "topics")

    def _load_sources(self) -> list[SourceEntry]:
        if not self._sources_path.exists():
            self._sources_path.parent.mkdir(parents=True, exist_ok=True)
            with self._sources_path.open("w", encoding="utf-8") as f:
                json.dump({"sources": []}, f, indent=2, ensure_ascii=False)
            return []

        with self._sources_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        entries: list[SourceEntry] = []
        for item in data.get("sources", []):
            if isinstance(item, dict) and "url" in item:
                name = item.get("name") or self._default_name_from_url(item["url"])
                entries.append(SourceEntry(name=name, url=item["url"]))
            elif isinstance(item, str):
                entries.append(SourceEntry(name=self._default_name_from_url(item), url=item))
        return entries

    def _save_sources(self) -> None:
        self._sources_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"sources": [asdict(s) for s in self.sources]}
        with self._sources_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _default_name_from_url(url: str) -> str:
        return urlparse(url).netloc.removeprefix("www.") or url