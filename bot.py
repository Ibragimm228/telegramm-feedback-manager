import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
import asyncio
import json
import os
 
logging.basicConfig(level=logging.INFO)
 
BOT_TOKEN = '@BotFather'
GROUP_ID = -100..... 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DATA_FILE = 'bot_data.json'

user_messages = {}
blocked_users = set()
user_info = {}
username_to_id = {}
user_topics = {} 
def save_data():
    data = {
        'blocked_users': list(blocked_users),
        'user_info': user_info,
        'username_to_id': username_to_id,
        'user_topics': user_topics
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info("Данные сохранены")

def load_data():
    global blocked_users, user_info, username_to_id, user_topics
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            blocked_users = set(data.get('blocked_users', []))
            user_info = data.get('user_info', {})
            user_info = {int(k): v for k, v in user_info.items()}
            username_to_id = data.get('username_to_id', {})
            username_to_id = {k: int(v) for k, v in username_to_id.items()}
            user_topics = data.get('user_topics', {})
            user_topics = {int(k): int(v) for k, v in user_topics.items()}
            logging.info(f"Данные загружены. Топики: {user_topics}")
        except Exception as e:
            logging.error(f"Ошибка загрузки данных: {e}")

async def get_or_create_topic(user_id: int, username: str) -> int:
    user_id = int(user_id)
    
    if user_id in user_topics:
        logging.info(f"Топик для пользователя {user_id} уже существует: {user_topics[user_id]}")
        return user_topics[user_id]
    
    try:
        topic_name = f"@{username}" if username != "без username" else f"User {user_id}"
        forum_topic = await bot.create_forum_topic(GROUP_ID, topic_name)
        topic_id = forum_topic.message_thread_id
        
        user_topics[user_id] = topic_id
        save_data()
        
        logging.info(f"Создан топик {topic_name} (ID: {topic_id}) для пользователя {user_id}")
        logging.info(f"Текущие топики: {user_topics}")
        return topic_id
    except Exception as e:
        logging.error(f"Ошибка создания топика: {e}")
        raise

@dp.message(Command("getid"))
async def get_chat_id(message: Message):
    chat_info = f"""
╔════════════════════════════════════════╗
║         ИНФОРМАЦИЯ О ЧАТЕ              ║
╠════════════════════════════════════════╣
║ 📍 Chat ID: {message.chat.id}
║ 📍 Chat Type: {message.chat.type}
║ 📍 Chat Title: {message.chat.title if message.chat.title else 'Личные сообщения'}
╠════════════════════════════════════════╣
"""
    
    if message.chat.type in ['group', 'supergroup']:
        chat_info += f"""║ ✅ Это {'супер' if message.chat.type == 'supergroup' else ''}группа!
║ 
║  Скопируйте этот ID:
║ GROUP_ID = {message.chat.id}
║ 
║ Вставьте в строку 12 файла bot.py
╚════════════════════════════════════════╝"""
    else:
        chat_info += """║ ❌ Это не группа!
║ Используйте команду /getid в группе
╚════════════════════════════════════════╝"""
    
    await message.answer(chat_info)
    print(chat_info) 

@dp.message(Command("start"))
async def start_handler(message: Message):
    if message.chat.id == GROUP_ID:
        await message.answer("Панель управления активна\n\nКоманды:\n/block - заблокировать (reply на сообщение)\n/unblock - разблокировать (reply на сообщение)\n/topics - показать все топики\n\nЧтобы ответить пользователю, просто напишите в его топик")
    else:
        await message.answer("Привет! Отправь мне свое сообщение")

@dp.message(Command("topics"))
async def show_topics_handler(message: Message):
    if message.chat.id != GROUP_ID:
        return
    
    if not user_topics:
        await message.answer("Топиков пока нет")
        return
    
    topics_info = "📋 **Активные топики:**\n\n"
    for user_id, topic_id in user_topics.items():
        username = user_info.get(user_id, "неизвестный")
        topics_info += f"👤 @{username} (ID: {user_id}) → Топик ID: {topic_id}\n"
    
    await message.answer(topics_info, parse_mode="Markdown")

@dp.message(Command("block"))
async def block_handler(message: Message):
    if message.chat.id != GROUP_ID:
        return
    
    if not message.reply_to_message:
        await message.answer("Ответьте на сообщение пользователя")
        return
    
    msg_id = message.reply_to_message.message_id
    if msg_id in user_messages:
        user_id = user_messages[msg_id]
        blocked_users.add(user_id)
        save_data()
        username = user_info.get(user_id, "без username")
        await message.answer(f"Пользователь @{username} заблокирован")
    else:
        await message.answer("Не удалось найти пользователя")

@dp.message(Command("unblock"))
async def unblock_handler(message: Message):
    if message.chat.id != GROUP_ID:
        return
    
    if not message.reply_to_message:
        await message.answer("Ответьте на сообщение пользователя")
        return
    
    msg_id = message.reply_to_message.message_id
    if msg_id in user_messages:
        user_id = user_messages[msg_id]
        if user_id in blocked_users:
            blocked_users.remove(user_id)
            save_data()
            username = user_info.get(user_id, "без username")
            await message.answer(f"Пользователь @{username} разблокирован")
        else:
            await message.answer("Пользователь не был заблокирован")
    else:
        await message.answer("Не удалось найти пользователя")

@dp.message(F.chat.id == GROUP_ID)
async def group_message_handler(message: Message):
    if message.text and message.text.startswith('/'):
        return

    if not message.message_thread_id:
        return
    
    user_id = None

    for uid, topic_id in user_topics.items():
        if topic_id == message.message_thread_id:
            user_id = uid
            logging.info(f"Найден пользователь {uid} для топика {topic_id}")
            break

    if not user_id and message.reply_to_message:
        msg_id = message.reply_to_message.message_id
        if msg_id in user_messages:
            user_id = user_messages[msg_id]
            logging.info(f"Найден пользователь {user_id} по reply")
    
    if not user_id:
        logging.warning(f"Не найден пользователь для топика {message.message_thread_id}")
        return
    
    try:
        if message.text:
            await bot.send_message(user_id, message.text)
        elif message.photo:
            await bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption)
        elif message.video:
            await bot.send_video(user_id, message.video.file_id, caption=message.caption)
        elif message.voice:
            await bot.send_voice(user_id, message.voice.file_id)
        elif message.video_note:
            await bot.send_video_note(user_id, message.video_note.file_id)
        elif message.document:
            await bot.send_document(user_id, message.document.file_id, caption=message.caption)
        elif message.audio:
            await bot.send_audio(user_id, message.audio.file_id, caption=message.caption)
        elif message.sticker:
            await bot.send_sticker(user_id, message.sticker.file_id)
        
        if message.message_thread_id:
            user_messages[message.message_id] = user_id
        
        await message.answer("✅ Отправлено")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message()
async def user_message_handler(message: Message):
    if message.chat.id == GROUP_ID:
        return
    
    if message.from_user.id in blocked_users:
        return
    
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else "без username"
    
    if user_info.get(user_id) != username:
        user_info[user_id] = username
        if message.from_user.username:
            username_to_id[message.from_user.username] = user_id
        save_data()
    
    try:
        topic_id = await get_or_create_topic(user_id, username)
        
        if message.text:
            sent = await bot.send_message(GROUP_ID, message.text, message_thread_id=topic_id)
        elif message.photo:
            sent = await bot.send_photo(GROUP_ID, message.photo[-1].file_id, caption=message.caption, message_thread_id=topic_id)
        elif message.video:
            sent = await bot.send_video(GROUP_ID, message.video.file_id, caption=message.caption, message_thread_id=topic_id)
        elif message.voice:
            sent = await bot.send_voice(GROUP_ID, message.voice.file_id, message_thread_id=topic_id)
        elif message.video_note:
            sent = await bot.send_video_note(GROUP_ID, message.video_note.file_id, message_thread_id=topic_id)
        elif message.document:
            sent = await bot.send_document(GROUP_ID, message.document.file_id, caption=message.caption, message_thread_id=topic_id)
        elif message.audio:
            sent = await bot.send_audio(GROUP_ID, message.audio.file_id, caption=message.caption, message_thread_id=topic_id)
        elif message.sticker:
            sent = await bot.send_sticker(GROUP_ID, message.sticker.file_id, message_thread_id=topic_id)
        else:
            return
        
        user_messages[sent.message_id] = user_id
        await message.answer("Сообщение отправлено")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer("Произошла ошибка при отправке сообщения")

async def main():
    load_data()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())