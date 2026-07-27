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
# Tokenni xavfsizlik uchun o'zgarmas saqlang
API_TOKEN = '7752496700:AAGeDWZf65Yi5T9XRBy7t9_r1grDtgaZ6DA'
ADMIN_ID = 8320643359
# DIQQAT: Guruh yoki kanal ID si manfiy son bo'lishi kerak (masalan: -100...)
ADMIN_CHANNEL_ID = -1004343145305 
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

    if not games:
        return None

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
    await message.answer(
        "📁 Janrni tanlang yoki buyurtma bering:",
        reply_markup=get_genres_kb()
    )

@dp.message(Command("add"), F.from_user.id == ADMIN_ID)
async def add_start(message: Message, state: FSMContext):
    await message.answer("Qaysi janrga o'yin qo'shmoqchisiz?", reply_markup=get_genres_kb())
    await state.set_state(AddGame.waiting_for_genre)

@dp.message(F.text == "🎁 O'yin zakas berish", F.chat.type == "private")
async def order_start(message: Message, state: FSMContext):
    await message.answer("📝 Buyurtma qilmoqchi bo'lgan o'yiningiz nomini va platformasini yozing:")
    await state.set_state(OrderGame.waiting_for_order_text)

@dp.message(F.text.in_(GENRES), F.chat.type == "private")
async def show_genre_games(message: Message):
    kb = get_games_by_genre_kb(message.text)
    if kb:
        await message.answer(f"✅ {message.text} o'yinlari:", reply_markup=kb)
    else:
        await message.answer("⚠️ Ushbu janrda hali o'yinlar yo'q.")

@dp.message(F.text, F.chat.type == "private", StateFilter(None))
async def handle_game_selection(message: Message):
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, photo_id FROM games WHERE name=?", (message.text,))
    game = cursor.fetchone()
    conn.close()

    if game:
        game_id, name, desc, photo_id = game
        kb = InlineKeyboardBuilder()
        kb.button(text="📥 Faylni olish", callback_data=f"get_file_{game_id}")
        await message.answer_photo(
            photo=photo_id,
            caption=f"🎮 **{name}**\n\n📝 {desc}",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )

# ================= FSM: ZAKAS QISMI =================

@dp.message(OrderGame.waiting_for_order_text)
async def order_received(message: Message, state: FSMContext):
    text = (
        f"🎁 **Yangi Buyurtma!**\n\n"
        f"👤 Kimdan: {message.from_user.full_name}\n"
        f"🆔 ID: `{message.from_user.id}`\n"
        f"📩 Xabar: {message.text}"
    )
    try:
        await bot.send_message(ADMIN_CHANNEL_ID, text, parse_mode="Markdown")
        await message.answer("✅ Buyurtmangiz adminga yuborildi!", reply_markup=get_genres_kb())
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await message.answer("❌ Adminga yuborishda xatolik yuz berdi.")
    await state.clear()

# ================= TO'LOV TIZIMI =================

@dp.callback_query(F.data.startswith("get_file_"))
async def show_payment_methods(callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    kb = InlineKeyboardBuilder()
    kb.button(text="💵 Naxt orqali", callback_data=f"pay_cash_{game_id}")
    kb.button(text="💳 Karta orqali", callback_data=f"pay_card_{game_id}")
    kb.adjust(2)
    await callback.message.answer("To'lov turini tanlang:", reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_cash_"))
async def process_pay_cash(callback: CallbackQuery, state: FSMContext):
    game_id = callback.data.split("_")[2]
    await state.update_data(target_game_id=game_id)
    await callback.message.answer("✍️ Naxt to'lov haqida (manzil yoki vaqtni) yozing yoki shunchaki fikringizni qoldiring:")
    await state.set_state(Feedback.waiting_for_feedback)
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_card_"))
async def process_pay_card(callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ To'lov qildim", callback_data=f"card_paid_{game_id}")
    kb.button(text="💬 Fikr/Muammo", callback_data=f"feedback_{game_id}")
    kb.adjust(1)
    
    text = (
        f"💳 **Karta orqali to'lov**\n\n"
        f"Raqam: `{KARTA_RAQAM}`\n"
        f"Ega: **{KARTA_EGASI}**\n\n"
        f"To'lovdan so'ng 'To'lov qildim' tugmasini bosing."
    )
    await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("card_paid_"))
async def process_card_paid(callback: CallbackQuery):
    game_id = callback.data.split("_")[2]
    user = callback.from_user
    
    admin_text = (
        f"💳 **Karta orqali to'lov so'rovi!**\n\n"
        f"👤 Foydalanuvchi: {user.full_name}\n"
        f"🆔 ID: `{user.id}`\n"
        f"🎮 O'yin ID: {game_id}"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data=f"admin_confirm_{user.id}_{game_id}")
    
    try:
        await bot.send_message(ADMIN_CHANNEL_ID, admin_text, reply_markup=kb.as_markup(), parse_mode="Markdown")
        await callback.message.answer("✅ To'lovingiz tekshirilmoqda. Admin tasdiqlagach fayl yuboriladi.")
    except Exception as e:
        await callback.message.answer("❌ Guruhga xabar ketmadi. Botni guruhga admin qiling.")
    await callback.answer()

@dp.callback_query(F.data.startswith("feedback_"))
async def start_feedback(callback: CallbackQuery, state: FSMContext):
    game_id = callback.data.split("_")[1]
    await state.update_data(target_game_id=game_id)
    await callback.message.answer("✍️ Xabaringizni yozib qoldiring:")
    await state.set_state(Feedback.waiting_for_feedback)
    await callback.answer()

@dp.message(Feedback.waiting_for_feedback)
async def process_feedback(message: Message, state: FSMContext):
    data = await state.get_data()
    game_id = data.get("target_game_id", "Noma'lum")
    
    text = (
        f"💬 **Yangi Xabar/Fikr**\n\n"
        f"👤 Kimdan: {message.from_user.full_name}\n"
        f"🆔 ID: `{message.from_user.id}`\n"
        f"🎮 O'yin ID: {game_id}\n"
        f"📩 Xabar: {message.text}"
    )
    
    try:
        await bot.send_message(ADMIN_CHANNEL_ID, text, parse_mode="Markdown")
        await message.answer("✅ Xabaringiz adminga yetkazildi!")
    except Exception:
        await message.answer("❌ Xabar yuborishda xatolik.")
    
    await state.clear()

# ================= ADMIN TASDIQLASH =================

@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(callback: CallbackQuery):
    # admin_confirm_{user_id}_{game_id}
    parts = callback.data.split("_")
    u_id = int(parts[2])
    g_id = int(parts[3])

    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, name FROM games WHERE id=?", (g_id,))
    game = cursor.fetchone()
    conn.close()

    if game:
        try:
            await bot.send_document(u_id, game[0], caption=f"✅ To'lov tasdiqlandi! \n🎮 O'yin: {game[1]}")
            await callback.message.edit_text(callback.message.text + "\n\n✅ **YUBORILDI**")
        except Exception as e:
            await callback.answer(f"Foydalanuvchiga yuborib bo'lmadi: {e}", show_alert=True)
    else:
        await callback.answer("O'yin bazadan topilmadi.")

# ================= O'YIN QO'SHISH (ADMIN) =================

@dp.message(AddGame.waiting_for_genre)
async def add_g1(message: Message, state: FSMContext):
    if message.text in GENRES:
        await state.update_data(genre=message.text)
        await message.answer("O'yin nomini yuboring:", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(AddGame.waiting_for_name)

@dp.message(AddGame.waiting_for_name)
async def add_g2(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("O'yin haqida tavsif:")
    await state.set_state(AddGame.waiting_for_description)

@dp.message(AddGame.waiting_for_description)
async def add_g3(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer("O'yin uchun rasm yuboring:")
    await state.set_state(AddGame.waiting_for_photo)

@dp.message(AddGame.waiting_for_photo, F.photo)
async def add_g4(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("O'yin faylini (document) yuboring:")
    await state.set_state(AddGame.waiting_for_file)

@dp.message(AddGame.waiting_for_file, F.document)
async def add_g5(message: Message, state: FSMContext):
    d = await state.get_data()
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO games (genre, name, description, photo_id, file_id) VALUES (?,?,?,?,?)",
                   (d['genre'], d['name'], d['desc'], d['photo'], message.document.file_id))
    conn.commit()
    conn.close()
    await message.answer("✅ O'yin qo'shildi!", reply_markup=get_genres_kb())
    await state.clear()

# ================= MAIN =================
async def main():
    init_db()
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())