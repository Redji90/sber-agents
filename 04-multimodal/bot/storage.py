"""Storage for transactions."""
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from bot.models import Transaction


class Storage:
    """Simple storage for transactions."""
    
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save_transactions([])
    
    def _load_transactions(self) -> List[dict]:
        """Load transactions from file."""
        if not self.path.exists():
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _save_transactions(self, transactions: List[dict]):
        """Save transactions to file."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(transactions, f, ensure_ascii=False, indent=2)
    
    def add_transaction(self, transaction: Transaction):
        """Add a new transaction."""
        transactions = self._load_transactions()
        transactions.append(transaction.to_dict())
        self._save_transactions(transactions)
    
    def get_transactions(self) -> List[Transaction]:
        """Get all transactions."""
        data = self._load_transactions()
        return [Transaction.from_dict(t) for t in data]
    
    def get_balance(self) -> float:
        """Calculate current balance."""
        transactions = self.get_transactions()
        balance = 0.0
        for t in transactions:
            if t.type.value == "income":
                balance += t.amount
            else:
                balance -= t.amount
        return balance

