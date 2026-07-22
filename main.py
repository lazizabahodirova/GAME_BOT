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
ADMIN_CHANNEL_ID = -1004343145305 
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
    waiting_for_genre, waiting_for_name, waiting_for_description, waiting_for_photo, waiting_for_file = State(), State(), State(), State(), State()

class OrderGame(StatesGroup): waiting_for_order_text = State()
class AdminReply(StatesGroup): waiting_for_text = State()

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

def get_user_pay_kb(game_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="💵 Naxt orqali", callback_data=f"upay_cash_{game_id}")
    builder.button(text="💳 Karta orqali", callback_data=f"upay_card_{game_id}")
    builder.adjust(2); return builder.as_markup()

def get_admin_action_kb(user_id, game_id="0"):
    builder = InlineKeyboardBuilder()
    if game_id != "0": builder.button(text="✅ Tasdiqlash", callback_data=f"adm_conf_{user_id}_{game_id}")
    else: builder.button(text="✅ To'lovni Tasdiqlash (Zakaz)", callback_data=f"adm_conf_{user_id}_0")
    builder.button(text="💬 Fikr bildirish", callback_data=f"adm_msg_{user_id}")
    builder.adjust(1); return builder.as_markup()

# --- ADMIN GURUHIDAGI AMALLAR (REPLY VA FAYL YUBORISH) ---

@dp.message(F.chat.id == ADMIN_CHANNEL_ID)
async def admin_group_manager(message: Message, state: FSMContext):
    # 1. Fikr bildirish holati
    cur_state = await state.get_state()
    if cur_state == AdminReply.waiting_for_text:
        data = await state.get_data()
        try:
            await bot.send_message(data['target_id'], f"👨‍💻 Admin: {message.text}")
            await message.reply("✅ Xabar yuborildi.")
        except: await message.reply("❌ Foydalanuvchi botni bloklagan.")
        await state.clear(); return

    # 2. Fayl yuborish yoki Matnli Reply
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        text = message.reply_to_message.text or message.reply_to_message.caption or ""
        match = re.search(r"ID: (\d+)", text)
        if match:
            user_id = match.group(1)
            # Agar fayl tashlansa
            if message.document or message.video or message.audio:
                try:
                    await bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id, caption="🎮 Mana siz so'ragan o'yin! Yuklab oling.")
                    await message.reply(f"✅ Fayl foydalanuvchiga (ID: {user_id}) yuborildi!")
                except: await message.reply("❌ Faylni yuborib bo'lmadi.")
            # Agar shunchaki matn yozilsa
            elif message.text:
                try:
                    await bot.send_message(user_id, f"👨‍💻 Admin: {message.text}")
                    await message.reply("✅ Xabar yuborildi.")
                except: await message.reply("❌ Yuborib bo'lmadi.")

# --- FOYDALANUVCHI HANDLERLARI ---

@dp.message(Command("start"), F.chat.type == "private")
@dp.message(F.text == "⬅️ Orqaga", F.chat.type == "private")
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("📁 Janrni tanlang yoki buyurtma bering:", reply_markup=get_genres_kb())

@dp.message(F.text.in_(GENRES), F.chat.type == "private")
async def show_genre_games(message: Message):
    kb = get_games_by_genre_kb(message.text)
    if kb: await message.answer(f"✅ {message.text} o'yinlari:", reply_markup=kb)
    else: await message.answer("⚠️ O'yin yo'q.")

@dp.message(F.text == "🎁 O'yin zakas berish", F.chat.type == "private")
async def order_start(message: Message, state: FSMContext):
    await message.answer("📝 O'yin nomini yozing:")
    await state.set_state(OrderGame.waiting_for_order_text)

@dp.message(OrderGame.waiting_for_order_text)
async def order_received(message: Message, state: FSMContext):
    text = f"🎁 Yangi Buyurtma!\n\n👤 @{message.from_user.username}\n🆔 ID: {message.from_user.id}\n📩 Fikr: {message.text}"
    await bot.send_message(ADMIN_CHANNEL_ID, text, reply_markup=get_admin_action_kb(message.from_user.id))
    await message.answer("✅ Adminga yuborildi! O'yin tayyor bo'lishini kuting.")
    await state.clear()

@dp.message(F.text, F.chat.type == "private", StateFilter(None))
async def handle_game_selection(message: Message):
    conn = sqlite3.connect('games_bot.db'); cursor = conn.cursor()
    cursor.execute("SELECT id FROM games WHERE name=?", (message.text,))
    game = cursor.fetchone(); conn.close()
    if game:
        await message.answer(f"🎮 {message.text} tanlandi. Yuklab olish uchun 5,000 so'm to'lov qiling 😁", reply_markup=get_user_pay_kb(game[0]))

# --- CALLBACKLAR ---

@dp.callback_query(F.data.startswith("adm_msg_"))
async def adm_msg_call(callback: CallbackQuery, state: FSMContext):
    user_id = callback.data.split("_")[2]
    await state.update_data(target_id=user_id); await state.set_state(AdminReply.waiting_for_text)
    await callback.message.reply(f"💬 ID: {user_id} uchun javob yozing:"); await callback.answer()

@dp.callback_query(F.data.startswith("adm_ready_"))
async def adm_ready_call(callback: CallbackQuery):
    uid = callback.data.split("_")[2]
    await bot.send_message(uid, "🎮 Siz zakaz bergan o'yin tayyor! Uni olish uchun to'lov qiling:", reply_markup=get_user_pay_kb(0))
    await callback.message.edit_text(callback.message.text + "\n\n✅ Javob berildi: O'yin tayyor")

@dp.callback_query(F.data.startswith("adm_conf_"))
async def adm_conf_call(callback: CallbackQuery):
    uid, gid = callback.data.split("_")[2], callback.data.split("_")[3]
    if gid == "0": # Zakaz qilingan o'yin bo'lsa
        await bot.send_message(uid, "✅ To'lovingiz tasdiqlandi! Admin hozir o'yin faylini yuboradi.")
        await callback.message.edit_text(callback.message.text + f"\n\n✅ TO'LOV TASDIQLANDI (ID: {uid})\n⚠️ Endi ushbu xabarga REPLY qilib o'yin faylini yuboring!")
    else: # Bazadagi o'yin bo'lsa
        conn = sqlite3.connect('games_bot.db'); cursor = conn.cursor()
        cursor.execute("SELECT name, description, photo_id, file_id FROM games WHERE id=?", (gid,))
        g = cursor.fetchone(); conn.close()
        if g:
            await bot.send_photo(uid, photo=g[2], caption=f"✅ To'lov tasdiqlandi!\n\n{g[0]}\n{g[1]}")
            await bot.send_document(uid, document=g[3])
            await callback.message.edit_text(callback.message.text + "\n\n✅ TASDIQLANDI VA YUBORILDI")
    await callback.answer()

# TO'LOV (USER)
@dp.callback_query(F.data.startswith("upay_cash_"))
async def u_cash(c: CallbackQuery):
    gid = c.data.split("_")[2]
    await bot.send_message(ADMIN_CHANNEL_ID, f"💵 Naqd To'lov!\n🆔 ID: {c.from_user.id}\n🎮 O'yin ID: {gid}", reply_markup=get_admin_action_kb(c.from_user.id, gid))
    await c.message.answer("👨‍💻 Admin javobini kuting.")

@dp.callback_query(F.data.startswith("upay_card_"))
async def u_card(c: CallbackQuery):
    gid = c.data.split("_")[2]
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ To'lov qildim", callback_data=f"upay_done_{gid}")
    await c.message.answer(f"💳 Karta: `{KARTA_RAQAM}`\n👤 Ega: {KARTA_EGASI}", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("upay_done_"))
async def u_done(c: CallbackQuery):
    gid = c.data.split("_")[2]
    await bot.send_message(ADMIN_CHANNEL_ID, f"💳 Karta to'lov!\n🆔 ID: {c.from_user.id}\n🎮 O'yin ID: {gid}", reply_markup=get_admin_action_kb(c.from_user.id, gid))
    await c.message.answer("⏳ To'lov tekshirilmoqda...")

# --- ADMIN: O'YIN QO'SHISH ---
@dp.message(Command("add"), F.from_user.id == ADMIN_ID)
async def add_start(m: Message, state: FSMContext):
    await m.answer("Qaysi janrga o'yin qo'shmoqchisiz?", reply_markup=get_genres_kb())
    await state.set_state(AddGame.waiting_for_genre)

@dp.message(AddGame.waiting_for_genre, F.text.in_(GENRES))
async def add_g1(m: Message, state: FSMContext):
    await state.update_data(genre=m.text); await m.answer(f"📝 {m.text} uchun o'yin nomini yuboring:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddGame.waiting_for_name)

@dp.message(AddGame.waiting_for_name)
async def add_g2(m: Message, state: FSMContext):
    await state.update_data(name=m.text); await m.answer("📄 Izoh yozing:"); await state.set_state(AddGame.waiting_for_description)

@dp.message(AddGame.waiting_for_description)
async def add_g3(m: Message, state: FSMContext):
    await state.update_data(desc=m.text); await m.answer("📸 Rasm yuboring:"); await state.set_state(AddGame.waiting_for_photo)

@dp.message(AddGame.waiting_for_photo, F.photo)
async def add_g4(m: Message, state: FSMContext):
    await state.update_data(photo=m.photo[-1].file_id); await m.answer("📁 Fayl yuboring:"); await state.set_state(AddGame.waiting_for_file)

@dp.message(AddGame.waiting_for_file, F.document)
async def add_g5(m: Message, state: FSMContext):
    d = await state.get_data(); conn = sqlite3.connect('games_bot.db'); cursor = conn.cursor()
    cursor.execute("INSERT INTO games (genre, name, description, photo_id, file_id) VALUES (?, ?, ?, ?, ?)", (d['genre'], d['name'], d['desc'], d['photo'], m.document.file_id))
    conn.commit(); conn.close()
    await m.answer("✅ Qo'shildi!", reply_markup=get_genres_kb()); await state.clear()

async def main():
    init_db()
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())