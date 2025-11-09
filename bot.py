import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
import asyncio
import json
import os

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = '@BotFather'
OWNER_ID = @userinfobot

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DATA_FILE = 'bot_data.json'

user_messages = {}
blocked_users = set()
user_info = {}
username_to_id = {}

def save_data():
    data = {
        'blocked_users': list(blocked_users),
        'user_info': user_info,
        'username_to_id': username_to_id
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info("Данные сохранены")

def load_data():
    global blocked_users, user_info, username_to_id
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            blocked_users = set(data.get('blocked_users', []))
            user_info = data.get('user_info', {})
            user_info = {int(k): v for k, v in user_info.items()}
            username_to_id = data.get('username_to_id', {})
            username_to_id = {k: int(v) for k, v in username_to_id.items()}
            logging.info("Данные загружены")
        except Exception as e:
            logging.error(f"Ошибка загрузки данных: {e}")

@dp.message(Command("start"))
async def start_handler(message: Message):
    if message.from_user.id == OWNER_ID:
        await message.answer("Панель владельца активна\n\nКоманды:\n/block - заблокировать (reply на сообщение)\n/unblock - разблокировать (reply на сообщение)\n\nЧтобы написать пользователю:\n@username текст сообщения")
    else:
        await message.answer("Привет! Отправь мне свое сообщение")

@dp.message(Command("block"))
async def block_handler(message: Message):
    if message.from_user.id != OWNER_ID:
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
    if message.from_user.id != OWNER_ID:
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

@dp.message(F.chat.id == OWNER_ID)
async def owner_message_handler(message: Message):
    if message.reply_to_message:
        msg_id = message.reply_to_message.message_id
        if msg_id not in user_messages:
            return
        
        user_id = user_messages[msg_id]
    elif message.text and message.text.startswith('@'):
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            await message.answer("Формат: @username текст сообщения")
            return
        
        username = parts[0][1:]
        text = parts[1]
        
        if username not in username_to_id:
            await message.answer(f"Пользователь @{username} не найден")
            return
        
        user_id = username_to_id[username]
        
        try:
            await bot.send_message(user_id, text)
            await message.answer(f"Сообщение отправлено @{username}")
            return
        except Exception as e:
            await message.answer(f"Ошибка отправки: {e}")
            return
    else:
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
        
        await message.answer("Ответ отправлен")
    except Exception as e:
        await message.answer(f"Ошибка отправки: {e}")

@dp.message()
async def user_message_handler(message: Message):
    if message.from_user.id == OWNER_ID:
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
        if message.text:
            sent = await bot.send_message(OWNER_ID, f"Новое сообщение от @{username}:\n\n{message.text}")
        elif message.photo:
            caption = f"Новое фото от @{username}{f': {message.caption}' if message.caption else ''}"
            sent = await bot.send_photo(OWNER_ID, message.photo[-1].file_id, caption=caption)
        elif message.video:
            caption = f"Новое видео от @{username}{f': {message.caption}' if message.caption else ''}"
            sent = await bot.send_video(OWNER_ID, message.video.file_id, caption=caption)
        elif message.voice:
            sent = await bot.send_voice(OWNER_ID, message.voice.file_id, caption=f"Новое голосовое от @{username}")
        elif message.video_note:
            sent = await bot.send_video_note(OWNER_ID, message.video_note.file_id)
            await bot.send_message(OWNER_ID, f"Новое видео-сообщение от @{username}")
        elif message.document:
            caption = f"Новый файл от @{username}{f': {message.caption}' if message.caption else ''}"
            sent = await bot.send_document(OWNER_ID, message.document.file_id, caption=caption)
        elif message.audio:
            caption = f"Новое аудио от @{username}{f': {message.caption}' if message.caption else ''}"
            sent = await bot.send_audio(OWNER_ID, message.audio.file_id, caption=caption)
        elif message.sticker:
            sent = await bot.send_sticker(OWNER_ID, message.sticker.file_id)
            await bot.send_message(OWNER_ID, f"Новый стикер от @{username}")
        else:
            return
        
        user_messages[sent.message_id] = user_id
        await message.answer("Сообщение отправлено")
        
    except Exception as e:
        logging.error(f"Error: {e}")

async def main():
    load_data()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
