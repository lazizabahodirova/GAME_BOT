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
ADMIN_ID = 8320643359 
ADMIN_CHANNEL_ID = -1004343145305 # Guruh IDsi
KARTA_RAQAM = "6262 5700 8837 1937" 
KARTA_EGASI = "SHERBEK NIZOMIDDINOV"

logging.basicConfig(level=logging.INFO)

GENRES = ["🚗 Car Games", "🔫 Action Games", "🧟 Horror Games", "⚽ Sports Games", "🌍 Open World", "🧩 Offline Games", "🌐 Online Games", "💎 MOD APK"]

# --- BAZA ---
def init_db():
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, genre TEXT, name TEXT, description TEXT, photo_id TEXT, file_id TEXT)''')
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
    for genre in GENRES: builder.add(KeyboardButton(text=genre))
    builder.add(KeyboardButton(text="🎁 O'yin zakas berish"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_games_by_genre_kb(genre_name):
    conn = sqlite3.connect('games_bot.db'); cursor = conn.cursor()
    cursor.execute("SELECT name FROM games WHERE genre=?", (genre_name,))
    games = cursor.fetchall(); conn.close()
    if not games: return None
    builder = ReplyKeyboardBuilder()
    for game in games: builder.add(KeyboardButton(text=game[0]))
    builder.add(KeyboardButton(text="⬅️ Orqaga")); builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# --- FOYDALANUVCHI AMALLARI ---

@dp.message(Command("start"), F.chat.type == "private")
@dp.message(F.text == "⬅️ Orqaga", F.chat.type == "private")
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("📁 Janrni tanlang yoki buyurtma bering:", reply_markup=get_genres_kb())

@dp.message(F.text.in_(GENRES), F.chat.type == "private")
async def show_genre_games(message: Message):
    kb = get_games_by_genre_kb(message.text)
    if kb: await message.answer(f"✅ {message.text} o'yinlari:", reply_markup=kb)
    else: await message.answer("⚠️ Ushbu janrda hali o'yinlar yo'q.")

# 1. O'YIN TANLANGANDA RASM VA IZOH CHIQARISH
@dp.message(F.text, F.chat.type == "private", StateFilter(None))
async def handle_game_selection(message: Message):
    conn = sqlite3.connect('games_bot.db'); cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, photo_id FROM games WHERE name=?", (message.text,))
    game = cursor.fetchone(); conn.close()
    
    if game:
        game_id, name, desc, photo_id = game
        kb = InlineKeyboardBuilder()
        kb.button(text="📥 Faylni yuklab olish", callback_data=f"get_file_{game_id}")
        
        await message.answer_photo(
            photo=photo_id,
            caption=f"🎮 **{name}**\n\n📝 {desc}",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )

# 2. YUKLAB OLISH BOSILGANDA TO'LOV TURLARI
@dp.callback_query(F.data.startswith("get_file_"))
async def show_payment_methods(callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    
    kb = InlineKeyboardBuilder()
    kb.button(text="💵 Naxt orqali", callback_data=f"pay_cash_{game_id}")
    kb.button(text="💳 Karta orqali", callback_data=f"pay_card_{game_id}")
    kb.adjust(2)
    
    await callback.message.answer(
        "Faylni yuklab olish uchun to'lov qilishingiz kerak. To'lov turini tanlang:",
        reply_markup=kb.as_markup()
    )
    await callback.answer()

# 3. NAQD TO'LOV TANLANGANDA
@dp.callback_query(F.data.startswith("pay_cash_"))
async def process_pay_cash(callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    user = callback.from_user
    
    # Guruhga xabar yuborish
    admin_text = (f"💵 **Naxt to'lov tanlandi!**\n\n"
                  f"👤 Foydalanuvchi: @{user.username or 'Yashirin'}\n"
                  f"🆔 ID: {user.id}\n"
                  f"🎮 O'yin ID: {game_id}\n\n"
                  f"Fikringizni qoldiring (Reply qilib javob yozing).")
    
    await bot.send_message(ADMIN_CHANNEL_ID, admin_text)
    await callback.message.answer("Adminga so'rov yuborildi. Admin javobini kuting...")
    await callback.answer()

# 4. KARTA ORQALI TO'LOV TANLANGANDA
@dp.callback_query(F.data.startswith("pay_card_"))
async def process_pay_card(callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ To'lov qilish", callback_data=f"card_paid_{game_id}")
    
    text = (f"💳 **Karta orqali to'lov**\n\n"
            f"Raqam: `{KARTA_RAQAM}`\n"
            f"Ega: {KARTA_EGASI}\n\n"
            f"To'lovni amalga oshirgach 'To'lov qilish' tugmasini bosing.")
    
    await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.answer()

# 5. KARTA TO'LOVI TASDIQLASH SO'ROVI
@dp.callback_query(F.data.startswith("card_paid_"))
async def process_card_paid(callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    user = callback.from_user
    
    await callback.message.answer("To'lovingiz tasdiqlanmoqda...")
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ To'lovni tasdiqlash", callback_data=f"admin_confirm_{user.id}_{game_id}")
    
    admin_text = (f"💳 **Karta orqali to'lov so'rovi!**\n\n"
                  f"👤 Foydalanuvchi: @{user.username or 'Yashirin'}\n"
                  f"🆔 ID: {user.id}\n"
                  f"Kartangizni tekshirib ko'ring, pul tushgan bo'lsa tasdiqlash tugmasini bosing.")
    
    await bot.send_message(ADMIN_CHANNEL_ID, admin_text, reply_markup=kb.as_markup())
    await callback.answer()

# 6. ADMIN TASDIQLAGANDA FAYLNI YUBORISH
@dp.callback_query(F.data.startswith("admin_confirm_"))
async def final_confirm(callback: CallbackQuery):
    _, _, user_id, game_id = callback.data.split("_")
    
    conn = sqlite3.connect('games_bot.db'); cursor = conn.cursor()
    cursor.execute("SELECT file_id, name FROM games WHERE id=?", (game_id,))
    game = cursor.fetchone(); conn.close()
    
    if game:
        try:
            await bot.send_document(user_id, document=game[0], caption=f"✅ To'lovingiz tasdiqlandi! \n🎮 O'yin: {game[1]}")
            await callback.message.edit_text(callback.message.text + f"\n\n✅ Tasdiqlandi, foydalanuvchiga fayl yuborildi!")
        except Exception as e:
            await callback.message.answer(f"Xatolik: {e}")
    await callback.answer()

# --- ADMIN: REPLY VA O'YIN QO'SHISH ---

@dp.message(F.chat.id == ADMIN_CHANNEL_ID, F.reply_to_message)
async def admin_reply_handler(message: Message):
    # Reply qilingan xabardan foydalanuvchi ID sini qidirish
    original_text = message.reply_to_message.text or message.reply_to_message.caption
    if original_text:
        match = re.search(r"🆔 ID: (\d+)", original_text)
        if match:
            user_id = match.group(1)
            try:
                await bot.send_message(user_id, f"👨‍💻 Admin javobi: {message.text}")
                await message.reply("✅ Foydalanuvchiga yetkazildi.")
            except:
                await message.reply("❌ Foydalanuvchiga yuborib bo'lmadi.")

# --- O'YIN QO'SHISH (ESKI KODINGIZDAN) ---
@dp.message(Command("add"), F.from_user.id == ADMIN_ID)
async def add_start(m: Message, state: FSMContext):
    await m.answer("Qaysi janrga o'yin qo'shmoqchisiz?", reply_markup=get_genres_kb())
    await state.set_state(AddGame.waiting_for_genre)

@dp.message(AddGame.waiting_for_genre, F.text.in_(GENRES))
async def add_g1(m: Message, state: FSMContext):
    await state.update_data(genre=m.text)
    await m.answer(f"O'yin nomini yozib yuboring!", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddGame.waiting_for_name)

@dp.message(AddGame.waiting_for_name)
async def add_g2(m: Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("O'yin uchun izoh yozib yuboring!")
    await state.set_state(AddGame.waiting_for_description)

@dp.message(AddGame.waiting_for_description)
async def add_g3(m: Message, state: FSMContext):
    await state.update_data(desc=m.text)
    await m.answer("O'yin rasmini yuboring:")
    await state.set_state(AddGame.waiting_for_photo)

@dp.message(AddGame.waiting_for_photo, F.photo)
async def add_g4(m: Message, state: FSMContext):
    await state.update_data(photo=m.photo[-1].file_id)
    await m.answer("O'yin faylini yuboring (Document):")
    await state.set_state(AddGame.waiting_for_file)

@dp.message(AddGame.waiting_for_file, F.document)
async def add_g5(m: Message, state: FSMContext):
    d = await state.get_data()
    conn = sqlite3.connect('games_bot.db'); cursor = conn.cursor()
    cursor.execute("INSERT INTO games (genre, name, description, photo_id, file_id) VALUES (?, ?, ?, ?, ?)", 
                   (d['genre'], d['name'], d['desc'], d['photo'], m.document.file_id))
    conn.commit(); conn.close()
    await m.answer("✅ O'yin qo'shildi!", reply_markup=get_genres_kb())
    await state.clear()

# ZAKAZ BERISH
@dp.message(F.text == "🎁 O'yin zakas berish", F.chat.type == "private")
async def order_start(message: Message, state: FSMContext):
    await message.answer("📝 O'yin nomini yozing:")
    await state.set_state(OrderGame.waiting_for_order_text)

@dp.message(OrderGame.waiting_for_order_text)
async def order_received(message: Message, state: FSMContext):
    text = f"🎁 **Yangi Buyurtma!**\n\n👤 @{message.from_user.username}\n🆔 ID: {message.from_user.id}\n📩 Fikr: {message.text}"
    await bot.send_message(ADMIN_CHANNEL_ID, text)
    await message.answer("✅ Adminga yuborildi!")
    await state.clear()

async def main():
    init_db()
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())