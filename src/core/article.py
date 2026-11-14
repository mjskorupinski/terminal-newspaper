import asyncio

from src.logger import get_logger

from abc import ABC
from datetime import datetime
from dateutil import parser as date_parser

from pydantic import BaseModel

import feedparser
import trafilatura
import httpx
import asyncio

LOGGER = get_logger('article_provider', stdout=False)

class Article(BaseModel):
    title: str
    url: str
    publish_date: datetime | None
    content: str

class Source(ABC):
    pass

class RSSSource(Source):
    def __init__(self, rss_url: str, max_concurrent = 10):
        self.rss_url = rss_url
        self.semaphore = asyncio.Semaphore(max_concurrent)

    def _parse_date(self, entry):
        date = getattr(entry, "published", getattr(entry, "updated", None))
        if date:
            try:
                parsed_date = date_parser.parse(date)
            except Exception:
                parsed_date = None
        return parsed_date

    async def _fetch_article(self, client: httpx.AsyncClient, entry) -> Article | None:
        async with self.semaphore:
            try:
                response = await client.get(entry.link, follow_redirects=True, timeout=10.0)
                if response.status_code != 200:
                    return None

                content = trafilatura.extract(
                    response.text,
                    include_comments=False,
                    include_tables=True
                )
                if not content:
                    return None

                parsed_date = self._parse_date(entry)

                return Article(
                    title=entry.title,
                    url=entry.link,
                    publish_date=parsed_date,
                    content=content
                )
            except Exception as e:
                LOGGER.error(f"Error fetching {entry.link}: {e}")
                return None

    async def fetch_articles(self) -> list[Article]:
        feed = feedparser.parse(self.rss_url)
        
        async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}) as client:
            tasks = [self._fetch_article(client, entry) for entry in feed.entries]
            results = await asyncio.gather(*tasks)

        return [article for article in results if article is not None]

class ArticleProvider:
    def __init__(self, sources: list[Source]):
        self._sources = sources

    async def fetch_articles(self) -> list[Article]:
        source_tasks = [source.fetch_articles() for source in self._sources]
        results = await asyncio.gather(*source_tasks, return_exceptions=True)

        all_articles: list[Article] = []
        for result in results:
            if isinstance(result, Exception):
               LOGGER.error(f'Error occured while fetching articles: {result}')
            else:
                all_articles.extend(result)

        return all_articles