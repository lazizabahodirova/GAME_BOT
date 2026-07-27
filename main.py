import asyncio
import sqlite3
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardRemove
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
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      genre TEXT, name TEXT, description TEXT, 
                      photo_id TEXT, file_id TEXT)''')
    conn.commit()
    conn.close()

# --- HOLATLAR (FSM) ---
class AddGame(StatesGroup):
    waiting_for_genre = State()
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_photo = State()
    waiting_for_file = State()

class OrderGame(StatesGroup): 
    waiting_for_order_text = State()

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

# --- 1. START VA ASOSIY MENYU ---
@dp.message(Command("start"), F.chat.type == "private")
@dp.message(F.text == "⬅️ Orqaga", F.chat.type == "private")
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("📁 Janrni tanlang yoki buyurtma bering:", reply_markup=get_genres_kb())

# --- 2. ADMIN: O'YIN QO'SHISH BOSQICHLARI ---
@dp.message(Command("add"), F.from_user.id == ADMIN_ID)
async def add_start(m: Message, state: FSMContext):
    await m.answer("Qaysi janrga o'yin qo'shmoqchisiz?", reply_markup=get_genres_kb())
    await state.set_state(AddGame.waiting_for_genre)

@dp.message(AddGame.waiting_for_genre, F.text.in_(GENRES))
async def add_genre(m: Message, state: FSMContext):
    await state.update_data(genre=m.text)
    await m.answer(f"O'yin nomini yozing:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AddGame.waiting_for_name)

@dp.message(AddGame.waiting_for_name)
async def add_name(m: Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("O'yin uchun izoh (description) yozing:")
    await state.set_state(AddGame.waiting_for_description)

@dp.message(AddGame.waiting_for_description)
async def add_desc(m: Message, state: FSMContext):
    await state.update_data(desc=m.text)
    await m.answer("O'yin uchun rasm yuboring:")
    await state.set_state(AddGame.waiting_for_photo)

@dp.message(AddGame.waiting_for_photo, F.photo)
async def add_photo(m: Message, state: FSMContext):
    await state.update_data(photo=m.photo[-1].file_id)
    await m.answer("Endi o'yin faylini (document) yuboring:")
    await state.set_state(AddGame.waiting_for_file)

@dp.message(AddGame.waiting_for_file, F.document)
async def add_file(m: Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect('games_bot.db'); cursor = conn.cursor()
    cursor.execute("INSERT INTO games (genre, name, description, photo_id, file_id) VALUES (?, ?, ?, ?, ?)", 
                   (data['genre'], data['name'], data['desc'], data['photo'], m.document.file_id))
    conn.commit(); conn.close()
    await m.answer("✅ O'yin muvaffaqiyatli qo'shildi!", reply_markup=get_genres_kb())
    await state.clear()

# --- 3. FOYDALANUVCHI: O'YIN TANLASH VA KO'RISH ---
@dp.message(F.text.in_(GENRES), F.chat.type == "private")
async def show_genre_games(message: Message):
    kb = get_games_by_genre_kb(message.text)
    if kb: await message.answer(f"✅ {message.text} o'yinlari:", reply_markup=kb)
    else: await message.answer("⚠️ Bu janrda o'yin yo'q.")

@dp.message(F.text, F.chat.type == "private", StateFilter(None))
async def handle_game_selection(message: Message):
    if message.text == "🎁 O'yin zakas berish": # Zakaz handler
        await message.answer("📝 O'yin nomini yozing:")
        await dp.fsm.get_context(message).set_state(OrderGame.waiting_for_order_text)
        return

    conn = sqlite3.connect('games_bot.db'); cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, photo_id FROM games WHERE name=?", (message.text,))
    game = cursor.fetchone(); conn.close()
    
    if game:
        game_id, name, desc, photo_id = game
        kb = InlineKeyboardBuilder()
        kb.button(text="📥 Faylni yuklab olish", callback_data=f"download_req_{game_id}")
        await message.answer_photo(
            photo=photo_id,
            caption=f"🎮 **{name}**\n\n📝 {desc}",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )

# --- 4. TO'LOV TIZIMI ---
@dp.callback_query(F.data.startswith("download_req_"))
async def select_payment(callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    kb = InlineKeyboardBuilder()
    kb.button(text="💵 Naxt orqali", callback_data=f"pay_cash_{game_id}")
    kb.button(text="💳 Karta orqali", callback_data=f"pay_card_{game_id}")
    kb.adjust(2)
    await callback.message.answer("Faylni yuklab olish uchun to'lov qiling. To'lov turini tanlang:", reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_cash_"))
async def pay_cash(callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    user = callback.from_user
    admin_msg = (f"💵 **Naxt to'lov tanlandi!**\n\n👤 Foydalanuvchi: @{user.username or 'Yashirin'}\n🆔 ID: {user.id}\n🎮 O'yin ID: {game_id}\n\nFikringizni qoldirish uchun ushbu xabarga reply qiling.")
    await bot.send_message(ADMIN_CHANNEL_ID, admin_msg)
    await callback.message.answer("Siz Naxt to'lovni tanladingiz. Admin javobini kuting...")
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_card_"))
async def pay_card(callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ To'lov qilish", callback_data=f"confirm_pay_{game_id}")
    text = f"💳 **Karta orqali to'lov**\n\n📌 Raqam: `{KARTA_RAQAM}`\n👤 Ega: {KARTA_EGASI}\n\nTo'lovni amalga oshirib tugmani bosing."
    await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("confirm_pay_"))
async def confirm_payment_request(callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    user = callback.from_user
    await callback.message.answer("To'lovingiz tasdiqlanmoqda...")
    
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ To'lovni tasdiqlash", callback_data=f"adm_verify_{user.id}_{game_id}")
    
    admin_msg = (f"💳 **Karta orqali to'lov so'rovi!**\n\n👤 Foydalanuvchi: @{user.username}\n🆔 ID: {user.id}\n"
                 f"Kartangizni tekshiring, pul tushgan bo'lsa tasdiqlang.")
    await bot.send_message(ADMIN_CHANNEL_ID, admin_msg, reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("adm_verify_"))
async def admin_verify(callback: CallbackQuery):
    _, _, user_id, game_id = callback.data.split("_")
    conn = sqlite3.connect('games_bot.db'); cursor = conn.cursor()
    cursor.execute("SELECT file_id, name FROM games WHERE id=?", (game_id,))
    game = cursor.fetchone(); conn.close()
    
    if game:
        await bot.send_document(user_id, document=game[0], caption=f"✅ To'lov tasdiqlandi! \n🎮 O'yin: {game[1]}")
        await callback.message.edit_text(callback.message.text + "\n\n✅ TASDIQLANDI!")
    await callback.answer()

# --- 5. ADMIN REPLY (GURUHDA JAVOB YOZISH) ---
@dp.message(F.chat.id == ADMIN_CHANNEL_ID, F.reply_to_message)
async def admin_reply(message: Message):
    orig_text = message.reply_to_message.text or message.reply_to_message.caption
    if orig_text:
        match = re.search(r"🆔 ID: (\d+)", orig_text)
        if match:
            user_id = match.group(1)
            try:
                await bot.send_message(user_id, f"👨‍💻 Admin: {message.text}")
                await message.reply("✅ Yuborildi.")
            except:
                await message.reply("❌ User botni bloklagan.")

# --- 6. ZAKAZ BERISH HANDLERI ---
@dp.message(OrderGame.waiting_for_order_text)
async def order_done(message: Message, state: FSMContext):
    admin_text = f"🎁 **Yangi Zakaz!**\n\n👤 @{message.from_user.username}\n🆔 ID: {message.from_user.id}\n📩 O'yin: {message.text}"
    await bot.send_message(ADMIN_CHANNEL_ID, admin_text)
    await message.answer("✅ Zakazingiz adminga yuborildi!", reply_markup=get_genres_kb())
    await state.clear()

async def main():
    init_db()
    print("Bot ishlamoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())