"""Data models for transactions."""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Literal
from enum import Enum


class TransactionType(str, Enum):
    """Transaction type."""
    INCOME = "income"
    EXPENSE = "expense"


class TransactionCategory(str, Enum):
    """Transaction categories."""
    # Expenses
    FOOD = "food"
    RESTAURANTS = "restaurants"
    TAXI = "taxi"
    EDUCATION = "education"
    TRAVEL = "travel"
    UTILITIES = "utilities"
    SHOPPING = "shopping"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    OTHER = "other"
    # Income
    SALARY = "salary"
    FREELANCE = "freelance"
    INVESTMENT = "investment"
    GIFT = "gift"


class TransactionFrequency(str, Enum):
    """Transaction frequency type."""
    DAILY = "daily"
    PERIODIC = "periodic"
    ONE_TIME = "one_time"


@dataclass
class Transaction:
    """Transaction data model."""
    date: str  # YYYY-MM-DD
    time: str  # HH:MM:SS
    type: TransactionType
    amount: float
    category: TransactionCategory
    frequency: TransactionFrequency
    description: str
    
    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        """Create transaction from dictionary."""
        return cls(
            date=data["date"],
            time=data["time"],
            type=TransactionType(data["type"]),
            amount=float(data["amount"]),
            category=TransactionCategory(data["category"]),
            frequency=TransactionFrequency(data["frequency"]),
            description=data["description"],
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

