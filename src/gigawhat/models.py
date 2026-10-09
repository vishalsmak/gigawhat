"""Model choices per profile. Everything that depends on which model runs reads from here."""

from dataclasses import dataclass

from langchain_cohere import CohereEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings

from gigawhat.config import Profile, Settings

# Chunk boundaries come from one tokenizer so both profiles split documents identically.
CHUNK_TOKENIZER = "Qwen/Qwen3-Embedding-0.6B"
CHUNK_MAX_TOKENS = 512


@dataclass(frozen=True)
class EmbeddingModel:
    name: str
    dimensions: int


EMBEDDING_MODELS = {
    Profile.CLOUD: EmbeddingModel("embed-v4.0", 1536),
    Profile.OFFLINE: EmbeddingModel("qwen3-embedding:0.6b", 1024),
}


def embedding_model(settings: Settings) -> EmbeddingModel:
    return EMBEDDING_MODELS[settings.profile]


def create_embeddings(settings: Settings) -> Embeddings:
    model = embedding_model(settings)
    if settings.profile is Profile.OFFLINE:
        return OllamaEmbeddings(model=model.name, base_url=settings.ollama_url)
    # client and async_client are built by CohereEmbeddings' own validator.
    return CohereEmbeddings(  # type: ignore[call-arg]
        model=model.name, cohere_api_key=settings.cohere_api_key
    )
