from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.embeddings import Embeddings

from abc import ABC, abstractmethod
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class ModelProvider(ABC):

    @abstractmethod
    def get_embeddings(self, model: str) -> Embeddings:
        pass 

class AzureOpenAIConfig(BaseSettings):
    api_key: SecretStr
    api_url: str
    api_version: str

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

class AzureOpenAI(ModelProvider):
    def __init__(self, config: AzureOpenAIConfig = AzureOpenAIConfig()):
        self._config = config

    def get_embeddings(self, embedding_model: str) -> AzureOpenAIEmbeddings:
        return AzureOpenAIEmbeddings(
            model=embedding_model,
            openai_api_key=self._config.api_key, 
            azure_endpoint=self._config.api_url,
            api_version=self._config.api_version
        )    

class CustomAzureOpenAI(AzureOpenAI):

    def get_embeddings(self, embedding_model: str) -> AzureOpenAIEmbeddings:
        return AzureOpenAIEmbeddings(
            model=embedding_model,
            openai_api_key=self._config.api_key, 
            azure_endpoint=f'{self._config.api_url}/{embedding_model}',
            api_version=self._config.api_version
        )    