#!/usr/bin/env python3
"""
Telegram бот для изучения украинского языка через методологию Discovery
Для носителей русского языка - фокус на разговорной бытовой речи
С поддержкой голосовых сообщений, AI-помощником и натуральным украинским голосом ElevenLabs
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
from elevenlabs.client import ElevenLabs

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "YOUR_ELEVENLABS_KEY")

# Инициализация клиентов
openai_client = OpenAI(api_key=OPENAI_API_KEY)
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# ElevenLabs голоса для украинского
UKRAINIAN_VOICES = {
    "nicoletta": "lBpHyluYpWLnqqh742Jh",  # Nicoletta - рекомендуемый голос
    "vira": "T0D5z8h7c1XgyjzzYXzW",       # Vira - молодой натуральный
    "anton": "EXAVITQu4vr4xnSDxMaL",      # Anton - дружелюбный
}

DEFAULT_VOICE = "nicoletta"  # По умолчанию Nicoletta

# Состояния для ConversationHandler
CHOOSING, LESSON, DIALOG, TRANSLATE, QUESTION = range(5)

# ============== БАЗА КОНТЕНТА: МЕТОДОЛОГИЯ DISCOVERY ==============

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
                "discovery": "'Можна' = можно, 'будь ласка' = пожалуйста (буквально 'будь ласков')",
                "audio_hint": "МОЖ-на, будь ЛА-ска"
            },
            {
                "ukrainian": "Я хочу каву",
                "russian": "Я хочу кофе",
                "context": "Заказываем кофе",
                "discovery": "'Кава' = кофе (женский род в украинском!). Не 'кофе', а 'кава'",
                "audio_hint": "я ХО-чу КА-ву"
            },
            {
                "ukrainian": "Скільки це коштує?",
                "russian": "Сколько это стоит?",
                "context": "Спрашиваем цену",
                "discovery": "'Скільки' = сколько, 'коштує' = стоит (от слова 'кошт' - цена)",
                "audio_hint": "СКІЛЬ-ки це КОШ-ту-є?"
            },
            {
                "ukrainian": "Дуже смачно!",
                "russian": "Очень вкусно!",
                "context": "Хвалим еду",
                "discovery": "'Дуже' = очень, 'смачно' = вкусно. Похоже на русское 'смачный'",
                "audio_hint": "ДУ-же СМА-чно!"
            },
            {
                "ukrainian": "Рахунок, будь ласка!",
                "russian": "Счет, пожалуйста!",
                "context": "Просим счет",
                "discovery": "'Рахунок' = счет (от слова 'рахувати' - считать)",
                "audio_hint": "ра-ХУ-нок, будь ЛА-ска"
            },
        ]
    },
    "transport": {
        "title": "🚌 Транспорт",
        "phrases": [
            {
                "ukrainian": "Де зупинка?",
                "russian": "Где остановка?",
                "context": "Ищем остановку",
                "discovery": "'Де' = где, 'зупинка' = остановка (от слова 'зупинити' - остановить)",
                "audio_hint": "де зу-ПІН-ка?"
            },
            {
                "ukrainian": "Один квиток до центру",
                "russian": "Один билет до центра",
                "context": "Покупаем билет",
                "discovery": "'Квиток' = билет, 'центр' → 'центру' (дательный падеж)",
                "audio_hint": "о-ДИН КВІ-ток до ЦЕН-тру"
            },
            {
                "ukrainian": "Це автобус номер 5?",
                "russian": "Это автобус номер 5?",
                "context": "Проверяем номер автобуса",
                "discovery": "'Це' = это, 'номер' = номер (похоже на русское)",
                "audio_hint": "це ав-то-БУС НО-мер п'ять?"
            },
        ]
    },
    "shopping": {
        "title": "🛍️ Покупки",
        "phrases": [
            {
                "ukrainian": "Скільки коштує?",
                "russian": "Сколько стоит?",
                "context": "Спрашиваем цену товара",
                "discovery": "'Коштує' = стоит (основной глагол для цены)",
                "audio_hint": "СКІЛЬ-ки КОШ-ту-є?"
            },
            {
                "ukrainian": "Це занадто дорого",
                "russian": "Это слишком дорого",
                "context": "Товар дорогой",
                "discovery": "'Занадто' = слишком, 'дорого' = дорого",
                "audio_hint": "це за-НА-дто ДО-ро-го"
            },
            {
                "ukrainian": "Є знижка?",
                "russian": "Есть скидка?",
                "context": "Спрашиваем про скидку",
                "discovery": "'Є' = есть (от слова 'бути' - быть), 'знижка' = скидка",
                "audio_hint": "є ЗНІ-жка?"
            },
        ]
    },
    "home": {
        "title": "🏠 Дома",
        "phrases": [
            {
                "ukrainian": "Я вдома",
                "russian": "Я дома",
                "context": "Говорим что мы дома",
                "discovery": "'Вдома' = дома (с приставкой 'в'). Не 'дома', а 'вдома'",
                "audio_hint": "я ВДО-ма"
            },
            {
                "ukrainian": "Що будемо їсти?",
                "russian": "Что будем есть?",
                "context": "Спрашиваем что готовить",
                "discovery": "'Що' = что, 'їсти' = есть (с диакритикой 'ї')",
                "audio_hint": "що БУ-де-мо ЇС-ти?"
            },
            {
                "ukrainian": "На добраніч!",
                "russian": "Спокойной ночи!",
                "context": "Пожелание перед сном",
                "discovery": "'На добраніч' = спокойной ночи (буквально 'на добрую ночь', слитно)",
                "audio_hint": "на ДОБ-ра-НІЧ!"
            },
        ]
    },
    "emotions": {
        "title": "😊 Эмоции",
        "phrases": [
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
            "mode": None,
            "voice": DEFAULT_VOICE
        }
    return user_data[user_id]


# ============== ГОЛОСОВЫЕ ФУНКЦИИ С ELEVENLABS ==============

async def generate_speech_elevenlabs(text: str, voice_id: str = None) -> bytes:
    """Генерация голосового сообщения через ElevenLabs"""
    try:
        if voice_id is None:
            voice_id = UKRAINIAN_VOICES[DEFAULT_VOICE]
        
        audio = elevenlabs_client.generate(
            text=text,
            voice=voice_id,
            model="eleven_multilingual_v2"
        )
        
        # Преобразуем в bytes
        audio_bytes = b"".join(audio)
        return audio_bytes
    except Exception as e:
        logger.error(f"ElevenLabs TTS error: {e}")
        return None


async def transcribe_voice(file_path: str) -> str:
    """Транскрипция голосового сообщения через OpenAI Whisper"""
    try:
        with open(file_path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="uk"
            )
        return transcript.text
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None


async def send_voice_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, voice_id: str = None) -> None:
    """Отправить голосовое сообщение с украинской фразой"""
    audio_data = await generate_speech_elevenlabs(text, voice_id)
    if audio_data:
        try:
            await update.callback_query.message.reply_voice(
                voice=io.BytesIO(audio_data),
                caption=f"🔊 {text}"
            )
        except:
            await update.message.reply_voice(
                voice=io.BytesIO(audio_data),
                caption=f"🔊 {text}"
            )
    else:
        await update.message.reply_text(
            f"⚠️ Не удалось сгенерировать аудио для: {text}"
        )


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка голосового сообщения от пользователя"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_file:
        await file.download_to_drive(tmp_file.name)
        tmp_path = tmp_file.name
    
    try:
        transcribed_text = await transcribe_voice(tmp_path)
        
        if not transcribed_text:
            await update.message.reply_text(
                "😕 Не удалось распознать голосовое сообщение. Попробуй ещё раз!"
            )
            return user_info.get("mode", CHOOSING) or CHOOSING
        
        await update.message.reply_text(
            f"🎤 Я услышал: *{transcribed_text}*",
            parse_mode='Markdown'
        )
        
        current_mode = user_info.get("mode")
        
        if current_mode == DIALOG:
            return await process_dialog_message(update, context, transcribed_text, user_info)
        elif current_mode == TRANSLATE:
            return await process_translation_answer(update, context, transcribed_text)
        else:
            return await process_general_voice(update, context, transcribed_text)
            
    finally:
        os.unlink(tmp_path)


async def process_dialog_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, user_info: dict = None) -> int:
    """Обработка сообщения в режиме диалога"""
    user_id = update.effective_user.id
    if user_info is None:
        user_info = get_user_data(user_id)
    
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
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        assistant_message = response.choices[0].message.content
        user_info["dialog_context"].append({"role": "assistant", "content": assistant_message})
        
        await update.message.reply_text(assistant_message)
        
        # Генерируем голосовой ответ
        ukrainian_part = assistant_message.split("(")[0].strip() if "(" in assistant_message else assistant_message[:100]
        if ukrainian_part and len(ukrainian_part) > 5:
            voice_id = UKRAINIAN_VOICES.get(user_info.get("voice", DEFAULT_VOICE))
            audio_data = await generate_speech_elevenlabs(ukrainian_part, voice_id)
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


async def process_translation_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, user_answer: str) -> int:
    """Проверить перевод пользователя"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    
    exercise = context.user_data.get("current_exercise")
    if not exercise:
        await update.message.reply_text("Упражнение не найдено. Начни заново: /translate")
        return TRANSLATE
    
    user_info["total_answers"] += 1
    
    system_prompt = f"""Ты — учитель украинского языка. Проверь ответ ученика.

Правильный ответ: {exercise['ukrainian']}
Ответ ученика: {user_answer}

Задача: 
1. Проверь правильность (допускай небольшие опечатки и вариации)
2. Если правильно - похвали и объясни на русском почему это правильно
3. Если неправильно - покажи правильный ответ, объясни ошибку и дай подсказку
4. Всегда будь дружелюбным и поддерживающим

Ответь на русском языке."""
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "system", "content": system_prompt}],
            max_tokens=300,
            temperature=0.7
        )
        
        feedback = response.choices[0].message.content
        
        # Проверяем правильность (простая проверка)
        is_correct = user_answer.lower().strip() == exercise['ukrainian'].lower().strip()
        
        if is_correct:
            user_info["correct_answers"] += 1
            user_info["streak"] += 1
            
            response_text = f"""
✅ *Правильно!* Молодец!

🔥 Серия правильных ответов: {user_info["streak"]}

{feedback}

Напиши /translate для следующего упражнения."""
        else:
            user_info["streak"] = 0
            response_text = f"""
❌ Не совсем правильно...

{feedback}

*Правильный ответ:* {exercise['ukrainian']}

Напиши /translate для следующего упражнения."""
        
        await update.message.reply_text(response_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        await update.message.reply_text(
            "Произошла ошибка при проверке. Попробуй ещё раз!"
        )
    
    return TRANSLATE


async def process_general_voice(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> int:
    """Обработка голосового сообщения в других режимах"""
    await update.message.reply_text(
        f"Ты сказал: *{text}*\n\nЭто отличная практика! 🎤",
        parse_mode='Markdown'
    )
    return CHOOSING


# ============== КОМАНДЫ БОТА ==============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало работы с ботом"""
    user = update.effective_user
    user_id = user.id
    user_info = get_user_data(user_id)
    user_info["mode"] = CHOOSING
    
    welcome_text = f"""
🇺🇦 *Привет, {user.first_name}!*

Добро пожаловать!

Я помогу тебе выучить украинский язык через метод *Discovery* — учимся на примерах, а не на правилах!

*Как это работает:*
• Ты видишь фразу в контексте
• Я объясняю особенности на русском
• Слушаешь натуральное произношение 🔊
• Практикуешься в диалоге и переводе

*Что ты можешь делать:*
📚 Уроки - изучай фразы по темам
💬 Диалог - общайся со мной на украинском
✍️ Перевод - переводи фразы с русского
❓ Вопросы - спрашивай что угодно об украинском
📊 Прогресс - смотри свою статистику

Выбери действие:
"""
    
    keyboard = [
        [InlineKeyboardButton("📚 Начать урок", callback_data="start_lesson")],
        [InlineKeyboardButton("💬 Диалог с AI", callback_data="start_dialog")],
        [InlineKeyboardButton("✍️ Перевод", callback_data="start_translate")],
        [InlineKeyboardButton("❓ Задать вопрос", callback_data="ask_question")]
    ]
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return CHOOSING


async def show_topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать список тем для обучения"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    user_info["mode"] = LESSON
    
    keyboard = []
    for topic_id, topic in DISCOVERY_LESSONS.items():
        status = "✅" if topic_id in user_info["completed_lessons"] else "⭕"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {topic['title']}",
                callback_data=f"topic_{topic_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])
    
    text = """
📚 *Выбери тему для обучения*

✅ = пройдено
⭕ = новое
"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    return LESSON


async def show_phrase(update: Update, context: ContextTypes.DEFAULT_TYPE, topic_id: str, phrase_idx: int) -> int:
    """Показать фразу с объяснением и озвучкой"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    
    topic = DISCOVERY_LESSONS.get(topic_id)
    if not topic or phrase_idx >= len(topic["phrases"]):
        await update.callback_query.answer("Упражнение завершено!")
        if topic_id not in user_info["completed_lessons"]:
            user_info["completed_lessons"].append(topic_id)
        return await show_topics(update, context)
    
    phrase = topic["phrases"][phrase_idx]
    user_info["current_topic"] = topic_id
    user_info["phrase_index"] = phrase_idx
    
    text = f"""
📖 *{topic['title']}*

🇺🇦 *{phrase['ukrainian']}*
🇷🇺 {phrase['russian']}

💡 *Discovery:* {phrase['discovery']}

📝 *Контекст:* {phrase['context']}

🔊 *Произношение:* {phrase['audio_hint']}
"""
    
    # Кнопки навигации
    keyboard = []
    
    # Кнопка для озвучки
    keyboard.append([
        InlineKeyboardButton("🔊 Послушай", callback_data=f"listen_{topic_id}_{phrase_idx}")
    ])
    
    # Кнопки навигации
    nav_buttons = []
    if phrase_idx > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"phrase_{topic_id}_{phrase_idx-1}"))
    if phrase_idx < len(topic["phrases"]) - 1:
        nav_buttons.append(InlineKeyboardButton("Далее ➡️", callback_data=f"phrase_{topic_id}_{phrase_idx+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("⬅️ К темам", callback_data="start_lesson")])
    
    await update.callback_query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    # Автоматически отправляем голосовое сообщение
    voice_id = UKRAINIAN_VOICES.get(user_info.get("voice", DEFAULT_VOICE))
    await send_voice_phrase(update, context, phrase['ukrainian'], voice_id)
    
    return LESSON


async def start_dialog_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начать режим диалога"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    user_info["mode"] = DIALOG
    user_info["dialog_context"] = []
    
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
    
    # Отправляем приветствие голосом
    voice_id = UKRAINIAN_VOICES.get(user_info.get("voice", DEFAULT_VOICE))
    greeting = "Привіт! Як справи? Давай спілкуватися по-українськи!"
    audio_data = await generate_speech_elevenlabs(greeting, voice_id)
    if audio_data:
        await update.message.reply_voice(
            voice=io.BytesIO(audio_data),
            caption="🔊 Послушай приветствие"
        )
    
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
    
    return await process_dialog_message(update, context, user_message, user_info)


async def start_translate_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начать упражнения на перевод"""
    user_id = update.effective_user.id
    user_info = get_user_data(user_id)
    user_info["mode"] = TRANSLATE
    
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
    
    # Отправляем вопрос голосом
    voice_id = UKRAINIAN_VOICES.get(user_info.get("voice", DEFAULT_VOICE))
    question = f"Переклади на українську: {exercise['russian']}"
    audio_data = await generate_speech_elevenlabs(question, voice_id)
    if audio_data:
        await update.message.reply_voice(
            voice=io.BytesIO(audio_data),
            caption="🔊 Послушай вопрос"
        )
    
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
    
    # Отправляем приглашение голосом
    voice_id = UKRAINIAN_VOICES.get(user_info.get("voice", DEFAULT_VOICE))
    invitation = "Яке у тебе питання про українську мову?"
    audio_data = await generate_speech_elevenlabs(invitation, voice_id)
    if audio_data:
        await update.message.reply_voice(
            voice=io.BytesIO(audio_data),
            caption="🔊 Послушай вопрос"
        )
    
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
        response = openai_client.chat.completions.create(
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
        parts = data.split("_")
        topic_id = parts[1]
        phrase_idx = int(parts[2])
        
        topic = DISCOVERY_LESSONS.get(topic_id)
        if topic and phrase_idx < len(topic["phrases"]):
            phrase = topic["phrases"][phrase_idx]
            voice_id = UKRAINIAN_VOICES.get(user_info.get("voice", DEFAULT_VOICE))
            await send_voice_phrase(update, context, phrase["ukrainian"], voice_id)
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
    
    # Обработчик ошибок для Conflict ошибок
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(f"Update {update} caused error {context.error}")
        if "Conflict" in str(context.error):
            logger.warning("Conflict error detected, restarting...")
            return
    
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
    application.add_error_handler(error_handler)
    
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
