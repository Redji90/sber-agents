"""LLM client for processing messages."""
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from openai import OpenAI
from bot.config import config
from bot.models import Transaction, TransactionType, TransactionCategory, TransactionFrequency

logger = logging.getLogger(__name__)


def normalize_category(category_str: str) -> TransactionCategory:
    """Normalize category string to TransactionCategory enum.
    
    Handles cases where model returns multiple categories separated by |,
    or variations in casing.
    """
    if not category_str:
        return TransactionCategory.OTHER
    
    # Handle multiple categories separated by |
    if "|" in category_str:
        # Take the first category if multiple are provided
        category_str = category_str.split("|")[0].strip()
    
    # Try to find matching category (case-insensitive)
    category_str_lower = category_str.lower()
    try:
        # First try direct match
        return TransactionCategory(category_str)
    except ValueError:
        # Try case-insensitive match
        for cat in TransactionCategory:
            if cat.value.lower() == category_str_lower:
                return cat
        # Default to "other" if no match found
        logger.warning(f"Unknown category '{category_str}', defaulting to 'other'")
        return TransactionCategory.OTHER


class LLMClient:
    """Client for LLM operations."""
    
    def __init__(self):
        provider = config.llm_provider
        model = config.llm_model
        api_key = config.llm_api_key
        base_url = config.llm_base_url
        
        if provider == "ollama":
            base_url = base_url or "http://localhost:11434/v1"
            api_key = "ollama"  # Ollama doesn't require real key
        
        # Set timeout for Ollama (longer for image processing)
        # Increased timeout and connection timeout for Ollama
        timeout = 300.0 if provider == "ollama" else 60.0
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url or "https://openrouter.ai/api/v1",
            timeout=timeout,
            max_retries=2,  # Reduce retries to fail faster
        )
        self.model = model
    
    async def extract_transaction(self, text: str) -> Optional[Transaction]:
        """Extract transaction from text using structured output."""
        
        schema = {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format. Use today's date if not specified."
                },
                "time": {
                    "type": "string",
                    "description": "Time in HH:MM:SS format. Use current time if not specified."
                },
                "type": {
                    "type": "string",
                    "enum": ["income", "expense"],
                    "description": "Transaction type: income or expense"
                },
                "amount": {
                    "type": "number",
                    "description": "Transaction amount as a number"
                },
                "category": {
                    "type": "string",
                    "enum": [
                        "food", "restaurants", "taxi", "education", "travel",
                        "utilities", "shopping", "entertainment", "health", "other",
                        "salary", "freelance", "investment", "gift"
                    ],
                    "description": "Transaction category"
                },
                "frequency": {
                    "type": "string",
                    "enum": ["daily", "periodic", "one_time"],
                    "description": "Transaction frequency type"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the transaction"
                }
            },
            "required": ["date", "time", "type", "amount", "category", "frequency", "description"]
        }
        
        now = datetime.now()
        
        prompt = f"""Extract financial transaction information from the following text (which may be from voice recognition, so it might have errors or be incomplete).

IMPORTANT: Try to extract transaction information even if the text is not perfect. Use your best judgment.

Rules:
- If amount is mentioned (even approximately), extract it
- If type is not clear, infer from context: spending money = "expense", receiving money = "income"
- If category is not specified, choose the most appropriate from the list based on keywords
- If date/time is missing, use today's date ({now.strftime('%Y-%m-%d')}) and current time ({now.strftime('%H:%M:%S')})
- If frequency is not mentioned, use "one_time"
- Always provide a description based on the text

Examples:
- "купил продукты на 500 рублей" → expense, amount: 500, category: food
- "заплатил за такси 300" → expense, amount: 300, category: taxi
- "получил зарплату 50000" → income, amount: 50000, category: salary
- "потратил 1000 на еду" → expense, amount: 1000, category: food

Text to analyze: {text}

Extract the transaction. If you can identify at least an amount and type (income/expense), return the data. Only return null if the text contains NO financial information at all."""

        try:
            # Run synchronous LLM call in thread to avoid blocking event loop
            def _call_llm():
                try:
                    return self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a financial transaction extractor. Extract transaction data from user messages."},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_schema", "json_schema": {"name": "transaction", "strict": True, "schema": schema}},
                        temperature=0.1,
                    )
                except Exception:
                    # Fallback for providers without structured output support
                    json_prompt = f"""{prompt}

Return the result as a JSON object with the following structure:
{{
  "date": "YYYY-MM-DD",
  "time": "HH:MM:SS",
  "type": "income" or "expense",
  "amount": <number>,
  "category": "one of: food, restaurants, taxi, education, travel, utilities, shopping, entertainment, health, other, salary, freelance, investment, gift",
  "frequency": "daily" or "periodic" or "one_time",
  "description": "<detailed description>"
}}

IMPORTANT: 
- The category must be a single value from the list above, not multiple values separated by |.
- Try to extract information even if text is incomplete or has recognition errors.
- If amount is mentioned (even approximately), extract it.
- If you can identify at least amount and type, return the data.

Return only valid JSON, no other text."""
                    return self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a financial transaction extractor. Always return valid JSON only."},
                            {"role": "user", "content": json_prompt}
                        ],
                        temperature=0.1,
                    )
            
            response = await asyncio.to_thread(_call_llm)
            
            content = response.choices[0].message.content.strip()
            logger.debug(f"LLM raw response: {content[:500]}")  # Log first 500 chars
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```", 2)[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from LLM response: {e}")
                logger.error(f"Response content: {content}")
                return None
            
            if result is None:
                logger.warning(f"LLM returned null for text: {text}")
                return None
            
            logger.info(f"Extracted transaction: type={result.get('type')}, amount={result.get('amount')}, category={result.get('category')}")
            
            return Transaction(
                date=result["date"],
                time=result["time"],
                type=TransactionType(result["type"]),
                amount=float(result["amount"]),
                category=normalize_category(result["category"]),
                frequency=TransactionFrequency(result["frequency"]),
                description=result["description"],
            )
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Check for timeout or connection errors
            is_timeout = "timeout" in error_msg.lower() or "timed out" in error_msg.lower() or "ConnectTimeout" in error_type
            is_connection_error = "connection" in error_msg.lower() or "connect" in error_msg.lower()
            
            if is_timeout or is_connection_error:
                logger.error(
                    f"Connection/timeout error extracting transaction from text '{text[:100]}': {error_msg}\n"
                    f"This usually means the LLM server (Ollama) is not accessible or not responding.\n"
                    f"Check if Ollama is running at {config.llm_base_url or 'http://localhost:11434/v1'}"
                )
            else:
                logger.error(f"Error extracting transaction from text '{text[:100]}': {e}", exc_info=True)
            return None


class VLMClient:
    """Client for Vision Language Model operations."""
    
    def __init__(self):
        provider = config.vlm_provider
        model = config.vlm_model
        api_key = config.vlm_api_key
        base_url = config.vlm_base_url
        
        if provider == "ollama":
            base_url = base_url or "http://localhost:11434/v1"
            api_key = "ollama"
        
        # Set timeout for Ollama
        timeout = 300.0 if provider == "ollama" else 60.0
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url or "https://openrouter.ai/api/v1",
            timeout=timeout,
        )
        self.model = model
        self.provider = provider
    
    async def extract_transaction_from_image(self, image_url: str = None, image_path: str = None, image_base64: str = None) -> Optional[Transaction]:
        """Extract transaction from receipt image."""
        
        schema = {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "time": {"type": "string", "description": "Time in HH:MM:SS format"},
                "type": {"type": "string", "enum": ["income", "expense"], "description": "Transaction type"},
                "amount": {"type": "number", "description": "Transaction amount"},
                "category": {
                    "type": "string",
                    "enum": [
                        "food", "restaurants", "taxi", "education", "travel",
                        "utilities", "shopping", "entertainment", "health", "other",
                        "salary", "freelance", "investment", "gift"
                    ],
                    "description": "Transaction category"
                },
                "frequency": {
                    "type": "string",
                    "enum": ["daily", "periodic", "one_time"],
                    "description": "Transaction frequency"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description extracted from receipt"
                }
            },
            "required": ["date", "time", "type", "amount", "category", "frequency", "description"]
        }
        
        now = datetime.now()
        
        prompt = f"""Analyze this receipt image and extract transaction information.
Use today's date ({now.strftime('%Y-%m-%d')}) and current time ({now.strftime('%H:%M:%S')}) if not visible on receipt.
Extract the total amount, items purchased, store name, and other relevant details."""

        try:
            json_prompt = f"""{prompt}

Return the result as a JSON object with the following structure:
{{
  "date": "YYYY-MM-DD",
  "time": "HH:MM:SS",
  "type": "income" or "expense",
  "amount": <number>,
  "category": "one of: food, restaurants, taxi, education, travel, utilities, shopping, entertainment, health, other, salary, freelance, investment, gift",
  "frequency": "daily" or "periodic" or "one_time",
  "description": "<detailed description>"
}}

IMPORTANT: The category must be a single value from the list above, not multiple values separated by |.

Return only valid JSON, no other text."""
            
            # Prepare image content based on provider
            import base64
            if self.provider == "ollama":
                # Ollama requires base64 or local file
                if image_base64:
                    image_data = image_base64
                elif image_path:
                    with open(image_path, "rb") as img_file:
                        image_data = base64.b64encode(img_file.read()).decode("utf-8")
                elif image_url:
                    # Download and convert to base64
                    import requests
                    response = requests.get(image_url)
                    image_data = base64.b64encode(response.content).decode("utf-8")
                else:
                    raise ValueError("No image source provided")
                
                image_content = f"data:image/jpeg;base64,{image_data}"
            else:
                # OpenAI/OpenRouter format
                if image_url:
                    image_content = {"type": "image_url", "image_url": {"url": image_url}}
                elif image_base64:
                    image_content = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                elif image_path:
                    with open(image_path, "rb") as img_file:
                        img_b64 = base64.b64encode(img_file.read()).decode("utf-8")
                    image_content = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                else:
                    raise ValueError("No image source provided")
            
            # Run synchronous VLM call in thread to avoid blocking event loop
            def _call_vlm():
                if self.provider == "ollama":
                    # Ollama uses different format - use fallback directly
                    logger.info(f"Sending image to Ollama model {self.model}, image size: {len(image_content)} chars")
                    content_list = [{"type": "text", "text": json_prompt}, {"type": "image_url", "image_url": {"url": image_content}}]
                    
                    try:
                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are a financial transaction extractor. Always return valid JSON only."
                                },
                                {
                                    "role": "user",
                                    "content": content_list
                                }
                            ],
                            temperature=0.1,
                        )
                        logger.info(f"Got response from Ollama, length: {len(response.choices[0].message.content)}")
                        return response
                    except Exception as e:
                        logger.error(f"Ollama API error: {e}", exc_info=True)
                        raise
                else:
                    # Try structured output first for other providers
                    try:
                        content_list = [{"type": "text", "text": prompt}, image_content]
                        
                        return self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {
                                    "role": "user",
                                    "content": content_list
                                }
                            ],
                            response_format={"type": "json_schema", "json_schema": {"name": "transaction", "strict": True, "schema": schema}},
                            temperature=0.1,
                        )
                    except Exception:
                        # Fallback for providers without structured output support
                        content_list = [{"type": "text", "text": json_prompt}, image_content]
                        
                        return self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are a financial transaction extractor. Always return valid JSON only."
                                },
                                {
                                    "role": "user",
                                    "content": content_list
                                }
                            ],
                            temperature=0.1,
                        )
            
            response = await asyncio.to_thread(_call_vlm)
            
            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```", 2)[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            result = json.loads(content)
            if result is None:
                return None
            
            return Transaction(
                date=result["date"],
                time=result["time"],
                type=TransactionType(result["type"]),
                amount=float(result["amount"]),
                category=normalize_category(result["category"]),
                frequency=TransactionFrequency(result["frequency"]),
                description=result["description"],
            )
        except Exception as e:
            logger.error(f"Error extracting transaction from image: {e}", exc_info=True)
            return None

