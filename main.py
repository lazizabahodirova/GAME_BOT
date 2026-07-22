import asyncio
import sqlite3
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- SOZLAMALAR ---
API_TOKEN = '7752496700:AAGeDWZf65Yi5T9XRBy7t9_r1grDtgaZ6DA' 
ADMIN_ID = 8320643359 
ADMIN_CHANNEL_ID = -1004343145305 
KARTA_RAQAM = "6262 5700 8837 1937" 
KARTA_EGASI = "SHERBEK NIZOMIDDINOV"

logging.basicConfig(level=logging.INFO)

GENRES = ["🚗 Car Games", "🔫 Action Games", "🧟 Horror Games", "⚽ Sports Games", 
          "🌍 Open World", "🧩 Offline Games", "🌐 Online Games", "💎 MOD APK"]

# --- BAZA ---
def init_db():
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS games 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       genre TEXT, name TEXT, description TEXT, 
                       photo_id TEXT, file_id TEXT)''')
    conn.commit()
    conn.close()

class AddGame(StatesGroup):
    waiting_for_genre = State()
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_photo = State()
    waiting_for_file = State()

class OrderGame(StatesGroup): 
    waiting_for_order_text = State()

class AdminReply(StatesGroup): 
    waiting_for_text = State()

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- KLAVIATURALAR ---
def get_genres_kb():
    builder = ReplyKeyboardBuilder()
    for genre in GENRES:
        builder.add(KeyboardButton(text=genre))
    builder.add(KeyboardButton(text="🎁 O'yin zakas berish"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_games_by_genre_kb(genre_name):
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM games WHERE genre=?", (genre_name,))
    games = cursor.fetchall()
    conn.close()
    
    if not games:
        return None
    builder = ReplyKeyboardBuilder()
    for game in games:
        builder.add(KeyboardButton(text=game[0]))
    builder.add(KeyboardButton(text="⬅️ Orqaga"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_user_pay_kb(game_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 Naxt orqali", callback_data=f"upay_cash_{game_id}")
    builder.button(text="💳 Karta orqali", callback_data=f"upay_card_{game_id}")
    builder.adjust(2)
    return builder.as_markup()

def get_admin_action_kb(user_id, game_id="0"):
    builder = InlineKeyboardBuilder()
    if game_id != "0":
        builder.button(text="✅ Tasdiqlash", callback_data=f"adm_conf_{user_id}_{game_id}")
    else:
        builder.button(text="✅ To'lovni Tasdiqlash (Zakaz)", callback_data=f"adm_conf_{user_id}_0")
    builder.button(text="💬 Fikr bildirish", callback_data=f"adm_msg_{user_id}")
    builder.adjust(1)
    return builder.as_markup()

# ===================== ADMIN: O'YIN QO'SHISH =====================
@dp.message(Command("add"), F.from_user.id == ADMIN_ID)
async def add_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("📌 **Qaysi janrga o'yin qo'shmoqchisiz?**", 
                        reply_markup=get_genres_kb())
    await state.set_state(AddGame.waiting_for_genre)

@dp.message(AddGame.waiting_for_genre, F.text.in_(GENRES))
async def add_genre_selected(message: Message, state: FSMContext):
    await state.update_data(genre=message.text)
    await message.answer(f"✅ Tanlandi: **{message.text}**\n\n📝 O'yin nomini yuboring:", 
                        reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddGame.waiting_for_name)

@dp.message(AddGame.waiting_for_name)
async def add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("📄 O'yin haqida izoh yozing (description):")
    await state.set_state(AddGame.waiting_for_description)

@dp.message(AddGame.waiting_for_description)
async def add_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("📸 O'yinning rasmini yuboring:")
    await state.set_state(AddGame.waiting_for_photo)

@dp.message(AddGame.waiting_for_photo, F.photo)
async def add_photo(message: Message, state: FSMContext):
    await state.update_data(photo_id=message.photo[-1].file_id)
    await message.answer("📁 O'yin faylini yuboring (document/video):")
    await state.set_state(AddGame.waiting_for_file)

@dp.message(AddGame.waiting_for_file, F.document | F.video)
async def add_file(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.document.file_id if message.document else message.video.file_id
    
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO games 
                      (genre, name, description, photo_id, file_id) 
                      VALUES (?, ?, ?, ?, ?)""", 
                   (data['genre'], data['name'], data['description'], 
                    data['photo_id'], file_id))
    conn.commit()
    conn.close()

    await message.answer(f"✅ **{data['name']}** o'yini muvaffaqiyatli qo'shildi!", 
                        reply_markup=get_genres_kb())
    await state.clear()

# ===================== QOLGAN KOD (o'zgartirishsiz) =====================
# ... (oldingi kodingizdagi boshqa handlerlarning hammasi o'zgarmadi)

@dp.message(F.chat.id == ADMIN_CHANNEL_ID)
async def admin_group_manager(message: Message, state: FSMContext):
    cur_state = await state.get_state()
    if cur_state == AdminReply.waiting_for_text:
        data = await state.get_data()
        try:
            await bot.send_message(data['target_id'], f"👨‍💻 Admin: {message.text}")
            await message.reply("✅ Xabar yuborildi.")
        except:
            await message.reply("❌ Foydalanuvchi botni bloklagan.")
        await state.clear()
        return

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        text = message.reply_to_message.text or message.reply_to_message.caption or ""
        match = re.search(r"ID: (\d+)", text)
        if match:
            user_id = match.group(1)
            if message.document or message.video or message.audio:
                try:
                    await bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, 
                                         message_id=message.message_id, 
                                         caption="🎮 Mana siz so'ragan o'yin! Yuklab oling.")
                    await message.reply(f"✅ Fayl foydalanuvchiga yuborildi!")
                except:
                    await message.reply("❌ Faylni yuborib bo'lmadi.")
            elif message.text:
                try:
                    await bot.send_message(user_id, f"👨‍💻 Admin: {message.text}")
                    await message.reply("✅ Xabar yuborildi.")
                except:
                    await message.reply("❌ Yuborib bo'lmadi.")

# Qolgan barcha handlerlaringizni (start, genre ko'rsatish, zakaz va boshqalar) 
# o'zingizning eski kodingizdan nusxa ko'chirib qo'ying. Ular o'zgarmagan.

async def main():
    init_db()
    print("✅ Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())