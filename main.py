import asyncio
import sqlite3
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- SOZLAMALAR ---
API_TOKEN = '7752496700:AAGeDWZf65Yi5T9XRBy7t9_r1grDtgaZ6DA' 
ADMIN_ID = 8320643359 
ADMIN_CHANNEL_ID = -1004343145305 
KARTA_RAQAM = "6262 5700 8837 1937" 
KARTA_EGASI = "SHERBEK NIZOMIDDINOV"

logging.basicConfig(level=logging.INFO)
GENRES = ["🚗 Car Games", "🔫 Action Games", "🧟 Horror Games", "⚽ Sports Games", "🌍 Open World", "🧩 Offline Games", "🌐 Online Games", "💎 MOD APK"]

# --- BAZA ---
def init_db():
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS games 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, genre TEXT, name TEXT, description TEXT, photo_id TEXT, file_id TEXT)''')
    conn.commit(); conn.close()

# --- FSM HOLATLARI ---
class AddGame(StatesGroup):
    waiting_for_genre = State()
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_photo = State()
    waiting_for_file = State()

class OrderGame(StatesGroup): 
    waiting_for_game_name = State()
    waiting_for_choice = State()
    waiting_for_extra_feedback = State()

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- KLAVIATURALAR ---
def get_genres_kb():
    builder = ReplyKeyboardBuilder()
    for genre in GENRES: builder.add(KeyboardButton(text=genre))
    builder.add(KeyboardButton(text="🎁 O'yin zakas berish"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_yes_no_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="✅ Ha"), KeyboardButton(text="❌ Yo'q")]
    ], resize_keyboard=True)

# --- START ---
@dp.message(Command("start"), F.chat.type == "private")
@dp.message(F.text == "⬅️ Orqaga", F.chat.type == "private")
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("📁 Janrni tanlang yoki buyurtma bering:", reply_markup=get_genres_kb())

# --- ADMIN: O'YIN QO'SHISH ---
@dp.message(Command("add"), F.from_user.id == ADMIN_ID)
async def add_start(m: Message, state: FSMContext):
    await m.answer("Qaysi janrga o'yin qo'shmoqchisiz?", reply_markup=get_genres_kb())
    await state.set_state(AddGame.waiting_for_genre)

@dp.message(AddGame.waiting_for_genre, F.text.in_(GENRES))
async def add_genre(m: Message, state: FSMContext):
    await state.update_data(genre=m.text)
    await m.answer("O'yin nomini yozing:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddGame.waiting_for_name)

@dp.message(AddGame.waiting_for_name)
async def add_name(m: Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("O'yin uchun izoh yozing:")
    await state.set_state(AddGame.waiting_for_description)

@dp.message(AddGame.waiting_for_description)
async def add_desc(m: Message, state: FSMContext):
    await state.update_data(desc=m.text)
    await m.answer("O'yin rasmini yuboring:")
    await state.set_state(AddGame.waiting_for_photo)

@dp.message(AddGame.waiting_for_photo, F.photo)
async def add_photo(m: Message, state: FSMContext):
    await state.update_data(photo=m.photo[-1].file_id)
    await m.answer("O'yin faylini (document) yuboring:")
    await state.set_state(AddGame.waiting_for_file)

@dp.message(AddGame.waiting_for_file, F.document)
async def add_file(m: Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect('games_bot.db'); cursor = conn.cursor()
    cursor.execute("INSERT INTO games (genre, name, description, photo_id, file_id) VALUES (?, ?, ?, ?, ?)", 
                   (data['genre'], data['name'], data['desc'], data['photo'], m.document.file_id))
    conn.commit(); conn.close()
    await m.answer("✅ O'yin qo'shildi!", reply_markup=get_genres_kb())
    await state.clear()

# --- FOYDALANUVCHI: O'YIN TANLASH ---
@dp.message(F.text.in_(GENRES), F.chat.type == "private")
async def show_genre_games(message: Message):
    conn = sqlite3.connect('games_bot.db'); cursor = conn.cursor()
    cursor.execute("SELECT name FROM games WHERE genre=?", (message.text,))
    games = cursor.fetchall(); conn.close()
    if not games:
        await message.answer("⚠️ Bu janrda o'yin yo'q.")
        return
    builder = ReplyKeyboardBuilder()
    for game in games: builder.add(KeyboardButton(text=game[0]))
    builder.add(KeyboardButton(text="⬅️ Orqaga")); builder.adjust(2)
    await message.answer(f"✅ {message.text} o'yinlari:", reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(F.text, F.chat.type == "private", StateFilter(None))
async def handle_selection(message: Message, state: FSMContext):
    if message.text == "🎁 O'yin zakas berish":
        await message.answer("📝 O'yin nomini yozing:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(OrderGame.waiting_for_game_name)
        return

    conn = sqlite3.connect('games_bot.db'); cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, photo_id FROM games WHERE name=?", (message.text,))
    game = cursor.fetchone(); conn.close()
    if game:
        kb = InlineKeyboardBuilder()
        kb.button(text="📥 Faylni yuklab olish", callback_data=f"dl_{game[0]}")
        await message.answer_photo(photo=game[3], caption=f"🎮 **{game[1]}**\n\n📝 {game[2]}", reply_markup=kb.as_markup(), parse_mode="Markdown")

# --- TO'LOV TIZIMI ---
@dp.callback_query(F.data.startswith("dl_"))
async def select_pay(callback: CallbackQuery):
    game_id = callback.data.split("_")[1]
    kb = InlineKeyboardBuilder()
    kb.button(text="💵 Naxt orqali", callback_data=f"pay_cash_{game_id}")
    kb.button(text="💳 Karta orqali", callback_data=f"pay_card_{game_id}")
    kb.adjust(2)
    await callback.message.answer("To'lov turini tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("pay_cash_"))
async def pay_cash(callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    user = callback.from_user
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ To'lovni tasdiqlash", callback_data=f"adm_v_{user.id}_{game_id}")
    admin_msg = f"💵 **Naxt to'lov so'rovi!**\n\n👤 @{user.username}\n🆔 ID: {user.id}\n🎮 O'yin ID: {game_id}\n\nTo'lov tushgan bo'lsa tasdiqlang."
    await bot.send_message(ADMIN_CHANNEL_ID, admin_msg, reply_markup=kb.as_markup())
    await callback.message.answer("Naqd to'lov tanlandi. Admin tasdiqlashini kuting.")

@dp.callback_query(F.data.startswith("pay_card_"))
async def pay_card(callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ To'lov qildim", callback_data=f"p_done_{game_id}")
    await callback.message.answer(f"💳 Karta: `{KARTA_RAQAM}`\n👤 Ega: {KARTA_EGASI}\n\nTo'lovdan so'ng tugmani bosing.", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("p_done_"))
async def card_done(callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    user = callback.from_user
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ To'lovni tasdiqlash", callback_data=f"adm_v_{user.id}_{game_id}")
    admin_msg = f"💳 **Karta orqali to'lov!**\n\n👤 @{user.username}\n🆔 ID: {user.id}\n🎮 O'yin ID: {game_id}\n\nTekshirib tasdiqlang."
    await bot.send_message(ADMIN_CHANNEL_ID, admin_msg, reply_markup=kb.as_markup())
    await callback.message.answer("To'lovingiz tasdiqlanmoqda...")

@dp.callback_query(F.data.startswith("adm_v_"))
async def admin_verify(callback: CallbackQuery):
    _, _, user_id, game_id = callback.data.split("_")
    conn = sqlite3.connect('games_bot.db'); cursor = conn.cursor()
    cursor.execute("SELECT file_id, name FROM games WHERE id=?", (game_id,))
    game = cursor.fetchone(); conn.close()
    if game:
        await bot.send_document(user_id, document=game[0], caption=f"✅ To'lov tasdiqlandi!\n🎮 O'yin: {game[1]}")
        await callback.message.edit_text(callback.message.text + "\n\n✅ TASDIQLANDI!")

# --- O'YIN ZAKAZ QILISH BOSQICHLARI ---
@dp.message(OrderGame.waiting_for_game_name)
async def order_game_name(message: Message, state: FSMContext):
    await state.update_data(game_name=message.text)
    admin_msg = f"🎁 **Yangi Zakaz!**\n\n👤 @{message.from_user.username}\n🆔 ID: {message.from_user.id}\n📩 O'yin nomi: {message.text}"
    await bot.send_message(ADMIN_CHANNEL_ID, admin_text=admin_msg) # Admin xabarini saqlash shart emas
    
    await message.answer("Yana nimadir yozasizmi (fikr, taklif)?", reply_markup=get_yes_no_kb())
    await state.set_state(OrderGame.waiting_for_choice)

@dp.message(OrderGame.waiting_for_choice)
async def order_choice(message: Message, state: FSMContext):
    if message.text == "✅ Ha":
        await message.answer("Fikringizni qoldiring:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(OrderGame.waiting_for_extra_feedback)
    else:
        await message.answer("Buyurtmangiz qabul qilindi!", reply_markup=get_genres_kb())
        await state.clear()

@dp.message(OrderGame.waiting_for_extra_feedback)
async def order_feedback(message: Message, state: FSMContext):
    data = await state.get_data()
    admin_msg = f"💬 **Zakazga qo'shimcha fikr!**\n\n👤 @{message.from_user.username}\n🆔 ID: {message.from_user.id}\n🎮 O'yin: {data['game_name']}\n💭 Fikr: {message.text}"
    await bot.send_message(ADMIN_CHANNEL_ID, admin_msg)
    await message.answer("Fikringiz adminga yetkazildi. Rahmat!", reply_markup=get_genres_kb())
    await state.clear()

# --- ADMIN REPLY HANDLER ---
@dp.message(F.chat.id == ADMIN_CHANNEL_ID, F.reply_to_message)
async def admin_reply(message: Message):
    orig = message.reply_to_message.text or message.reply_to_message.caption
    if orig:
        match = re.search(r"🆔 ID: (\d+)", orig)
        if match:
            user_id = match.group(1)
            try:
                await bot.send_message(user_id, f"👨‍💻 Admin javobi: {message.text}")
                await message.reply("✅ Foydalanuvchiga yuborildi.")
            except:
                await message.reply("❌ Yuborishda xatolik (user bloklagan bo'lishi mumkin).")

async def main():
    init_db()
    print("Bot ishlamoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())