import json
from datetime import date, datetime
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.article import Article

CHROMA_DIR = Path("./db")

class ArticleStorage:
    def __init__(self, embeddings: Embeddings, persist_dir: Path = CHROMA_DIR) -> None:
        self._embeddings = embeddings
        self._persist_dir = persist_dir
        self._cache_path = self._persist_dir / "articles_cache.json"

        self._persist_dir.mkdir(parents=True, exist_ok=True)

        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
        )
        self.vector_store = Chroma(
            collection_name="articles",
            embedding_function=self._embeddings,
            persist_directory=str(self._persist_dir),
        )

        self._articles: dict[str, Article] = {}
        self._sync_with_today()

    @property
    def articles_count(self) -> int:
        return len(self._articles)

    @staticmethod
    def _today_str() -> str:
        return date.today().isoformat()

    def _reset_database(self) -> None:
        self.vector_store.reset_collection()
        self._articles.clear()
        self._write_cache({})

    def _sync_with_today(self) -> None:
        if not self._cache_path.exists():
            self._reset_database()
            return

        with self._cache_path.open("r", encoding="utf-8") as f:
            payload: dict = json.load(f)

        if payload.get("date") != self._today_str():
            self._reset_database()
            return

        raw_articles: dict[str, dict] = payload.get("articles", {})
        self._articles = {
            url: Article(
                title=entry["title"],
                url=url,
                content=entry["content"],
                publish_date=(
                    datetime.fromisoformat(entry["publish_date"])
                    if entry.get("publish_date")
                    else None
                ),
            )
            for url, entry in raw_articles.items()
        }

    def _write_cache(self, articles_payload: dict[str, dict]) -> None:
        payload = {
            "date": self._today_str(),
            "articles": articles_payload,
        }
        with self._cache_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def _save_articles(self, articles: list[Article]) -> None:
        self._articles |= {a.url: a for a in articles}

        serialized = {
            url: {
                "title": art.title,
                "content": art.content,
                "publish_date": art.publish_date.isoformat() if art.publish_date else None,
            }
            for url, art in self._articles.items()
        }
        self._write_cache(serialized)

    def _chunk_article(self, article: Article) -> list[Document]:
        metadata = {
            "title": article.title,
            "url": article.url,
        }
        chunks = self._text_splitter.split_text(article.content)
        return [Document(page_content=chunk, metadata=metadata) for chunk in chunks]

    async def store_articles(self, articles: list[Article]) -> None:
        self._sync_with_today()

        new_articles = [a for a in articles if a.url not in self._articles]
        if not new_articles:
            return

        self._save_articles(new_articles)

        documents: list[Document] = []
        for article in new_articles:
            documents.extend(self._chunk_article(article))

        if documents:
            await self.vector_store.aadd_documents(documents)

    async def search_by_topic(self, topic_phrase: str, k: int = 5) -> list[Article]:
        self._sync_with_today()

        if not self._articles:
            return []

        matched_chunks = await self.vector_store.asimilarity_search(topic_phrase, k=k)

        urls = list(
            dict.fromkeys(
                chunk.metadata["url"]
                for chunk in matched_chunks
                if chunk.metadata.get("url")
            )
        )

        return [self._articles[url] for url in urls if url in self._articles]