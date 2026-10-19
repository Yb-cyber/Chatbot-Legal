"""Single owner of the LightRAG instance (OpenRouter-only).

Breaks the circular import between main.py <-> download_argentina_legal.py:
every module imports the instance from here instead of from main.
"""

import asyncio
import logging
import os
from typing import Optional

from lightrag import LightRAG
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

rag: Optional[LightRAG] = None


def get_config() -> dict:
    base_url = os.getenv("LLM_BASE_URL", os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))
    embed_base_url = os.getenv("EMBEDDING_BASE_URL", base_url)
    api_key = os.getenv("LLM_API_KEY", os.getenv("OPENROUTER_API_KEY", "ollama"))

    return {
        "working_dir": os.getenv("WORKING_DIR", "./rag_storage"),
        "base_url": base_url,
        "embed_base_url": embed_base_url,
        "llm_model": os.getenv("LLM_MODEL", "llama3.2:3b"),
        "embedding_model": os.getenv(
            "EMBEDDING_MODEL", "nomic-embed-text"
        ),
        "embedding_dim": int(os.getenv("EMBEDDING_DIM", "768")),
        "max_embed_tokens": int(os.getenv("MAX_EMBED_TOKENS", "8192")),
        "api_key": api_key,
    }


def _validate_key(api_key: str, base_url: str):
    # Si usamos un servidor local (Ollama, LM Studio, etc.), no se requiere API key
    if "localhost" in base_url or "127.0.0.1" in base_url:
        return

    if not api_key or api_key.strip() in (
        "",
        "your_openrouter_api_key_here",
        "sk-or-v1-...",
        "REPLACE_ME",
    ):
        raise RuntimeError(
            "API KEY no configurada. Si usas OpenRouter, consigue una en https://openrouter.ai/keys y ponla en .env"
        )


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc)
    return any(
        code in msg for code in ("429", "503", "504", "500", "UNAVAILABLE", "404")
    )


async def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
    """LLM completion compatible con OpenAI/Ollama/OpenRouter."""
    from rag_manager import get_config as _cfg

    cfg = _cfg()
    kwargs.pop("model", None)
    last_exc: Optional[Exception] = None
    for attempt in range(3):
        try:
            return await openai_complete_if_cache(
                cfg["llm_model"],
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                base_url=cfg["base_url"],
                api_key=cfg["api_key"],
                **kwargs,
            )
        except Exception as e:
            last_exc = e
            if "401" in str(e) or "invalid" in str(e).lower():
                raise
            if attempt < 2 and _is_retryable(e):
                wait = 2**attempt * 2
                logger.warning(
                    f"LLM attempt {attempt + 1}/3 failed ({e}). Retrying in {wait}s..."
                )
                await asyncio.sleep(wait)
                continue
            raise
    raise last_exc  # pragma: no cover


def build_embedding_func() -> EmbeddingFunc:
    cfg = get_config()
    is_local = "localhost" in cfg["embed_base_url"] or "127.0.0.1" in cfg["embed_base_url"]

    if is_local:
        from lightrag.llm.ollama import ollama_embed
        # Extraer host base eliminando /v1 si está presente
        host = cfg["embed_base_url"].replace("/v1", "")

        async def _embed(texts, **kwargs):
            return await ollama_embed.func(
                texts,
                embed_model=cfg["embedding_model"],
                host=host,
                embedding_dim=cfg["embedding_dim"],
                **kwargs,
            )

        return EmbeddingFunc(
            embedding_dim=cfg["embedding_dim"],
            max_token_size=cfg["max_embed_tokens"],
            func=_embed,
        )

    # Proveedor remoto OpenAI / OpenRouter
    async def _embed_remote(texts, **kwargs):
        return await openai_embed.func(
            texts,
            model=cfg["embedding_model"],
            base_url=cfg["embed_base_url"],
            api_key=cfg["api_key"],
            **kwargs,
        )

    return EmbeddingFunc(
        embedding_dim=cfg["embedding_dim"],
        max_token_size=cfg["max_embed_tokens"],
        func=_embed_remote,
    )


async def init_rag() -> LightRAG:
    global rag
    cfg = get_config()
    _validate_key(cfg["api_key"], cfg["base_url"])
    os.makedirs(cfg["working_dir"], exist_ok=True)

    rag = LightRAG(
        working_dir=cfg["working_dir"],
        llm_model_func=llm_model_func,
        embedding_func=build_embedding_func(),
    )
    await rag.initialize_storages()
    logger.info(
        f"RAG initialized: {cfg['llm_model']} + {cfg['embedding_model']} "
        f"(dim={cfg['embedding_dim']}) via {cfg['base_url']}"
    )
    return rag


async def close_rag():
    global rag
    if rag:
        await rag.finalize_storages()
        rag = None


def get_rag() -> Optional[LightRAG]:
    return rag
