from app.core.config import settings
from langchain_openai import OpenAIEmbeddings
from langchain_ollama import OllamaEmbeddings
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from functools import lru_cache
from threading import Lock


_model_lock = Lock()


@lru_cache(maxsize=1)
def _huggingface_model(model_name, token):
    return HuggingFaceEmbeddings(model_name=model_name, model_kwargs={"token": token} if token else {})


class EmbeddingsFactory:
    @staticmethod
    def create():
        """
        Factory method to create an embeddings instance based on .env config.
        """
        embeddings_provider = settings.EMBEDDINGS_PROVIDER.lower()

        if embeddings_provider == "openai":
            return OpenAIEmbeddings(
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                model=settings.OPENAI_EMBEDDINGS_MODEL
            )
        elif embeddings_provider == "dashscope":
            return DashScopeEmbeddings(
                model=settings.DASH_SCOPE_EMBEDDINGS_MODEL,
                dashscope_api_key=settings.DASH_SCOPE_API_KEY
            )
        elif embeddings_provider == "ollama":
            return OllamaEmbeddings(
                model=settings.OLLAMA_EMBEDDINGS_MODEL,
                base_url=settings.OLLAMA_API_BASE
            )
        elif embeddings_provider == "huggingface":
            # Reuse one local model per worker; serialize cold starts so concurrent
            # uploads/searches cannot download and load duplicate copies.
            with _model_lock:
                return _huggingface_model(settings.HUGGINGFACE_EMBEDDINGS_MODEL, settings.HUGGINGFACE_API_KEY)
        else:
            raise ValueError(f"Unsupported embeddings provider: {embeddings_provider}")
