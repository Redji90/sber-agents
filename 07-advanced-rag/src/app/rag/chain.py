"""Построение RAG-цепочки на базе LangChain."""
from __future__ import annotations

import logging

# Импорт для LangChain 1.0+ - функции из langchain-classic
try:
    # Попытка импорта из langchain.chains (для старых версий)
    from langchain.chains.combine_documents import create_stuff_documents_chain
    from langchain.chains.history_aware_retriever import create_history_aware_retriever
except ImportError:
    # Для LangChain 1.0+ используем langchain_classic
    from langchain_classic.chains.combine_documents import create_stuff_documents_chain
    from langchain_classic.chains.history_aware_retriever import create_history_aware_retriever
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnablePassthrough, RunnableParallel, RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from src.app import config
from src.app.rag.retrieval import BM25Retriever, HybridRetriever, Reranker

logger = logging.getLogger(__name__)

CONTEXTUALIZE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Ты помощник, который переписывает пользовательский запрос так, "
            "чтобы он был самодостаточным. Используй историю диалога только "
            "для уточнения смысла вопроса.",
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ]
)

QA_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", config.SYSTEM_ROLE + "\nИспользуй предоставленный контекст для ответа."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "Контекст:\n{context}\n\nВопрос:\n{input}"),
        (
            "assistant",
            "Если контекст не содержит ответа, скажи об этом. "
            "В конце перечисли использованные источники в виде списка.",
        ),
    ]
)


class RerankingRetriever(BaseRetriever):
    """Обёртка retriever'а с поддержкой reranking."""

    def __init__(self, retriever: BaseRetriever, reranker: Reranker, k: int = 4):
        """Инициализирует RerankingRetriever.

        Args:
            retriever: Базовый retriever для получения документов
            reranker: Reranker для улучшения порядка документов
            k: Количество документов после reranking
        """
        super().__init__()
        self._retriever = retriever
        self._reranker = reranker
        self._k = k

    def _get_relevant_documents(self, query: str) -> list[Document]:
        """Возвращает релевантные документы с применением reranking.

        Args:
            query: Поисковый запрос

        Returns:
            Список документов после reranking
        """
        # Получаем документы от базового retriever'а
        documents = self._retriever.get_relevant_documents(query)

        # Применяем reranking
        reranked_docs = self._reranker.rerank(query, documents, top_k=self._k)

        return reranked_docs

    async def _aget_relevant_documents(self, query: str) -> list[Document]:
        """Асинхронная версия _get_relevant_documents."""
        # Получаем документы от базового retriever'а
        documents = await self._retriever.aget_relevant_documents(query)

        # Применяем reranking (синхронный метод)
        reranked_docs = self._reranker.rerank(query, documents, top_k=self._k)

        return reranked_docs


def create_retriever_for_mode(
    semantic_retriever: BaseRetriever,
    documents: list[Document] | None = None,
) -> BaseRetriever:
    """Создаёт retriever в зависимости от режима RAG_MODE.

    Args:
        semantic_retriever: Semantic retriever (InMemoryVectorStore retriever)
        documents: Список документов для BM25 индексации (нужен для hybrid режимов)

    Returns:
        Retriever в соответствии с режимом RAG_MODE
    """
    mode = config.RAG_MODE

    if mode == "semantic":
        # Просто возвращаем semantic retriever
        return semantic_retriever

    elif mode == "hybrid":
        # Создаём Hybrid retriever (semantic + BM25)
        if documents is None:
            raise ValueError(
                "Для hybrid режима нужны документы для BM25 индексации. "
                "Убедитесь, что индекс загружен (запустите /index)."
            )

        # Используем переданный semantic_retriever, но создаём новый с правильным k
        # если он был создан с другим k
        if hasattr(semantic_retriever, 'search_kwargs') and semantic_retriever.search_kwargs.get('k') != config.SEMANTIC_K:
            from src.app.indexing.vector_store import get_vector_store_manager
            manager = get_vector_store_manager()
            semantic_retriever = manager.get_retriever(k=config.SEMANTIC_K)
        elif not hasattr(semantic_retriever, 'search_kwargs'):
            # Если нет search_kwargs, создаём новый с правильным k
            from src.app.indexing.vector_store import get_vector_store_manager
            manager = get_vector_store_manager()
            semantic_retriever = manager.get_retriever(k=config.SEMANTIC_K)

        bm25_retriever = BM25Retriever(documents, k=config.BM25_K)
        hybrid_retriever = HybridRetriever(
            semantic_retriever=semantic_retriever,
            bm25_retriever=bm25_retriever,
            k=config.HYBRID_K,
        )
        return hybrid_retriever

    elif mode == "hybrid+reranker":
        # Создаём Hybrid retriever с reranking
        if documents is None:
            raise ValueError(
                "Для hybrid+reranker режима нужны документы для BM25 индексации. "
                "Убедитесь, что индекс загружен (запустите /index)."
            )

        # Используем переданный semantic_retriever, но создаём новый с правильным k
        if hasattr(semantic_retriever, 'search_kwargs') and semantic_retriever.search_kwargs.get('k') != config.SEMANTIC_K:
            from src.app.indexing.vector_store import get_vector_store_manager
            manager = get_vector_store_manager()
            semantic_retriever = manager.get_retriever(k=config.SEMANTIC_K)
        elif not hasattr(semantic_retriever, 'search_kwargs'):
            from src.app.indexing.vector_store import get_vector_store_manager
            manager = get_vector_store_manager()
            semantic_retriever = manager.get_retriever(k=config.SEMANTIC_K)

        bm25_retriever = BM25Retriever(documents, k=config.BM25_K)
        hybrid_retriever = HybridRetriever(
            semantic_retriever=semantic_retriever,
            bm25_retriever=bm25_retriever,
            k=config.HYBRID_K,
        )
        # Оборачиваем в RerankingRetriever
        reranker = Reranker()
        reranking_retriever = RerankingRetriever(
            retriever=hybrid_retriever,
            reranker=reranker,
            k=config.RERANKER_K,
        )
        return reranking_retriever

    else:
        raise ValueError(f"Недопустимый режим RAG: {mode}")


def _get_llm() -> BaseChatModel:
    """Возвращает LLM в зависимости от провайдера."""
    provider = config.LLM_PROVIDER.lower()
    
    if provider == "gigachat":
        from langchain_community.llms import GigaChat
        from langchain_core.language_models.chat_models import BaseChatModel
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        from langchain_core.outputs import ChatGeneration, ChatResult
        from typing import List, Any
        
        # Создаем обертку для GigaChat, чтобы использовать его как ChatModel
        class GigaChatChatModel(BaseChatModel):
            """Обертка для GigaChat, чтобы использовать его как ChatModel."""
            
            def __init__(self, credentials: str, verify_ssl_certs: bool = False, **kwargs):
                super().__init__(**kwargs)
                self.giga = GigaChat(credentials=credentials, verify_ssl_certs=verify_ssl_certs)
            
            def _generate(self, messages: List[Any], stop: List[str] | None = None, **kwargs) -> ChatResult:
                # Преобразуем сообщения LangChain в формат для GigaChat
                # messages - это список BaseMessage объектов
                text_parts = []
                for msg in messages:
                    msg_type = msg.__class__.__name__
                    if msg_type == "SystemMessage":
                        text_parts.append(f"Система: {msg.content}")
                    elif msg_type == "HumanMessage":
                        text_parts.append(f"Пользователь: {msg.content}")
                    elif msg_type == "AIMessage":
                        text_parts.append(f"Ассистент: {msg.content}")
                    else:
                        # Fallback для других типов сообщений
                        if hasattr(msg, 'content'):
                            text_parts.append(str(msg.content))
                        else:
                            text_parts.append(str(msg))
                
                # Объединяем все сообщения в один промпт
                prompt = "\n".join(text_parts)
                
                # Вызываем GigaChat
                response = self.giga.invoke(prompt)
                
                # Возвращаем результат в формате ChatResult
                return ChatResult(
                    generations=[ChatGeneration(message=AIMessage(content=response))]
                )
            
            async def _agenerate(self, messages: List[Any], stop: List[str] | None = None, **kwargs) -> ChatResult:
                # Асинхронная версия - используем синхронный вызов в executor
                import asyncio
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self._generate, messages, stop)
            
            @property
            def _llm_type(self) -> str:
                return "gigachat"
        
        llm = GigaChatChatModel(
            credentials=config.OPENAI_API_KEY,
            verify_ssl_certs=False,
        )
        logger.info("Используется GigaChat LLM")
        return llm
    else:
        # OpenAI-совместимый API (OpenAI, Groq, OpenRouter, etc.)
        llm = ChatOpenAI(
            model=config.LLM_MODEL,
            temperature=0.2,
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
            max_retries=3,  # Умеренное количество retry (больше retry при 429 только усугубляет ситуацию)
            timeout=60.0,  # Разумный таймаут
        )
        logger.info("Используется OpenAI-совместимый LLM: %s (base_url: %s)", config.LLM_MODEL, config.OPENAI_BASE_URL)
        return llm


def build_rag_chain(retriever: BaseRetriever) -> Runnable:
    """Строит RAG-цепочку с явным возвратом документов через RunnablePassthrough.

    Args:
        retriever: Retriever для получения документов (может быть semantic/hybrid/hybrid+reranker)

    Returns:
        RAG цепочка в LCEL стиле с поддержкой трансформации запроса на основе истории
    """
    # Получаем LLM в зависимости от провайдера
    llm = _get_llm()

    # Создаём history-aware retriever для трансформации запроса на основе истории
    parameters = create_history_aware_retriever.__code__.co_varnames
    kwargs = {"llm": llm, "retriever": retriever}
    if "contextualize_prompt" in parameters:
        kwargs["contextualize_prompt"] = CONTEXTUALIZE_PROMPT
    elif "contextual_prompt" in parameters:
        kwargs["contextual_prompt"] = CONTEXTUALIZE_PROMPT
    elif "prompt" in parameters:
        kwargs["prompt"] = CONTEXTUALIZE_PROMPT
    else:
        raise RuntimeError("Unsupported LangChain version: no prompt argument for create_history_aware_retriever")

    history_aware_retriever = create_history_aware_retriever(**kwargs)

    question_answer_chain = create_stuff_documents_chain(
        llm=llm,
        prompt=QA_PROMPT,
    )

    # Используем RunnablePassthrough для явного сохранения документов
    # и RunnableParallel для параллельного выполнения генерации ответа и извлечения документов
    # Сохраняем функциональность трансформации запроса на основе истории переписки
    chain = (
        RunnablePassthrough.assign(context=history_aware_retriever)
        | RunnableParallel(
            answer=question_answer_chain,
            context=lambda x: x.get("context", []),
        )
    )

    logger.debug("RAG цепочка построена для режима: %s", config.RAG_MODE)

    return chain

