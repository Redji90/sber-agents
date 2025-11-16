"""Построение RAG-цепочки на базе LangChain."""
from __future__ import annotations

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnablePassthrough, RunnableParallel
from langchain_openai import ChatOpenAI

from src.app import config

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


def build_rag_chain(retriever: BaseRetriever) -> Runnable:
    """Строит RAG-цепочку с явным возвратом документов через RunnablePassthrough."""
    llm = ChatOpenAI(
        model=config.LLM_MODEL,
        temperature=0.2,
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL,
        max_retries=20,  # Увеличено для более агрессивной обработки rate limits
        timeout=120.0,  # Увеличен таймаут до 120 секунд для retry
    )

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
    chain = (
        RunnablePassthrough.assign(context=history_aware_retriever)
        | RunnableParallel(
            answer=question_answer_chain,
            context=lambda x: x.get("context", []),
        )
    )

    return chain

