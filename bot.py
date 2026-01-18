#!/usr/bin/env python3
"""
Telegram бот для изучения украинского языка через методологию Discovery
Для носителей русского языка - фокус на разговорной бытовой речи
С поддержкой голосовых сообщений и AI-помощником
"""

from dotenv import load_dotenv
load_dotenv()

import os
import io
import json
import random
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from openai import OpenAI

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_KEY")

# Инициализация OpenAI клиента
client = OpenAI(api_key=OPENAI_API_KEY)

# Состояния для ConversationHandler
CHOOSING, LESSON, DIALOG, TRANSLATE, QUESTION = range(5)

# ============== БАЗА КОНТЕНТА: МЕТОДОЛОГИЯ DISCOVERY ==============
# Фразы организованы по темам с контекстом и объяснениями

DISCOVERY_LESSONS = {
    "greetings": {
        "title": "🤝 Приветствия",
        "phrases": [
            {
                "ukrainian": "Привіт!",
                "russian": "Привет!",
                "context": "Неформальное приветствие для друзей и знакомых",
                "discovery": "Обрати внимание: 'і' в украинском часто там, где в русском 'е'. Привет → Привіт",
                "audio_hint": "При-ВІТ (ударение на последний слог)"
            },
            {
                "ukrainian": "Добрий день!",
                "russian": "Добрый день!",
                "context": "Формальное приветствие в течение дня",
                "discovery": "В украинском 'и' читается как русское 'ы'. Добрий = Добрый",
                "audio_hint": "ДОБ-рий день"
            },
            {
                "ukrainian": "Добрий ранок!",
                "russian": "Доброе утро!",
                "context": "Утреннее приветствие",
                "discovery": "'Ранок' = утро. Запомни: ранок - раннее время, рано!",
                "audio_hint": "ДОБ-рий РА-нок"
            },
            {
                "ukrainian": "Добрий вечір!",
                "russian": "Добрый вечер!",
                "context": "Вечернее приветствие",
                "discovery": "'Вечір' похоже на русское 'вечер', но с 'і'. Типичная замена е→і",
                "audio_hint": "ДОБ-рий ВЕ-чір"
            },
            {
                "ukrainian": "Як справи?",
                "russian": "Как дела?",
                "context": "Спрашиваем как дела у собеседника",
                "discovery": "'Як' = как, 'справи' = дела (от слова 'справа' - дело). Як справи? - буквально 'как дела?'",
                "audio_hint": "як СПРА-ви?"
            },
            {
                "ukrainian": "Дякую, добре!",
                "russian": "Спасибо, хорошо!",
                "context": "Стандартный ответ на 'Як справи?'",
                "discovery": "'Дякую' = спасибо (похоже на польское dziękuję). 'Добре' = хорошо",
                "audio_hint": "ДЯ-ку-ю, ДОБ-ре"
            },
        ]
    },
    "cafe": {
        "title": "☕ В кафе",
        "phrases": [
            {
                "ukrainian": "Можна меню, будь ласка?",
                "russian": "Можно меню, пожалуйста?",
                "context": "Просим меню в кафе или ресторане",
                "discovery": "'Будь ласка' = пожалуйста. Буквально 'будь ласков'. Очень вежливая форма!",
                "audio_hint": "МОЖ-на ме-НЮ, будь ЛАС-ка"
            },
            {
                "ukrainian": "Я хочу каву",
                "russian": "Я хочу кофе",
                "context": "Заказываем кофе",
                "discovery": "'Кава' = кофе. В украинском женский род! 'Смачна кава' - вкусный кофе",
                "audio_hint": "я ХО-чу КА-ву"
            },
            {
                "ukrainian": "Скільки коштує?",
                "russian": "Сколько стоит?",
                "context": "Спрашиваем цену",
                "discovery": "'Скільки' = сколько, 'коштує' = стоит. Коштує от слова 'кошт' - стоимость",
                "audio_hint": "СКІЛЬ-ки кош-ТУ-є?"
            },
            {
                "ukrainian": "Рахунок, будь ласка",
                "russian": "Счёт, пожалуйста",
                "context": "Просим счёт",
                "discovery": "'Рахунок' = счёт. Похоже на 'рахувати' - считать",
                "audio_hint": "ра-ХУ-нок, будь ЛАС-ка"
            },
            {
                "ukrainian": "Дуже смачно!",
                "russian": "Очень вкусно!",
                "context": "Хвалим еду",
                "discovery": "'Дуже' = очень, 'смачно' = вкусно. Смачного! - приятного аппетита!",
                "audio_hint": "ДУ-же СМАЧ-но"
            },
        ]
    },
    "transport": {
        "title": "🚌 Транспорт",
        "phrases": [
            {
                "ukrainian": "Де зупинка?",
                "russian": "Где остановка?",
                "context": "Спрашиваем где остановка транспорта",
                "discovery": "'Де' = где, 'зупинка' = остановка (от 'зупинитися' - остановиться)",
                "audio_hint": "де зу-ПИН-ка?"
            },
            {
                "ukrainian": "Який автобус їде до центру?",
                "russian": "Какой автобус едет до центра?",
                "context": "Узнаём маршрут",
                "discovery": "'Який' = какой, 'їде' = едет. Буква 'ї' читается как 'йи'",
                "audio_hint": "я-КИЙ ав-ТО-бус ЇДЕ до ЦЕН-тру?"
            },
            {
                "ukrainian": "Мені потрібно вийти тут",
                "russian": "Мне нужно выйти здесь",
                "context": "Просим остановить",
                "discovery": "'Потрібно' = нужно, 'вийти' = выйти, 'тут' = здесь/тут",
                "audio_hint": "ме-НІ по-ТРІБ-но ВИЙ-ти тут"
            },
            {
                "ukrainian": "Скільки коштує квиток?",
                "russian": "Сколько стоит билет?",
                "context": "Спрашиваем цену билета",
                "discovery": "'Квиток' = билет. Запомни это слово - часто используется!",
                "audio_hint": "СКІЛЬ-ки кош-ТУ-є кви-ТОК?"
            },
        ]
    },
    "shopping": {
        "title": "🛒 Покупки",
        "phrases": [
            {
                "ukrainian": "Скільки це коштує?",
                "russian": "Сколько это стоит?",
                "context": "Спрашиваем цену товара",
                "discovery": "'Це' = это. Простое и частое слово!",
                "audio_hint": "СКІЛЬ-ки це кош-ТУ-є?"
            },
            {
                "ukrainian": "Чи можна подивитися?",
                "russian": "Можно посмотреть?",
                "context": "Просим показать товар",
                "discovery": "'Чи' - вопросительная частица (необязательна). 'Подивитися' = посмотреть",
                "audio_hint": "чи МОЖ-на по-ди-ВИ-ти-ся?"
            },
            {
                "ukrainian": "Я візьму це",
                "russian": "Я возьму это",
                "context": "Решаем купить",
                "discovery": "'Візьму' = возьму. Обрати внимание на 'і' вместо 'о'",
                "audio_hint": "я ВІЗЬ-му це"
            },
            {
                "ukrainian": "Де можна заплатити?",
                "russian": "Где можно заплатить?",
                "context": "Ищем кассу",
                "discovery": "'Заплатити' = заплатить. Почти как в русском!",
                "audio_hint": "де МОЖ-на за-пла-ТИ-ти?"
            },
            {
                "ukrainian": "Дякую, до побачення!",
                "russian": "Спасибо, до свидания!",
                "context": "Прощаемся",
                "discovery": "'До побачення' = до свидания. 'Побачення' от 'бачити' - видеть",
                "audio_hint": "ДЯ-ку-ю, до по-БА-чен-ня"
            },
        ]
    },
    "home": {
        "title": "🏠 Дома",
        "phrases": [
            {
                "ukrainian": "Я вдома",
                "russian": "Я дома",
                "context": "Сообщаем что мы дома",
                "discovery": "'Вдома' = дома. Приставка 'в' добавляется",
                "audio_hint": "я ВДО-ма"
            },
            {
                "ukrainian": "Я голодний/голодна",
                "russian": "Я голодный/голодная",
                "context": "Говорим что хотим есть",
                "discovery": "'Голодний' (м.р.) / 'голодна' (ж.р.) - почти как в русском!",
                "audio_hint": "я го-ЛОД-ний / го-ЛОД-на"
            },
            {
                "ukrainian": "Що будемо їсти?",
                "russian": "Что будем есть?",
                "context": "Обсуждаем еду",
                "discovery": "'Що' = что, 'їсти' = есть (кушать). 'Ї' читается как 'йи'",
                "audio_hint": "що БУ-де-мо ЇС-ти?"
            },
            {
                "ukrainian": "Я хочу спати",
                "russian": "Я хочу спать",
                "context": "Говорим что устали",
                "discovery": "'Спати' = спать. Инфинитив на '-ти' вместо русского '-ть'",
                "audio_hint": "я ХО-чу СПА-ти"
            },
            {
                "ukrainian": "На добраніч!",
                "russian": "Спокойной ночи!",
                "context": "Желаем спокойной ночи",
                "discovery": "'Добраніч' = доброй ночи. Слитное написание!",
                "audio_hint": "на доб-ра-НІЧ!"
            },
        ]
    },
    "emotions": {
        "title": "😊 Эмоции и чувства",
        "phrases": [
            {
                "ukrainian": "Я радий/рада тебе бачити!",
                "russian": "Я рад/рада тебя видеть!",
                "context": "Выражаем радость от встречи",
                "discovery": "'Радий' (м.р.) / 'рада' (ж.р.), 'бачити' = видеть",
                "audio_hint": "я РА-дий/РА-да те-БЕ БА-чи-ти"
            },
            {
                "ukrainian": "Мені сумно",
                "russian": "Мне грустно",
                "context": "Выражаем грусть",
                "discovery": "'Сумно' = грустно. От слова 'сум' - печаль",
                "audio_hint": "ме-НІ СУМ-но"
            },
            {
                "ukrainian": "Я втомився/втомилася",
                "russian": "Я устал/устала",
                "context": "Говорим об усталости",
                "discovery": "'Втомитися' = устать. 'Втома' = усталость",
                "audio_hint": "я вто-МИВ-ся / вто-МИ-ла-ся"
            },
            {
                "ukrainian": "Це чудово!",
                "russian": "Это чудесно!",
                "context": "Выражаем восторг",
                "discovery": "'Чудово' = чудесно, замечательно. Очень позитивное слово!",
                "audio_hint": "це чу-ДО-во!"
            },
            {
                "ukrainian": "Мені подобається",
                "russian": "Мне нравится",
                "context": "Выражаем симпатию",
                "discovery": "'Подобається' = нравится. Похоже на 'подобаться'",
                "audio_hint": "ме-НІ по-до-БА-єть-ся"
            },
        ]
    },
    "numbers": {
        "title": "🔢 Числа",
        "phrases": [
            {
                "ukrainian": "Один, два, три",
                "russian": "Один, два, три",
                "context": "Базовые числа",
                "discovery": "Числа 1-3 почти как в русском! Легко запомнить.",
                "audio_hint": "о-ДИН, два, три"
            },
            {
                "ukrainian": "Чотири, п'ять, шість",
                "russian": "Четыре, пять, шесть",
                "context": "Числа 4-6",
                "discovery": "'Чотири' = четыре (чо- вместо че-). 'П'ять' с апострофом!",
                "audio_hint": "чо-ТИ-ри, п'ять, шість"
            },
            {
                "ukrainian": "Сім, вісім, дев'ять, десять",
                "russian": "Семь, восемь, девять, десять",
                "context": "Числа 7-10",
                "discovery": "'Сім' = семь, 'вісім' = восемь. Обрати внимание на 'і'!",
                "audio_hint": "сім, ВІ-сім, ДЕВ'-ять, ДЕ-сять"
            },
        ]
    }
}

# Упражнения на перевод
TRANSLATION_EXERCISES = [
    {"russian": "Привет, как дела?", "ukrainian": "Привіт, як справи?", "hint": "Помни: е→і"},
    {"russian": "Спасибо, хорошо", "ukrainian": "Дякую, добре", "hint": "Дякую = спасибо"},
    {"russian": "Сколько это стоит?", "ukrainian": "Скільки це коштує?", "hint": "коштує = стоит"},
    {"russian": "Я хочу кофе", "ukrainian": "Я хочу каву", "hint": "кава = кофе (ж.р.)"},
    {"russian": "Где остановка?", "ukrainian": "Де зупинка?", "hint": "зупинка = остановка"},
    {"russian": "До свидания!", "ukrainian": "До побачення!", "hint": "побачення от 'бачити' - видеть"},
    {"russian": "Очень вкусно!", "ukrainian": "Дуже смачно!", "hint": "смачно = вкусно"},
    {"russian": "Я дома", "ukrainian": "Я вдома", "hint": "вдома = дома (с приставкой в)"},
    {"russian": "Что будем есть?", "ukrainian": "Що будемо їсти?", "hint": "їсти = есть"},
    {"russian": "Спокойной ночи!", "ukrainian": "На добраніч!", "hint": "добраніч - слитно"},
    {"russian": "Пожалуйста", "ukrainian": "Будь ласка", "hint": "буквально 'будь ласков'"},
    {"russian": "Я устал", "ukrainian": "Я втомився", "hint": "втомитися = устать"},
    {"russian": "Это чудесно!", "ukrainian": "Це чудово!", "hint": "чудово = чудесно"},
    {"russian": "Мне нравится", "ukrainian": "Мені подобається", "hint": "подобається = нравится"},
    {"russian": "Доброе утро!", "ukrainian": "Добрий ранок!", "hint": "ранок = утро"},
]

# Хранилище данных пользователей
user_data = {}

def get_user_data(user_id: int) -> dict:
    """Получить или создать данные пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {
            "completed_lessons": [],
            "current_topic": None,
            "phrase_index": 0,
            "correct_answers": 0,
            "total_answers": 0,
            "streak": 0,
            "last_activity": None,
            "dialog_context": [],
            "mode": None  # Текущий режим работы
        }
    return user_data[user_id]


# ============== ГОЛОСОВЫЕ ФУНКЦИИ ==============

async def generate_speech(text: str, voice: str = "alloy") -> bytes:
    """Генерация голосового сообщения через OpenAI TTS"""
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,  # alloy, echo, fable, onyx, nova, shimmer
            input=text
        )
        return response.content
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return None


async def transcribe_voice(file_path: str) -> str:
    """Транскрипция голосового сообщения через OpenAI Whisper"""
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="uk"  # Украинский язык
            )
        return transcript.text
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None


async def send_voice_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Отправить голосовое сообщение с украинской фразой"""
    audio_data = await generate_speech(text)
    if audio_data:
        await update.callback_query.message.reply_voice(
            voice=io.BytesIO(audio_data),
            caption=f"🔊 {text}"
        )
    else:
        await update.callback_query.message.reply_text(
            f"⚠️ Не удалось сгенерировать аудио для: {text}"
        )


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка голосового сообщения от пользователя"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    
    # Скачиваем голосовое сообщение
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    
    # Создаём временный файл
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_file:
        await file.download_to_drive(tmp_file.name)
        tmp_path = tmp_file.name
    
    try:
        # Транскрибируем
        transcribed_text = await transcribe_voice(tmp_path)
        
        if not transcribed_text:
            await update.message.reply_text(
                "😕 Не удалось распознать голосовое сообщение. Попробуй ещё раз!"
            )
            return user_info.get("mode", CHOOSING) or CHOOSING
        
        # Показываем что распознали
        await update.message.reply_text(
            f"🎤 Я услышал: *{transcribed_text}*",
            parse_mode='Markdown'
        )
        
        # Обрабатываем в зависимости от режима
        current_mode = user_info.get("mode")
        
        if current_mode == DIALOG:
            # В режиме диалога - обрабатываем как текстовое сообщение
            return await process_dialog_message(update, context, transcribed_text)
        elif current_mode == TRANSLATE:
            # В режиме перевода - проверяем ответ
            return await process_translation_answer(update, context, transcribed_text)
        else:
            # В других режимах - используем AI для анализа
            return await process_general_voice(update, context, transcribed_text)
            
    finally:
        # Удаляем временный файл
        os.unlink(tmp_path)


async def process_dialog_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> int:
    """Обработка сообщения в режиме диалога"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    
    # Добавляем сообщение в контекст
    user_info["dialog_context"].append({"role": "user", "content": text})
    
    system_prompt = """Ты — дружелюбный учитель украинского языка для русскоговорящего ученика.
    
Правила:
1. Отвечай на украинском языке
2. После украинского текста добавляй перевод на русский в скобках
3. Если ученик сделал ошибку — мягко исправь и объясни на русском
4. Используй простые бытовые фразы
5. Поддерживай и хвали за попытки
6. Если ученик пишет на русском — переведи его фразу на украинский и попроси повторить
7. Веди естественный диалог на бытовые темы
8. Если ученик говорит голосом — похвали за практику произношения

Пример ответа:
"Привіт! Як справи? (Привет! Как дела?)
Ти добре написав! (Ты хорошо написал!)
💡 Маленькая подсказка: в украинском 'е' часто становится 'і'"
"""
    
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(user_info["dialog_context"][-10:])
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        assistant_message = response.choices[0].message.content
        user_info["dialog_context"].append({"role": "assistant", "content": assistant_message})
        
        await update.message.reply_text(assistant_message)
        
        # Генерируем голосовой ответ для украинской части
        # Извлекаем украинский текст (до скобок)
        ukrainian_part = assistant_message.split("(")[0].strip() if "(" in assistant_message else assistant_message[:100]
        if ukrainian_part and len(ukrainian_part) > 5:
            audio_data = await generate_speech(ukrainian_part)
            if audio_data:
                await update.message.reply_voice(
                    voice=io.BytesIO(audio_data),
                    caption="🔊 Послушай произношение"
                )
        
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        await update.message.reply_text(
            "Извини, произошла ошибка. Попробуй ещё раз!"
        )
    
    return DIALOG


async def process_translation_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> int:
    """Обработка ответа на упражнение перевода"""
    user_answer = text.strip().lower()
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    
    exercise = context.user_data.get("current_exercise", {})
    correct_answer = exercise.get("ukrainian", "").lower()
    
    user_info["total_answers"] += 1
    
    # Проверяем ответ с помощью AI для большей гибкости
    try:
        check_response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "system",
                "content": """Ты проверяешь перевод ученика с русского на украинский.
                Ответь JSON: {"correct": true/false, "explanation": "краткое объяснение на русском"}
                Будь гибким: небольшие опечатки или альтернативные формы допустимы."""
            }, {
                "role": "user",
                "content": f"Русский: '{exercise.get('russian', '')}'\nПравильный ответ: '{correct_answer}'\nОтвет ученика: '{user_answer}'"
            }],
            max_tokens=150
        )
        
        result_text = check_response.choices[0].message.content
        # Пытаемся распарсить JSON
        try:
            # Убираем возможные markdown-обёртки
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            result = json.loads(result_text)
            is_correct = result.get("correct", False)
            explanation = result.get("explanation", "")
        except:
            # Если не удалось распарсить, используем простую проверку
            is_correct = user_answer == correct_answer
            explanation = ""
            
    except Exception as e:
        logger.error(f"Check error: {e}")
        is_correct = user_answer == correct_answer
        explanation = ""
    
    if is_correct:
        user_info["correct_answers"] += 1
        user_info["streak"] += 1
        
        response = f"""
✅ *Правильно!* Молодец!

🔥 Серия правильных ответов: {user_info["streak"]}

Напиши /translate для следующего упражнения.
"""
        # Отправляем голосовое подтверждение
        audio_data = await generate_speech(exercise.get("ukrainian", ""))
        if audio_data:
            await update.message.reply_voice(
                voice=io.BytesIO(audio_data),
                caption=f"🔊 {exercise.get('ukrainian', '')}"
            )
    else:
        user_info["streak"] = 0
        
        response = f"""
❌ *Не совсем так*

Твой ответ: {user_answer}
Правильно: *{exercise.get('ukrainian', '?')}*

💡 {explanation if explanation else 'Попробуй обратить внимание на особенности украинского написания.'}

Напиши /translate для следующего упражнения.
"""
    
    await update.message.reply_text(response, parse_mode='Markdown')
    user_info["mode"] = CHOOSING
    return CHOOSING


async def process_general_voice(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> int:
    """Обработка голосового сообщения в общем режиме"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    
    # Используем AI для понимания намерения
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "system",
                "content": """Ты — помощник для изучения украинского языка.
                Пользователь отправил голосовое сообщение. Определи его намерение и помоги:
                - Если это попытка сказать что-то на украинском — оцени произношение и исправь ошибки
                - Если это вопрос — ответь на него
                - Если это просьба перевести — переведи
                - Если непонятно — предложи начать урок или диалог
                
                Отвечай дружелюбно, давай примеры на украинском с переводом."""
            }, {
                "role": "user",
                "content": f"Пользователь сказал: '{text}'"
            }],
            max_tokens=500,
            temperature=0.7
        )
        
        answer = response.choices[0].message.content
        await update.message.reply_text(answer)
        
        # Предлагаем действия
        keyboard = [
            [InlineKeyboardButton("📚 Начать урок", callback_data="start_lesson")],
            [InlineKeyboardButton("💬 Диалог с AI", callback_data="start_dialog")],
            [InlineKeyboardButton("✍️ Перевод", callback_data="start_translate")]
        ]
        await update.message.reply_text(
            "Что хочешь делать дальше?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"AI error: {e}")
        await update.message.reply_text(
            "Произошла ошибка. Попробуй написать текстом или используй /start"
        )
    
    return CHOOSING


# ============== ОБРАБОТЧИКИ КОМАНД ==============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Приветствие и главное меню"""
    user = update.effective_user
    user_info = get_user_data(user.id)
    user_info["mode"] = CHOOSING
    
    welcome_text = f"""
🇺🇦 *Привет, {user.first_name}!*

Добро пожаловать!

Я помогу тебе выучить украинский язык через метод *Discovery* — учимся на примерах, а не на правилах!

*Как это работает:*
• Ты видишь фразу в контексте
• Я объясняю особенности на русском
• Ты практикуешься через диалоги и переводы
• 🎤 *Можешь отправлять голосовые сообщения!*

*Что умею:*
📚 /lesson — Мини-урок по теме
💬 /dialog — Диалог с AI на украинском
✍️ /translate — Упражнения на перевод
❓ /ask — Задать вопрос об украинском
📊 /progress — Твой прогресс
🔊 /voice — Озвучить фразу

Выбери действие:
"""
    
    keyboard = [
        [InlineKeyboardButton("📚 Начать урок", callback_data="start_lesson")],
        [InlineKeyboardButton("💬 Диалог с AI", callback_data="start_dialog")],
        [InlineKeyboardButton("✍️ Перевод", callback_data="start_translate")],
        [InlineKeyboardButton("❓ Задать вопрос", callback_data="ask_question")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return CHOOSING


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для озвучивания фразы"""
    if context.args:
        text = " ".join(context.args)
        audio_data = await generate_speech(text)
        if audio_data:
            await update.message.reply_voice(
                voice=io.BytesIO(audio_data),
                caption=f"🔊 {text}"
            )
        else:
            await update.message.reply_text("Не удалось сгенерировать аудио.")
    else:
        await update.message.reply_text(
            "Использование: /voice <фраза на украинском>\n"
            "Пример: /voice Привіт, як справи?"
        )


async def show_topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать доступные темы для урока"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    user_info["mode"] = LESSON
    
    keyboard = []
    for topic_id, topic_data in DISCOVERY_LESSONS.items():
        keyboard.append([InlineKeyboardButton(
            topic_data["title"], 
            callback_data=f"topic_{topic_id}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
📚 *Выбери тему для урока:*

Каждая тема содержит полезные фразы с объяснениями.
Метод Discovery: сначала видишь пример, потом понимаешь правило!

🔊 К каждой фразе есть аудио-произношение!
"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    return LESSON


async def show_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE, topic_id: str, phrase_idx: int) -> None:
    """Показать фразу из урока"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    
    topic = DISCOVERY_LESSONS.get(topic_id)
    if not topic or phrase_idx >= len(topic["phrases"]):
        # Урок завершён
        keyboard = [[InlineKeyboardButton("🔙 К темам", callback_data="start_lesson")]]
        await update.callback_query.edit_message_text(
            "🎉 *Отлично! Тема пройдена!*\n\nВыбери следующую тему или попрактикуйся в диалоге.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        if topic_id not in user_info["completed_lessons"]:
            user_info["completed_lessons"].append(topic_id)
        return
    
    phrase = topic["phrases"][phrase_idx]
    
    text = f"""
{topic["title"]} — Фраза {phrase_idx + 1}/{len(topic["phrases"])}

🇺🇦 *{phrase["ukrainian"]}*
🇷🇺 {phrase["russian"]}

📍 *Контекст:* {phrase["context"]}

💡 *Discovery:* {phrase["discovery"]}

🔊 *Произношение:* `{phrase["audio_hint"]}`
"""
    
    keyboard = [
        [InlineKeyboardButton("🔊 Послушать", callback_data=f"listen_{topic_id}_{phrase_idx}")],
        [InlineKeyboardButton("➡️ Следующая", callback_data=f"phrase_{topic_id}_{phrase_idx + 1}")],
        [InlineKeyboardButton("🔙 К темам", callback_data="start_lesson")]
    ]
    
    await update.callback_query.edit_message_text(
        text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def start_dialog_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начать диалог с AI"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    user_info["dialog_context"] = []
    user_info["mode"] = DIALOG
    
    text = """
💬 *Режим диалога*

Сейчас мы будем общаться на украинском!
Я буду отвечать на украинском и помогать тебе.

*Правила:*
• Пиши на украинском (как можешь)
• 🎤 Можешь отправлять голосовые сообщения!
• Я исправлю ошибки и объясню
• Можешь спрашивать "как сказать...?"

*Начнём с простого:*
Поздоровайся со мной на украинском! 👋

_(Напиши /stop чтобы выйти из диалога)_
"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')
    
    return DIALOG


async def handle_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка текстовых сообщений в режиме диалога"""
    user_message = update.message.text
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    
    if user_message.lower() == '/stop':
        user_info["mode"] = CHOOSING
        await update.message.reply_text(
            "Диалог завершён!\n\nИспользуй /start для главного меню."
        )
        return CHOOSING
    
    return await process_dialog_message(update, context, user_message)


async def start_translate_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начать упражнения на перевод"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    user_info["mode"] = TRANSLATE
    
    # Выбираем случайное упражнение
    exercise = random.choice(TRANSLATION_EXERCISES)
    context.user_data["current_exercise"] = exercise
    
    text = f"""
✍️ *Упражнение на перевод*

Переведи на украинский:

🇷🇺 *{exercise["russian"]}*

💡 Подсказка: {exercise["hint"]}

🎤 Можешь ответить голосовым сообщением!

_(Напиши свой перевод или /skip чтобы пропустить)_
"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')
    
    return TRANSLATE


async def check_translation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Проверить перевод пользователя (текстовый)"""
    user_answer = update.message.text.strip()
    return await process_translation_answer(update, context, user_answer)


async def ask_question_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Режим вопросов об украинском языке"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    user_info["mode"] = QUESTION
    
    text = """
❓ *Задай вопрос*

Ты можешь спросить меня о чём угодно:
• Как сказать что-то на украинском?
• Почему так пишется/говорится?
• В чём разница между словами?
• Грамматические вопросы

🎤 Можешь спросить голосом!

Напиши свой вопрос:

_(Напиши /stop чтобы вернуться в меню)_
"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')
    
    return QUESTION


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка вопроса пользователя"""
    question = update.message.text
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    
    if question.lower() == '/stop':
        user_info["mode"] = CHOOSING
        await update.message.reply_text(
            "Возвращаемся в меню. Используй /start"
        )
        return CHOOSING
    
    system_prompt = """Ты — эксперт по украинскому языку, помогающий русскоговорящему ученику.

Правила ответа:
1. Отвечай на русском языке (это вопрос об украинском, не практика)
2. Давай примеры на украинском с переводом
3. Объясняй различия между русским и украинским
4. Упоминай типичные ошибки русскоговорящих
5. Будь дружелюбным и поддерживающим
6. Если уместно, дай мнемонику для запоминания
7. Если спрашивают как произносится — объясни подробно"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        answer = response.choices[0].message.content
        await update.message.reply_text(answer)
        
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке вопроса. Попробуй ещё раз!"
        )
    
    await update.message.reply_text(
        "\n_Есть ещё вопросы? Пиши! Или /stop для выхода._",
        parse_mode='Markdown'
    )
    return QUESTION


async def show_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать прогресс пользователя"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    
    total_topics = len(DISCOVERY_LESSONS)
    completed = len(user_info["completed_lessons"])
    
    if user_info["total_answers"] > 0:
        accuracy = (user_info["correct_answers"] / user_info["total_answers"]) * 100
    else:
        accuracy = 0
    
    text = f"""
📊 *Твой прогресс*

📚 Темы: {completed}/{total_topics} пройдено
✍️ Упражнения: {user_info["total_answers"]} выполнено
✅ Точность: {accuracy:.1f}%
🔥 Текущая серия: {user_info["streak"]}

*Пройденные темы:*
"""
    
    for topic_id in user_info["completed_lessons"]:
        topic = DISCOVERY_LESSONS.get(topic_id, {})
        text += f"• {topic.get('title', topic_id)}\n"
    
    if not user_info["completed_lessons"]:
        text += "_Пока нет пройденных тем_\n"
    
    text += "\nПродолжай учиться! 💪"
    
    await update.message.reply_text(text, parse_mode='Markdown')


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    
    if data == "start_lesson":
        return await show_topics(update, context)
    
    elif data == "start_dialog":
        return await start_dialog_mode(update, context)
    
    elif data == "start_translate":
        return await start_translate_mode(update, context)
    
    elif data == "ask_question":
        return await ask_question_mode(update, context)
    
    elif data == "back_to_menu":
        user_info["mode"] = CHOOSING
        keyboard = [
            [InlineKeyboardButton("📚 Начать урок", callback_data="start_lesson")],
            [InlineKeyboardButton("💬 Диалог с AI", callback_data="start_dialog")],
            [InlineKeyboardButton("✍️ Перевод", callback_data="start_translate")],
            [InlineKeyboardButton("❓ Задать вопрос", callback_data="ask_question")]
        ]
        await query.edit_message_text(
            "Выбери действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CHOOSING
    
    elif data.startswith("topic_"):
        topic_id = data.replace("topic_", "")
        user_info["current_topic"] = topic_id
        await show_phrase(update, context, topic_id, 0)
        return LESSON
    
    elif data.startswith("phrase_"):
        parts = data.split("_")
        topic_id = parts[1]
        phrase_idx = int(parts[2])
        await show_phrase(update, context, topic_id, phrase_idx)
        return LESSON
    
    elif data.startswith("listen_"):
        # Озвучивание фразы
        parts = data.split("_")
        topic_id = parts[1]
        phrase_idx = int(parts[2])
        
        topic = DISCOVERY_LESSONS.get(topic_id)
        if topic and phrase_idx < len(topic["phrases"]):
            phrase = topic["phrases"][phrase_idx]
            await send_voice_phrase(update, context, phrase["ukrainian"])
        return LESSON
    
    return CHOOSING


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущего действия"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    user_info["mode"] = CHOOSING
    
    await update.message.reply_text(
        "Действие отменено. Используй /start для начала."
    )
    return ConversationHandler.END


def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Conversation handler для управления состояниями
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                CallbackQueryHandler(button_handler),
                CommandHandler("lesson", show_topics),
                CommandHandler("dialog", start_dialog_mode),
                CommandHandler("translate", start_translate_mode),
                CommandHandler("ask", ask_question_mode),
                CommandHandler("progress", show_progress),
                MessageHandler(filters.VOICE, handle_voice_message),
            ],
            LESSON: [
                CallbackQueryHandler(button_handler),
                MessageHandler(filters.VOICE, handle_voice_message),
            ],
            DIALOG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_dialog),
                MessageHandler(filters.VOICE, handle_voice_message),
                CommandHandler("stop", cancel),
            ],
            TRANSLATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_translation),
                MessageHandler(filters.VOICE, handle_voice_message),
                CommandHandler("skip", start_translate_mode),
            ],
            QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question),
                MessageHandler(filters.VOICE, handle_voice_message),
                CommandHandler("stop", cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("progress", show_progress))
    application.add_handler(CommandHandler("voice", voice_command))
    
    # Запуск бота
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
