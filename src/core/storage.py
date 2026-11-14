import json
from datetime import date, datetime
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.core.article import Article

CHROMA_DIR = Path("./db")
DEFAULT_MAX_DISTANCE = 0.76 


class ArticleStorage:
    def __init__(self, embeddings: Embeddings, persist_dir: Path = CHROMA_DIR, 
                 max_distance: float = DEFAULT_MAX_DISTANCE) -> None:
        self._embeddings = embeddings
        self._persist_dir = persist_dir
        self._cache_path = self._persist_dir / "articles_cache.json"
        self._max_distance = max_distance

        self._persist_dir.mkdir(parents=True, exist_ok=True)

        self.vector_store = self._create_vector_store()
        self._articles: dict[str, Article] = {}
        self._sync_with_today()

    def _create_vector_store(self) -> Chroma:
        return Chroma(
            collection_name="articles",
            embedding_function=self._embeddings,
            persist_directory=str(self._persist_dir),
            collection_metadata={"hnsw:space": "cosine"},
        )

    @property
    def articles_count(self) -> int:
        return len(self._articles)

    @staticmethod
    def _today_str() -> str:
        return date.today().isoformat()

    def _reset_database(self) -> None:
        """Deletes and recreates the collection so hnsw:space='cosine' is preserved."""
        try:
            self.vector_store.delete_collection()
        except Exception:
            pass
        self.vector_store = self._create_vector_store()
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
        """Embeds Title + Lead as primary topic vector, plus 1 coarse body window for long articles."""
        metadata = {
            "title": article.title,
            "url": article.url,
        }
        clean_text = article.content.strip()

        documents = [
            Document(
                page_content=f"{article.title}\n\n{clean_text[:1500]}",
                metadata=metadata,
            )
        ]

        if len(clean_text) > 1800:
            documents.append(
                Document(
                    page_content=f"{article.title}\n\n{clean_text[1300:4000]}",
                    metadata=metadata,
                )
            )

        return documents

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

    async def search_by_topic(
        self,
        topic_phrase: str,
        k: int = 10,
        max_distance: float | None = None,
    ) -> list[Article]:
        self._sync_with_today()

        if not self._articles:
            return []

        cutoff = max_distance if max_distance is not None else self._max_distance

        scored_chunks = await self.vector_store.asimilarity_search_with_score(
            topic_phrase,
            k=min(k * 3, len(self._articles) * 2),
        )

        best_distances: dict[str, float] = {}
        for chunk, distance in scored_chunks:
            url = chunk.metadata.get("url")
            if not url or url not in self._articles:
                continue
            if distance <= cutoff and distance < best_distances.get(url, float("inf")):
                best_distances[url] = distance

        ranked_urls = sorted(best_distances, key=best_distances.get)[:k]
        return [self._articles[url] for url in ranked_urls]