import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def open_deposit(amount: float, rate: float, term_months: int, client_name: str) -> str:
    """
    Локальный инструмент для открытия вклада (критичная операция с HITL).

    Выполняет простой расчет дохода по вкладу и возвращает детали вклада.
    """
    try:
        if amount < 1000:
            return "Минимальная сумма вклада — 1 000 ₽."

        # Простой процент без капитализации
        income = amount * (rate / 100.0) * (term_months / 12.0)
        total = amount + income

        # Генерируем mock-номер вклада
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        deposit_number = f"40817 810 0 {timestamp[-4:]} {timestamp[:7]}"

        result = (
            "✅ **Вклад успешно открыт!**\n\n"
            "📋 **Детали вклада:**\n"
            f"   Владелец: {client_name}\n"
            f"   Номер вклада: {deposit_number}\n"
            f"   Сумма: {amount:,.2f} ₽\n"
            f"   Срок: {term_months} мес.\n"
            f"   Ставка: {rate:.2f}% годовых\n"
            f"   Ориентировочный доход: {income:,.2f} ₽\n"
            f"   Итоговая сумма к концу срока: {total:,.2f} ₽\n"
            "   Статус: Активен\n\n"
            "ℹ️ Точные условия и график начисления процентов указаны в договоре вклада.\n"
        )

        logger.info(
            f"open_deposit tool called locally: amount={amount}, rate={rate}, "
            f"term_months={term_months}, client={client_name}"
        )
        return result
    except Exception as e:
        logger.error(f"Error in open_deposit: {e}", exc_info=True)
        return "Не удалось открыть вклад из-за внутренней ошибки. Попробуйте позже."



