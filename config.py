"""
Конфигурация бота для изучения украинского языка
"""
import os

# Telegram Bot Token (получить у @BotFather)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Модель GPT для использования
GPT_MODEL = "gpt-4.1-mini"  # или "gpt-4.1-nano" для экономии

# Настройки обучения
SETTINGS = {
    "max_dialog_history": 10,  # Сколько сообщений хранить в контексте диалога
    "max_tokens_dialog": 500,  # Максимум токенов в ответе диалога
    "max_tokens_question": 800,  # Максимум токенов в ответе на вопрос
    "temperature": 0.7,  # Креативность ответов (0-1)
}

# Проверка конфигурации
def validate_config():
    errors = []
    if not TELEGRAM_TOKEN:
        errors.append("TELEGRAM_TOKEN не установлен")
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY не установлен")
    return errors
