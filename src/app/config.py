from pathlib import Path
from src.utils import load_json_list, save_json_list

SETTINGS_DIR = Path("settings")
SOURCES_FILE = SETTINGS_DIR / "sources.json"
TOPICS_FILE = SETTINGS_DIR / "topics.json"

class AppConfig:
    def __init__(self, sources_path: Path = SOURCES_FILE, 
                 topics_path: Path = TOPICS_FILE) -> None:
        self._sources_path = sources_path
        self._topics_path = topics_path
        self.sources: list[str] = load_json_list(self._sources_path, "sources")
        self.topics: list[str] = load_json_list(self._topics_path, "topics")

    def add_source(self, url: str) -> None:
        self.sources.append(url)
        save_json_list(self.sources, self._sources_path, "sources")

    def remove_source(self, url: str) -> None:
        self.sources.remove(url)
        save_json_list(self.sources, self._sources_path, "sources")

    def add_topic(self, topic: str) -> None:
        self.topics.append(topic)
        save_json_list(self.topics, self._topics_path, "topics")

    def remove_topic(self, topic: str) -> None:
        self.topics.remove(topic)
        save_json_list(self.topics, self._topics_path, "topics")