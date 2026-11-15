import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app.config import SourceEntry
    from src.core.article import Article
    from src.core.newspaper import TerminalNewspaper


class NewspaperEngine:
    def __init__(self) -> None:
        self._instance: TerminalNewspaper | None = None

    @property
    def is_initialized(self) -> bool:
        return self._instance is not None

    @property
    def article_count(self) -> int:
        return self._instance.articles_count if self._instance is not None else 0

    def reset(self) -> None:
        self._instance = None

    def _build(self, sources: list["SourceEntry"]) -> "TerminalNewspaper":
        from src.core.article import RSSSource
        from src.core.newspaper import TerminalNewspaper

        return TerminalNewspaper([RSSSource(name=s.name, rss_url=s.url) for s in sources])

    async def initialize(self, sources: list["SourceEntry"]) -> "TerminalNewspaper":
        if self._instance is None:
            self._instance = await asyncio.to_thread(self._build, sources)
        return self._instance

    async def prepare_news(self, sources: list["SourceEntry"]) -> None:
        newspaper = await self.initialize(sources)
        await newspaper.prepare_news()

    async def search(self, sources: list["SourceEntry"], topic: str, limit: int = 25) -> list["Article | str"]:
        newspaper = await self.initialize(sources)
        raw = await newspaper.get_articles_for(topic, limit)
        return [art for art in (raw or []) if art is not None]

    async def get_all_articles(self, sources: list["SourceEntry"]) -> list["Article"]:
        newspaper = await self.initialize(sources)
        return newspaper.get_all_articles()

    async def get_articles_by_source(self, sources: list["SourceEntry"], source_name: str) -> list["Article"]:
        newspaper = await self.initialize(sources)
        return newspaper.get_articles_by_source(source_name)