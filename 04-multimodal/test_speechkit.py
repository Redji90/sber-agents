"""Тестовый скрипт для проверки Yandex SpeechKit API."""
import requests
import sys
from bot.config import config

def test_speechkit_api():
    """Тестирование подключения к Yandex SpeechKit API."""
    print("=" * 60)
    print("Тест подключения к Yandex SpeechKit API")
    print("=" * 60)
    
    # Проверка конфигурации
    api_key = config.speech_api_key.strip() if config.speech_api_key else ""
    
    print(f"\n1. Проверка конфигурации:")
    print(f"   Provider: {config.speech_provider}")
    print(f"   Language: {config.speech_language}")
    print(f"   API Key length: {len(api_key)} символов")
    print(f"   API Key (first 8 chars): {api_key[:8]}...")
    print(f"   API Key (last 4 chars): ...{api_key[-4:] if len(api_key) > 4 else 'N/A'}")
    
    if not api_key:
        print("\n❌ ОШИБКА: API-ключ не настроен!")
        print("   Укажите API-ключ в config.yaml или .env")
        return False
    
    if len(api_key) < 30:
        print(f"\n⚠️  ПРЕДУПРЕЖДЕНИЕ: API-ключ слишком короткий ({len(api_key)} символов)")
        print("   Возможно, ключ скопирован не полностью")
    
    # Тестовый запрос
    print(f"\n2. Тестовый запрос к API:")
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    
    headers = {
        "Authorization": f"Api-Key {api_key}",
    }
    
    params = {
        "lang": config.speech_language,
        "format": "oggopus",
    }
    
    print(f"   URL: {url}")
    print(f"   Headers: Authorization: Api-Key {api_key[:8]}...")
    print(f"   Params: {params}")
    
    # Создаем минимальный тестовый OGG файл (пустой или минимальный)
    # Для реального теста нужен аудиофайл, но для проверки авторизации
    # можно попробовать отправить пустой запрос
    try:
        print(f"\n3. Отправка запроса...")
        # Используем минимальный тестовый OGG файл или пустые данные
        test_data = b""  # Пустые данные для проверки авторизации
        
        response = requests.post(
            url, 
            headers=headers, 
            params=params, 
            data=test_data,
            timeout=10
        )
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("\n✅ УСПЕХ: API-ключ работает корректно!")
            print(f"   Response: {response.text[:200]}")
            return True
        elif response.status_code == 401:
            print("\n❌ ОШИБКА: 401 Unauthorized")
            print(f"   Response: {response.text}")
            try:
                error_json = response.json()
                error_code = error_json.get('error_code', 'N/A')
                error_message = error_json.get('error_message', 'N/A')
                print(f"   Error Code: {error_code}")
                print(f"   Error Message: {error_message}")
                
                # Проверяем тип ошибки
                if "API key not found or invalid" in error_message or "Unauthenticated" in error_message:
                    print("\n   🔑 Проблема: API-ключ неверный или не найден")
                    print("   Решение:")
                    print("   • Создайте новый API-ключ в консоли Yandex Cloud")
                    print("   • Область действия: yc.ai.speechkitStt.execute")
                    print("   • Скопируйте ключ полностью и обновите config.yaml")
                elif "PermissionDenied" in error_message:
                    print("\n   🔐 Проблема: Нет прав доступа к каталогу")
                    print("   Это означает, что API-ключ правильный, но у сервисного аккаунта")
                    print("   нет необходимых прав на каталог!")
                    print("\n   Возможные причины:")
                    print("   1. Роль 'ai.speechkit-stt.user' назначена на облако/организацию, а не на каталог")
                    print("   2. Роль назначена на каталог, но сервисный аккаунт создан в другом каталоге")
                    print("   3. Нужно подождать несколько минут после назначения роли (синхронизация)")
                    print("\n   Решение:")
                    print("   1. Перейдите: Каталоги → default → Права доступа")
                    print("   2. Найдите сервисный аккаунт speechkit-bot в списке")
                    print("   3. Кликните на него или на кнопку 'Настроить доступ'")
                    print("   4. Убедитесь, что роль 'ai.speechkit-stt.user' назначена на КАТАЛОГ default")
                    print("   5. Если роль есть на облаке/организации - удалите её")
                    print("   6. Назначьте роль заново, но обязательно на каталог (folder)")
                    print("   7. Подождите 1-2 минуты и попробуйте снова")
                else:
                    print("\n   Возможные причины:")
                    print("   • API-ключ неверный или неполный")
                    print("   • API-ключ создан не для этого сервисного аккаунта")
                    print("   • API-ключ не имеет области действия yc.ai.speechkitStt.execute")
                    print("   • Сервисный аккаунт не имеет роли ai.speechkit-stt.user")
            except:
                pass
            return False
        elif response.status_code == 400:
            print("\n⚠️  Статус 400 (Bad Request)")
            print("   Это может означать, что авторизация прошла успешно,")
            print("   но запрос неверный (например, отсутствует аудио)")
            print(f"   Response: {response.text[:200]}")
            print("\n✅ Авторизация работает, но нужен реальный аудиофайл для теста")
            return True
        else:
            print(f"\n⚠️  Неожиданный статус: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ ОШИБКА при отправке запроса:")
        print(f"   {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ НЕОЖИДАННАЯ ОШИБКА:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_speechkit_api()
    sys.exit(0 if success else 1)

