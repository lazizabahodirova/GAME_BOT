import asyncio
import sqlite3
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- SOZLAMALAR ---
API_TOKEN = '7752496700:AAGeDWZf65Yi5T9XRBy7t9_r1grDtgaZ6DA'
ADMIN_ID = 8320643359 # Sizning ID
ADMIN_CHANNEL_ID = -1004343145305 # Guruh ID (manfiy son bo'lishi shart)
KARTA_RAQAM = "6262 5700 8837 1937"
KARTA_EGASI = "SHERBEK NIZOMIDDINOV"

logging.basicConfig(level=logging.INFO)

GENRES = [
    "🚗 Car Games", "🔫 Action Games", "🧟 Horror Games", "⚽ Sports Games",
    "🌍 Open World", "🧩 Offline Games", "🌐 Online Games", "💎 MOD APK"
]

# --- BAZA ---
def init_db():
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS games
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      genre TEXT,
                      name TEXT,
                      description TEXT,
                      photo_id TEXT,
                      file_id TEXT)''')
    conn.commit()
    conn.close()

# --- STATES ---
class AddGame(StatesGroup):
    waiting_for_genre = State()
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_photo = State()
    waiting_for_file = State()

class OrderGame(StatesGroup):
    waiting_for_order_text = State()

class Feedback(StatesGroup):
    waiting_for_feedback = State()

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

def get_games_by_genre_kb(genre_name: str):
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM games WHERE genre=?", (genre_name,))
    games = cursor.fetchall()
    conn.close()
    if not games: return None
    builder = ReplyKeyboardBuilder()
    for game in games:
        builder.add(KeyboardButton(text=game[0]))
    builder.add(KeyboardButton(text="⬅️ Orqaga"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# ================= HANDLERLAR =================

@dp.message(Command("start"), F.chat.type == "private")
@dp.message(F.text == "⬅️ Orqaga", F.chat.type == "private")
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("📁 Janrni tanlang yoki buyurtma bering:", reply_markup=get_genres_kb())

# 1. ADMIN O'YIN QO'SHISH (/add)
@dp.message(Command("add"), F.from_user.id == ADMIN_ID)
async def add_start(message: Message, state: FSMContext):
    await message.answer("Qaysi janrga o'yin qo'shmoqchisiz?", reply_markup=get_genres_kb())
    await state.set_state(AddGame.waiting_for_genre)

@dp.message(AddGame.waiting_for_genre)
async def add_g_genre(message: Message, state: FSMContext):
    if message.text in GENRES:
        await state.update_data(genre=message.text)
        await message.answer("O'yin nomini yozib yuboring!", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(AddGame.waiting_for_name)
    else:
        await message.answer("Iltimos, menyudagi janrlardan birini tanlang!")

@dp.message(AddGame.waiting_for_name)
async def add_g_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("O'yin uchun izoh (tavsif) yuboring:")
    await state.set_state(AddGame.waiting_for_description)

@dp.message(AddGame.waiting_for_description)
async def add_g_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer("O'yin uchun rasm yuboring:")
    await state.set_state(AddGame.waiting_for_photo)

@dp.message(AddGame.waiting_for_photo, F.photo)
async def add_g_photo(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("Endi o'yin faylini (document) yuboring:")
    await state.set_state(AddGame.waiting_for_file)

@dp.message(AddGame.waiting_for_file, F.document)
async def add_g_file(message: Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO games (genre, name, description, photo_id, file_id) VALUES (?, ?, ?, ?, ?)",
                   (data['genre'], data['name'], data['desc'], data['photo'], message.document.file_id))
    conn.commit()
    conn.close()
    await message.answer(f"✅ O'yin '{data['name']}' bazaga muvaffaqiyatli qo'shildi!", reply_markup=get_genres_kb())
    await state.clear()

# 2. FOYDALANUVCHI O'YIN TANLASHI
@dp.message(F.text.in_(GENRES), F.chat.type == "private")
async def show_games(message: Message):
    kb = get_games_by_genre_kb(message.text)
    if kb:
        await message.answer(f"✅ {message.text} janridagi o'yinlar:", reply_markup=kb)
    else:
        await message.answer("⚠️ Bu janrda hozircha o'yinlar yo'q.")

@dp.message(F.text, F.chat.type == "private", StateFilter(None))
async def game_detail(message: Message):
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, photo_id FROM games WHERE name=?", (message.text,))
    game = cursor.fetchone()
    conn.close()

    if game:
        g_id, name, desc, photo = game
        kb = InlineKeyboardBuilder()
        kb.button(text="📥 O'yin faylini yuklab olish", callback_data=f"get_file_{g_id}")
        await message.answer_photo(photo=photo, caption=f"🎮 **{name}**\n\n📝 {desc}", reply_markup=kb.as_markup(), parse_mode="Markdown")

# 3. TO'LOV TIZIMI
@dp.callback_query(F.data.startswith("get_file_"))
async def choose_payment(callback: CallbackQuery):
    g_id = callback.data.split("_")[2]
    kb = InlineKeyboardBuilder()
    kb.button(text="💵 Naxt orqali", callback_data=f"pay_cash_{g_id}")
    kb.button(text="💳 Karta orqali", callback_data=f"pay_card_{g_id}")
    await callback.message.answer("To'lov usulini tanlang:", reply_markup=kb.as_markup())
    await callback.answer()

# NAXT ORQALI
@dp.callback_query(F.data.startswith("pay_cash_"))
async def pay_cash(callback: CallbackQuery):
    g_id = callback.data.split("_")[2]
    user = callback.from_user
    
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, genre FROM games WHERE id=?", (g_id,))
    game = cursor.fetchone()
    conn.close()

    admin_msg = (
        f"💵 **Naxt to'lov so'rovi!**\n\n"
        f"👤 Foydalanuvchi: @{user.username or 'username_yoq'}\n"
        f"🆔 ID: `{user.id}`\n"
        f"🎮 O'yin: {game[0]} ({game[1]})\n"
        f"Fikringiz bo'lsa yozib qoldiring."
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data=f"admin_confirm_{user.id}_{g_id}")
    
    await bot.send_message(ADMIN_CHANNEL_ID, admin_msg, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.message.answer("✅ Adminga so'rov yuborildi. Tasdiqlanganidan so'ng o'yin yuboriladi.")
    await callback.answer()

# KARTA ORQALI
@dp.callback_query(F.data.startswith("pay_card_"))
async def pay_card(callback: CallbackQuery):
    g_id = callback.data.split("_")[2]
    text = f"💳 **Karta orqali to'lov**\n\nRaqam: `{KARTA_RAQAM}`\nEga: {KARTA_EGASI}\n\nTo'lov qilganingizdan so'ng 'To'lov qildim' (Fikr qoldirish) tugmasi orqali xabar bering."
    
    kb = InlineKeyboardBuilder()
    # Telegram avtomatik ilovani ochishga harakat qiladi (deep link)
    kb.button(text="📱 To'lov qilish (Click/Payme)", url="https://payme.uz/@sherbek_nizomiddinov") 
    kb.button(text="💬 Fikr qoldirish / To'lov qildim", callback_data=f"feedback_{g_id}")
    kb.adjust(1)
    
    await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.answer()

# 4. FIKR QOLDIRISH VA ZAKAS BERISH
@dp.message(F.text == "🎁 O'yin zakas berish")
async def zakas_start(message: Message, state: FSMContext):
    await message.answer("📝 Qaysi o'yinni zakas qilmoqchisiz? Nomini yozing:")
    await state.set_state(OrderGame.waiting_for_order_text)

@dp.message(OrderGame.waiting_for_order_text)
async def zakas_done(message: Message, state: FSMContext):
    msg = f"🎁 **Yangi o'yin zakazi!**\n\n👤 @{message.from_user.username}\n🆔 ID: `{message.from_user.id}`\n📩 O'yin: {message.text}"
    await bot.send_message(ADMIN_CHANNEL_ID, msg, parse_mode="Markdown")
    await message.answer("✅ Zakazingiz adminga yetkazildi.")
    await state.clear()

@dp.callback_query(F.data.startswith("feedback_"))
async def feedback_start(callback: CallbackQuery, state: FSMContext):
    g_id = callback.data.split("_")[1]
    await state.update_data(f_game_id=g_id)
    await callback.message.answer("✍️ Muammo yoki to'lov haqida yozing (masalan: 'To'lov qildim'):")
    await state.set_state(Feedback.waiting_for_feedback)
    await callback.answer()

@dp.message(Feedback.waiting_for_feedback)
async def feedback_done(message: Message, state: FSMContext):
    data = await state.get_data()
    g_id = data.get("f_game_id")
    
    msg = (f"💬 **To'lov / Muammo haqida fikr**\n\n"
           f"👤 @{message.from_user.username}\n"
           f"🆔 ID: `{message.from_user.id}`\n"
           f"🎮 O'yin ID: {g_id}\n"
           f"📩 Xabar: {message.text}")
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash (Faylni yuborish)", callback_data=f"admin_confirm_{message.from_user.id}_{g_id}")
    
    await bot.send_message(ADMIN_CHANNEL_ID, msg, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await message.answer("✅ Xabaringiz adminga yuborildi.")
    await state.clear()

# 5. ADMIN TASDIQLASHI VA REPLY
@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(callback: CallbackQuery):
    parts = callback.data.split("_")
    u_id, g_id = parts[2], parts[3]
    
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, name FROM games WHERE id=?", (g_id,))
    game = cursor.fetchone()
    conn.close()

    if game:
        try:
            await bot.send_document(chat_id=u_id, document=game[0], caption=f"✅ To'lovingiz tasdiqlandi!\n🎮 O'yin: {game[1]}")
            await callback.message.edit_text(callback.message.text + "\n\n✅ **FOYDALANUVCHIGA YUBORILDI**")
        except:
            await callback.answer("Foydalanuvchi botni bloklagan bo'lishi mumkin!", show_alert=True)
    else:
        await callback.answer("O'yin topilmadi!")

@dp.message(F.chat.id == ADMIN_CHANNEL_ID, F.reply_to_message)
async def admin_reply(message: Message):
    orig_text = message.reply_to_message.text or message.reply_to_message.caption
    if not orig_text: return

    match = re.search(r"🆔 ID: `?(\d+)`?", orig_text)
    if match:
        user_id = match.group(1)
        try:
            await bot.send_message(user_id, f"👨‍💻 **Admin:** {message.text}")
            await message.reply("✅ Foydalanuvchiga javobingiz yuborildi.")
        except:
            await message.reply("❌ Yuborishda xato.")

# ================= MAIN =================
async def main():
    init_db()
    print("Bot ishlamoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())