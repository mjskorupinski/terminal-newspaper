from src.core.article import Source, Article
from src.core.storage import ArticleStorage
from src.core.article import ArticleProvider
from src.core.nlp import CustomAzureOpenAI

DEFAULT_EMBEDDINGS_MODELS = 'text-embedding-3-small'

class TerminalNewspaper:
    def __init__(self, sources: list[Source]):
        self._model_provider = CustomAzureOpenAI()

        self._article_provider = ArticleProvider(sources)
        self._storage = ArticleStorage(
            self._model_provider.get_embeddings(DEFAULT_EMBEDDINGS_MODELS)
        )

    @property
    def articles_count(self):
        return self._storage.articles_count

    def get_all_articles(self) -> list[Article]:
        return self._storage.get_all_articles()

    def get_articles_by_source(self, source_name: str) -> list[Article]:
        return self._storage.get_articles_by_source(source_name)

    async def prepare_news(self) -> None:
        articles = await self._article_provider.fetch_articles()
        await self._storage.store_articles(articles)

    async def get_articles_for(self, search_phrase: str, n: int) -> list[Article]:
        return await self._storage.search_by_topic(search_phrase, n)

