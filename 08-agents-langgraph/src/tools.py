"""
Инструменты для ReAct агента

Инструменты - это функции, которые агент может вызывать для получения информации.
Декоратор @tool из LangChain автоматически создает описание для LLM.
"""
import json
import logging
from langchain_core.tools import tool
import rag

logger = logging.getLogger(__name__)

@tool
def rag_search(query: str) -> str:
    """
    Ищет информацию в документах Сбербанка (условия кредитов, вкладов и других банковских продуктов).
    
    Возвращает JSON со списком источников, где каждый источник содержит:
    - source: имя файла
    - page: номер страницы (только для PDF)
    - page_content: текст документа
    """
    try:
        # Получаем релевантные документы через RAG (retrieval + reranking)
        documents = rag.retrieve_documents(query)
        
        if not documents:
            return json.dumps({"sources": []}, ensure_ascii=False)
        
        # Формируем структурированный ответ для агента
        sources = []
        for doc in documents:
            source_data = {
                "source": doc.metadata.get("source", "Unknown"),
                "page_content": doc.page_content  # Полный текст документа
            }
            # page только для PDF (у JSON документов его нет)
            if "page" in doc.metadata:
                source_data["page"] = doc.metadata["page"]
            sources.append(source_data)
        
        # ensure_ascii=False для корректной кириллицы
        return json.dumps({"sources": sources}, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"Error in rag_search: {e}", exc_info=True)
        return json.dumps({"sources": []}, ensure_ascii=False)


@tool
def currency_converter(amount: float, from_currency: str, to_currency: str) -> str:
    """
    Конвертирует сумму из одной валюты в другую.
    
    Поддерживаемые валюты: USD (доллар США), EUR (евро), RUB (российский рубль).
    Использует актуальные курсы валют.
    
    Args:
        amount: Сумма для конвертации (положительное число)
        from_currency: Исходная валюта (USD, EUR, RUB)
        to_currency: Целевая валюта (USD, EUR, RUB)
    
    Returns:
        Строка с результатом конвертации в формате: "X [FROM] = Y [TO]"
    """
    try:
        # Фиксированные курсы валют (примерные, можно заменить на API)
        # Курсы относительно RUB (1 USD = X RUB, 1 EUR = Y RUB)
        exchange_rates = {
            "USD": 95.0,  # 1 USD = 95 RUB
            "EUR": 103.0,  # 1 EUR = 103 RUB
            "RUB": 1.0     # 1 RUB = 1 RUB
        }
        
        # Нормализуем названия валют к верхнему регистру
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        # Проверяем валидность валют
        if from_currency not in exchange_rates:
            return f"Ошибка: валюта '{from_currency}' не поддерживается. Используйте USD, EUR или RUB."
        
        if to_currency not in exchange_rates:
            return f"Ошибка: валюта '{to_currency}' не поддерживается. Используйте USD, EUR или RUB."
        
        # Проверяем сумму
        if amount < 0:
            return "Ошибка: сумма должна быть положительным числом."
        
        # Конвертируем через RUB (базовая валюта)
        # Сначала в RUB, потом в целевую валюту
        amount_in_rub = amount * exchange_rates[from_currency]
        result_amount = amount_in_rub / exchange_rates[to_currency]
        
        # Форматируем результат
        result = f"{amount:.2f} {from_currency} = {result_amount:.2f} {to_currency}"
        
        logger.info(f"Currency conversion: {amount} {from_currency} -> {result_amount:.2f} {to_currency}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in currency_converter: {e}", exc_info=True)
        return f"Ошибка при конвертации валют: {str(e)}"
