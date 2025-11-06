"""Main bot application."""
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import config
from bot.llm_client import LLMClient, VLMClient
from bot.storage import Storage
from bot.models import Transaction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

storage = Storage(config.storage_path)
llm_client = LLMClient()
vlm_client = VLMClient()


async def safe_edit_text(message, text: str, max_retries: int = 2):
    """Безопасное редактирование текста сообщения с обработкой ошибок сети."""
    from aiogram.exceptions import TelegramNetworkError
    
    for attempt in range(max_retries):
        try:
            await message.edit_text(text)
            return True
        except TelegramNetworkError as e:
            logger.warning(f"Network error editing message (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)  # Короткая пауза перед повтором
            else:
                logger.error(f"Failed to edit message after {max_retries} attempts")
                # Пробуем отправить новое сообщение вместо редактирования
                try:
                    # Используем bot для отправки нового сообщения в тот же чат
                    await bot.send_message(message.chat.id, text)
                    return True
                except Exception as send_error:
                    logger.error(f"Failed to send new message: {send_error}")
                    return False
        except Exception as e:
            logger.error(f"Unexpected error editing message: {e}")
            return False
    return False


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Start command handler."""
    await message.answer(
        "Привет! Я твой персональный финансовый советник.\n\n"
        "Я могу:\n"
        "• Записывать твои доходы и расходы из сообщений\n"
        "• Обрабатывать голосовые сообщения\n"
        "• Анализировать фотографии чеков\n"
        "• Показывать баланс (/balance)\n\n"
        "Просто отправь мне сообщение о транзакции!"
    )


@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    """Show balance command handler."""
    balance = storage.get_balance()
    transactions = storage.get_transactions()
    
    income = sum(t.amount for t in transactions if t.type.value == "income")
    expense = sum(t.amount for t in transactions if t.type.value == "expense")
    
    response = (
        f"💰 <b>Текущий баланс:</b> {balance:,.2f} ₽\n\n"
        f"📈 Доходы: {income:,.2f} ₽\n"
        f"📉 Расходы: {expense:,.2f} ₽\n"
        f"📊 Всего транзакций: {len(transactions)}"
    )
    await message.answer(response)


@dp.message(F.voice | F.audio)
async def handle_voice(message: Message):
    """Handle voice messages."""
    status_msg = await message.answer("🎤 Обрабатываю голосовое сообщение...")
    
    try:
        # Download voice file
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        # Download to local temp file
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
            await bot.download_file(file_path, tmp.name)
            temp_path = tmp.name
        
        try:
            # Transcribe audio
            await safe_edit_text(status_msg, "🔊 Распознаю речь...")
            transcript = await transcribe_audio(temp_path)
            
            if transcript:
                logger.info(f"Transcription result: {transcript}")
                await safe_edit_text(status_msg, f"✅ Распознано: {transcript}\n\n📝 Извлекаю информацию о транзакции...")
                
                # Extract transaction from transcript
                transaction = await llm_client.extract_transaction(transcript)
                if transaction:
                    storage.add_transaction(transaction)
                    await safe_edit_text(
                        status_msg,
                        f"✅ Транзакция добавлена:\n"
                        f"📅 {transaction.date} {transaction.time}\n"
                        f"{'💰 Доход' if transaction.type.value == 'income' else '💸 Расход'}: {transaction.amount:,.2f} ₽\n"
                        f"📂 Категория: {transaction.category.value}\n"
                        f"📝 {transaction.description}"
                    )
                else:
                    # Проверяем, была ли ошибка подключения к LLM
                    error_hint = ""
                    # Попробуем определить причину по логам (это будет видно в логах)
                    # Но для пользователя дадим общий совет
                    error_hint = (
                        "\n\n💡 <b>Возможные причины:</b>\n"
                        "• Сервер LLM (Ollama) недоступен или не отвечает\n"
                        "• Текст не содержит достаточно информации о транзакции\n"
                        "• Попробуйте указать сумму, тип (доход/расход) и категорию более явно\n\n"
                        "Примеры:\n"
                        "• \"купил продукты на 500 рублей\"\n"
                        "• \"получил зарплату 50000\"\n"
                        "• \"потратил 300 на такси\""
                    )
                    
                    await safe_edit_text(
                        status_msg,
                        f"✅ Распознано: {transcript}\n\n"
                        "⚠️ Не удалось извлечь информацию о транзакции из сообщения."
                        + error_hint
                    )
            else:
                # Проверяем, какой провайдер используется
                provider_hint = ""
                if config.speech_provider == "openai":
                    base_url = config.speech_base_url or config.llm_base_url or ""
                    if "ollama" in base_url.lower() or "11434" in base_url:
                        provider_hint = (
                            "\n\n💡 <b>Совет:</b> Похоже, что Ollama не поддерживает Whisper API должным образом.\n"
                            "Попробуйте использовать:\n"
                            "• <b>Vosk</b> (бесплатно, офлайн) - см. VOSK_SETUP.md\n"
                            "• <b>Yandex SpeechKit</b> (платно) - см. SPEECHKIT_SETUP.md"
                        )
                    else:
                        provider_hint = (
                            "\n\n💡 <b>Совет:</b> Проблемы с подключением к OpenAI API.\n"
                            "Попробуйте:\n"
                            "• <b>Vosk</b> (бесплатно, офлайн) - см. VOSK_SETUP.md\n"
                            "• <b>Yandex SpeechKit</b> - см. SPEECHKIT_SETUP.md"
                        )
                elif config.speech_provider == "vosk":
                    provider_hint = (
                        "\n\n💡 <b>Совет:</b> Проблемы с Vosk.\n"
                        "Проверьте:\n"
                        "• Правильность пути к модели (model_path)\n"
                        "• Установлен ли FFmpeg\n"
                        "• См. инструкцию: VOSK_SETUP.md"
                    )
                
                await safe_edit_text(
                    status_msg,
                    "❌ Не удалось распознать голосовое сообщение.\n\n"
                    "Возможные причины:\n"
                    "• Плохое качество аудио\n"
                    "• Не настроен API для транскрибации\n"
                    "• Проблемы с подключением к сервису"
                    + provider_hint
                )
        finally:
            os.unlink(temp_path)
    except ValueError as e:
        # Configuration errors
        error_msg = str(e)
        logger.error(f"Configuration error: {error_msg}")
        await safe_edit_text(
            status_msg,
            f"❌ Ошибка конфигурации:\n{error_msg}\n\n"
            "Пожалуйста, настройте API для транскрибации в config.yaml или .env файле.\n"
            "См. инструкцию: SPEECHKIT_SETUP.md"
        )
    except Exception as e:
        logger.error(f"Error processing voice: {e}", exc_info=True)
        error_text = f"❌ Произошла ошибка при обработке голосового сообщения:\n{str(e)}\n\nПроверьте логи для подробностей."
        # Если не удалось отредактировать сообщение, пробуем отправить новое
        if not await safe_edit_text(status_msg, error_text):
            try:
                await message.answer(error_text)
            except Exception as send_error:
                logger.error(f"Failed to send error message to user: {send_error}")


async def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio using configured provider (Yandex SpeechKit, OpenAI Whisper, Vosk, etc.)."""
    try:
        if config.speech_provider == "yandex":
            return await transcribe_yandex(audio_path)
        elif config.speech_provider == "openai":
            return await transcribe_openai(audio_path)
        elif config.speech_provider == "vosk":
            return await transcribe_vosk(audio_path)
        else:
            # Fallback to OpenAI if provider not specified
            logger.warning(f"Unknown speech provider: {config.speech_provider}, using OpenAI")
            return await transcribe_openai(audio_path)
    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)
        return None


async def transcribe_yandex(audio_path: str) -> str:
    """Transcribe audio using Yandex SpeechKit."""
    import requests
    
    if not config.speech_api_key:
        raise ValueError("Yandex SpeechKit requires API key. Please configure in config.yaml or .env")
    
    # Проверяем и очищаем API-ключ от пробелов
    api_key = config.speech_api_key.strip()
    if not api_key:
        raise ValueError("API key is empty after trimming whitespace")
    
    # Логируем начало и конец ключа для отладки (безопасно)
    logger.info(f"Using API key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '****'} (length: {len(api_key)})")
    
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    
    headers = {
        "Authorization": f"Api-Key {api_key}",
    }
    
    # При использовании сервисного аккаунта НЕ указываем folderId в запросе
    # SpeechKit автоматически использует каталог, в котором был создан сервисный аккаунт
    params = {
        "lang": config.speech_language,
        "format": "oggopus",  # Telegram voice messages are in OGG Opus format
    }
    
    # Если folderId указан, не добавляем его в параметры (это может вызвать ошибку 401)
    # Удаляем эту строку, так как при использовании сервисного аккаунта folderId не нужен
    
    with open(audio_path, "rb") as audio_file:
        response = requests.post(url, headers=headers, params=params, data=audio_file, timeout=30)
    
    if response.status_code != 200:
        error_msg = response.text
        logger.error(f"Yandex SpeechKit error: {response.status_code} - {error_msg}")
        
        # Provide helpful error messages
        if response.status_code == 401:
            error_detail = ""
            try:
                error_json = response.json()
                error_code = error_json.get("error_code", "")
                error_message = error_json.get("error_message", "")
                if "PermissionDenied" in error_message or error_code == "UNAUTHORIZED":
                    error_detail = (
                        "\n\nВозможные причины:\n"
                        "• API-ключ создан не для сервисного аккаунта с ролью ai.speechkit-stt.user\n"
                        "• Роль ai.speechkit-stt.user не назначена на каталог (folder)\n"
                        "• Folder ID указан неправильно\n"
                        "• API-ключ устарел или недействителен\n\n"
                        "См. инструкцию: SPEECHKIT_SETUP.md (раздел 'Устранение проблем')"
                    )
            except:
                pass
            raise Exception(f"Yandex SpeechKit API error: 401 (Unauthorized){error_detail}")
        elif response.status_code == 403:
            raise Exception(
                f"Yandex SpeechKit API error: 403 (Forbidden)\n\n"
                "Проверьте, что сервисный аккаунт имеет роль ai.speechkit-stt.user "
                "и что Folder ID указан правильно.\n"
                "См. инструкцию: SPEECHKIT_SETUP.md"
            )
        else:
            raise Exception(f"Yandex SpeechKit API error: {response.status_code} - {error_msg}")
    
    result = response.json()
    
    if "result" in result:
        return result["result"]
    else:
        error_msg = result.get("error_message", "Unknown error")
        logger.error(f"Yandex SpeechKit recognition error: {error_msg}")
        raise Exception(f"Recognition error: {error_msg}")


async def transcribe_openai(audio_path: str) -> str:
    """Transcribe audio using OpenAI Whisper API (or compatible API like Ollama)."""
    from openai import OpenAI as OpenAIClient
    import os
    
    # Используем настройки из speech секции, если указаны, иначе из llm секции
    api_key = config.speech_api_key or config.llm_api_key or "dummy"
    base_url = config.speech_base_url or config.llm_base_url or "https://api.openai.com/v1"
    
    # Get file size for logging
    file_size = os.path.getsize(audio_path)
    logger.info(f"Using OpenAI Whisper API: base_url={base_url}, language={config.speech_language}, file_size={file_size} bytes")
    
    # Create client with increased timeout
    # Note: We handle retries manually, so set max_retries to 0 to avoid double retries
    transcription_client = OpenAIClient(
        api_key=api_key,
        base_url=base_url,
        timeout=120.0,  # 2 minutes timeout for large files
        max_retries=0,  # We handle retries manually in the loop below
    )
    
    # Определяем язык для распознавания
    language = None
    if config.speech_language and config.speech_language != "auto":
        # Преобразуем ru-RU в ru, en-US в en и т.д.
        lang_code = config.speech_language.split("-")[0] if "-" in config.speech_language else config.speech_language
        language = lang_code if lang_code != "auto" else None
    
    # Retry logic with exponential backoff
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            with open(audio_path, "rb") as audio_file:
                transcription_params = {
                    "model": "whisper-1",
                    "file": audio_file,
                }
                if language:
                    transcription_params["language"] = language
                
                logger.info(f"Transcription attempt {attempt + 1}/{max_attempts}")
                response = transcription_client.audio.transcriptions.create(**transcription_params)
                
                return response.text
                
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.warning(f"Transcription attempt {attempt + 1} failed: {error_type}: {error_msg}")
            
            # Проверяем, является ли это ошибкой подключения, которая вряд ли исправится
            is_connection_error = (
                "Connection error" in error_msg or 
                "disconnected" in error_msg.lower() or
                "RemoteProtocolError" in error_type
            )
            
            # Если это ошибка подключения и это не последняя попытка, пробуем еще раз
            # Но если это явно проблема сервера (disconnected), не тратим время на ожидание
            if is_connection_error and attempt < max_attempts - 1:
                # Для ошибок подключения делаем короткую паузу
                wait_time = 0.5  # Короткая пауза для ошибок подключения
                logger.info(f"Connection error detected, retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            elif attempt < max_attempts - 1:
                # Для других ошибок используем экспоненциальную задержку
                wait_time = (2 ** attempt) * 1.0  # 1s, 2s, 4s
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                # Последняя попытка - пробрасываем ошибку
                logger.error(f"All {max_attempts} transcription attempts failed. Last error: {error_type}: {error_msg}")
                raise
    
    # Should not reach here, but just in case
    raise Exception("Transcription failed after all retry attempts")


async def transcribe_vosk(audio_path: str) -> str:
    """Transcribe audio using Vosk (offline speech recognition)."""
    import os
    import tempfile
    import json
    from vosk import Model, SetLogLevel, KaldiRecognizer
    from pydub import AudioSegment
    import wave
    
    # Проверяем наличие модели
    if not config.speech_model_path:
        raise ValueError(
            "Vosk requires model_path. Please configure in config.yaml:\n"
            "speech:\n"
            "  provider: \"vosk\"\n"
            "  model_path: \"path/to/vosk-model\"\n\n"
            "Download models from: https://alphacephei.com/vosk/models"
        )
    
    model_path = config.speech_model_path
    if not os.path.exists(model_path):
        raise ValueError(
            f"Vosk model not found at path: {model_path}\n\n"
            "Please download a model from https://alphacephei.com/vosk/models\n"
            "Recommended for Russian: vosk-model-small-ru-0.22 or vosk-model-ru-0.42"
        )
    
    logger.info(f"Using Vosk model: {model_path}")
    
    # Отключаем логи Vosk (они слишком подробные)
    SetLogLevel(-1)
    
    # Загружаем модель (кэшируем для повторного использования)
    if not hasattr(transcribe_vosk, '_model_cache'):
        transcribe_vosk._model_cache = {}
    
    if model_path not in transcribe_vosk._model_cache:
        logger.info(f"Loading Vosk model from {model_path}...")
        transcribe_vosk._model_cache[model_path] = Model(model_path)
        logger.info("Vosk model loaded successfully")
    
    model = transcribe_vosk._model_cache[model_path]
    
    # Конвертируем аудио в формат, который понимает Vosk (WAV, 16kHz, mono, PCM)
    # Vosk работает синхронно, поэтому используем executor для асинхронной работы
    def convert_and_transcribe():
        wav_path = None
        try:
            # Конвертируем OGG в WAV
            audio = AudioSegment.from_file(audio_path)
            
            # Конвертируем в моно, 16kHz, PCM (требования Vosk)
            audio = audio.set_channels(1)  # Моно
            audio = audio.set_frame_rate(16000)  # 16kHz
            audio = audio.set_sample_width(2)  # 16-bit PCM
            
            # Сохраняем во временный WAV файл
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
                audio.export(tmp_wav.name, format="wav")
                wav_path = tmp_wav.name
            
            # Открываем WAV файл с использованием context manager для правильного закрытия
            with wave.open(wav_path, "rb") as wf:
                # Проверяем формат
                if wf.getnchannels() != 1:
                    raise ValueError("Audio file must be mono")
                if wf.getcomptype() != "NONE":
                    raise ValueError("Audio file must be uncompressed PCM")
                
                # Создаем распознаватель с правильным API
                rec = KaldiRecognizer(model, wf.getframerate())
                rec.SetWords(True)  # Включаем распознавание слов для лучшего результата
                
                # Распознаем аудио
                results = []
                while True:
                    data = wf.readframes(4000)  # Читаем по 4000 фреймов
                    if len(data) == 0:
                        break
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        if result.get("text"):
                            results.append(result["text"])
                
                # Получаем финальный результат
                final_result = json.loads(rec.FinalResult())
                if final_result.get("text"):
                    results.append(final_result["text"])
            
            # Объединяем все результаты
            text = " ".join(results).strip()
            
            if not text:
                raise Exception("Vosk recognition returned empty result")
            
            return text
            
        finally:
            # Удаляем временный WAV файл после закрытия
            if wav_path and os.path.exists(wav_path):
                try:
                    # Небольшая задержка для Windows, чтобы файл точно был закрыт
                    import time
                    time.sleep(0.1)
                    os.unlink(wav_path)
                except (PermissionError, OSError) as e:
                    logger.warning(f"Could not delete temporary file {wav_path}: {e}")
    
    # Выполняем распознавание в отдельном потоке (Vosk синхронный)
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(None, convert_and_transcribe)
    
    logger.info(f"Vosk transcription result: {text}")
    return text


@dp.message(F.photo)
async def handle_photo(message: Message):
    """Handle photo messages (receipts)."""
    status_msg = await message.answer("Обрабатываю изображение чека...")
    
    try:
        # Get largest photo
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        
        # Download image to temp file
        import tempfile
        import os
        import base64
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            await bot.download_file(file.file_path, tmp.name)
            temp_path = tmp.name
        
        try:
            # For Ollama, we need base64 or local file
            if config.vlm_provider == "ollama":
                # Optimize image size for Ollama (resize if too large)
                from PIL import Image
                import io
                
                # Open and resize if needed
                img = Image.open(temp_path)
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if image is too large (max 1024px on longest side)
                max_size = 1024
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    logger.info(f"Resized image from {img.size} to {new_size}")
                
                # Save to bytes and encode
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='JPEG', quality=85, optimize=True)
                image_base64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
                logger.info(f"Image encoded, base64 size: {len(image_base64)} chars")
                
                transaction = await vlm_client.extract_transaction_from_image(image_base64=image_base64)
            else:
                # For OpenRouter/OpenAI, use URL
                file_url = f"https://api.telegram.org/file/bot{config.telegram_bot_token}/{file.file_path}"
                transaction = await vlm_client.extract_transaction_from_image(image_url=file_url)
        finally:
            os.unlink(temp_path)
        
        if transaction:
            storage.add_transaction(transaction)
            await safe_edit_text(
                status_msg,
                f"✅ Транзакция из чека добавлена:\n"
                f"📅 {transaction.date} {transaction.time}\n"
                f"{'💰 Доход' if transaction.type.value == 'income' else '💸 Расход'}: {transaction.amount:,.2f} ₽\n"
                f"📂 Категория: {transaction.category.value}\n"
                f"📝 {transaction.description}"
            )
        else:
            await safe_edit_text(status_msg, "Не удалось извлечь информацию о транзакции из изображения.")
    except Exception as e:
        logger.error(f"Error processing photo: {e}", exc_info=True)
        error_text = f"Произошла ошибка при обработке изображения: {str(e)}"
        if not await safe_edit_text(status_msg, error_text):
            try:
                await message.answer(error_text)
            except Exception as send_error:
                logger.error(f"Failed to send error message to user: {send_error}")


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message):
    """Handle text messages."""
    text = message.text
    
    # Extract transaction from text
    transaction = await llm_client.extract_transaction(text)
    
    if transaction:
        storage.add_transaction(transaction)
        await message.answer(
            f"✅ Транзакция добавлена:\n"
            f"📅 {transaction.date} {transaction.time}\n"
            f"{'💰 Доход' if transaction.type.value == 'income' else '💸 Расход'}: {transaction.amount:,.2f} ₽\n"
            f"📂 Категория: {transaction.category.value}\n"
            f"📝 {transaction.description}"
        )
    else:
        await message.answer(
            "Не удалось извлечь информацию о транзакции.\n"
            "Попробуй описать транзакцию более подробно, например:\n"
            "• 'Купил продукты на 500 рублей в магазине'\n"
            "• 'Получил зарплату 50000 рублей'\n"
            "• 'Заказал такси на 300 рублей'"
        )


async def main():
    """Main entry point."""
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

