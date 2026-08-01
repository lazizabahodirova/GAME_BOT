import json
import asyncio
import sqlite3
import logging
import re
from html import escape
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message, CallbackQuery, KeyboardButton, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- SOZLAMALAR ---
API_TOKEN = '7752496700:AAGeDWZf65Yi5T9XRBy7t9_r1grDtgaZ6DA'
ADMIN_ID = 8320643359
ADMIN_CHANNEL_ID = -1004343145305
KARTA_RAQAM = "6262 5700 8837 1937"
KARTA_EGASI = "SHERBEK NIZOMIDDINOV"

logging.basicConfig(level=logging.INFO)

GENRES = [
    "🚗 Car Games", "🔫 Action Games", "🧟 Horror Games", "⚽ Sports Games",
    "🌍 Open World", "📱 Apps", "🌐 Online Games", "🕹PPSSPP Games"
]

PC_GAME_GENRES = [
    "🏎 Car Games", "⚽ Sport Games", "🥊 Fight Games", "🧟 Zombie Games",
    "👻 Horror Games", "🕹 Arcade", "🌎 Open World",
    "💥 Action Games", "🧠 Strategy", "✈️ Simulator"
]

# --- BAZA ---
def init_db():
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS items
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      platform TEXT,          -- android / pc
                      category TEXT,          -- janr yoki apps/games
                      name TEXT,
                      description TEXT,
                      photo_id TEXT,
                      file_id TEXT,
                      link TEXT)''')
    conn.commit()
    conn.close()

# --- STATES ---
class AddItem(StatesGroup):
    waiting_for_genre = State()          # Android uchun
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_photo = State()
    waiting_for_file_or_link = State()

class DeleteItem(StatesGroup):
    waiting_for_category = State()
    waiting_for_item = State()

class OrderItem(StatesGroup):
    waiting_for_name = State()
    waiting_for_more = State()           # Yana fikr bormi?
    waiting_for_feedback = State()

class Payment(StatesGroup):
    waiting_for_check = State()          # Karta cheki

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ========== KLAVIATURALAR ==========
def main_menu_kb():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📱 Android"), KeyboardButton(text="💻 PC"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def android_menu_kb():
    builder = ReplyKeyboardBuilder()
    for g in GENRES:
        builder.add(KeyboardButton(text=g))
    builder.add(KeyboardButton(text="🎁 Ilova/O'yin buyurtirish"))
    builder.add(KeyboardButton(text="⬅️ Orqaga"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def pc_menu_kb():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📲 Ilovalar"), KeyboardButton(text="🎮 O'yinlar"))
    builder.add(KeyboardButton(text="⬅️ Orqaga"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def pc_apps_kb():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🎁 Ilova/O'yin buyurtirish"))
    builder.add(KeyboardButton(text="⬅️ Orqaga"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def pc_games_kb():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🎁 Ilova/O'yin buyurtirish"))
    builder.add(KeyboardButton(text="⬅️ Orqaga"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)
def pc_genres_kb():
    builder = ReplyKeyboardBuilder()
    for g in PC_GAME_GENRES:
        builder.add(KeyboardButton(text=g))
    builder.add(KeyboardButton(text="🎁 Ilova/O'yin buyurtirish"))
    builder.add(KeyboardButton(text="⬅️ Orqaga"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_items_kb(platform: str, category: str):
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM items WHERE platform=? AND category=?", (platform, category))
    items = cursor.fetchall()
    conn.close()
    builder = ReplyKeyboardBuilder()
    for item in items:
        builder.add(KeyboardButton(text=item[0]))
    builder.add(KeyboardButton(text="⬅️ Orqaga"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def yes_no_kb():
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Ha"), KeyboardButton(text="Yo'q"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# ========== START & NAVIGATSIYA ==========
@dp.message(Command("start"), F.chat.type == "private")
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("📱 Android yoki 💻 PC bo'limini tanlang:", reply_markup=main_menu_kb())

@dp.message(F.text == "⬅️ Orqaga", F.chat.type == "private")
async def back_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    platform = data.get("platform")
    category = data.get("category")
    
    if platform == "android":
        await message.answer("📱 Android bo'limi:", reply_markup=android_menu_kb())
    elif platform == "pc":
        if category in ["apps", "games"]:
            await message.answer("💻 PC bo'limi:", reply_markup=pc_menu_kb())
        else:
            await message.answer("📱 Android yoki 💻 PC:", reply_markup=main_menu_kb())
    else:
        await message.answer("📱 Android yoki 💻 PC:", reply_markup=main_menu_kb())
    await state.clear()

@dp.message(F.text == "📱 Android", F.chat.type == "private")
async def android_section(message: Message, state: FSMContext):
    await state.update_data(platform="android")
    await message.answer("📱 Android o'yinlari janrini tanlang:", reply_markup=android_menu_kb())

@dp.message(F.text == "💻 PC", F.chat.type == "private")
async def pc_section(message: Message, state: FSMContext):
    await state.update_data(platform="pc")
    await message.answer("💻 PC bo'limini tanlang:", reply_markup=pc_menu_kb())

@dp.message(F.text == "📲 Ilovalar", F.chat.type == "private")
async def pc_apps(message: Message, state: FSMContext):
    await state.update_data(platform="pc", category="apps")
    kb = get_items_kb("pc", "apps")
    await message.answer("📲 PC Ilovalari:", reply_markup=kb)

@dp.message(F.text == "🎮 O'yinlar", F.chat.type == "private")
async def pc_games(message: Message, state: FSMContext):
    await state.update_data(platform="pc", category="games")  # vaqtinchalik
    await message.answer(
        "🎮 PC O'yinlari — janrni tanlang:",
        reply_markup=pc_genres_kb()
    )

# ========== /ADD (ADMIN) ==========
@dp.message(Command("add"), F.from_user.id == ADMIN_ID)
async def add_start(message: Message, state: FSMContext):
    data = await state.get_data()
    platform = data.get("platform")
    category = data.get("category")

    if platform == "android":
        await message.answer("Qaysi janrga o'yin qo'shmoqchisiz?", reply_markup=android_menu_kb())
        await state.set_state(AddItem.waiting_for_genre)

    elif platform == "pc" and category == "apps":
        await message.answer("Qo'shmoqchi bo'lgan ilovangizni nomini yozing!")
        await state.set_state(AddItem.waiting_for_name)
        await state.update_data(add_type="app")

    elif platform == "pc" and (category == "games" or category in PC_GAME_GENRES):
        # Agar hali janr tanlanmagan bo'lsa — janr so'raymiz
        if category == "games" or category not in PC_GAME_GENRES:
            await message.answer(
                "Qaysi janrga PC o'yinini qo'shmoqchisiz?",
                reply_markup=pc_genres_kb()
            )
            await state.set_state(AddItem.waiting_for_genre)
        else:
            # Allaqachon janr tanlangan
            await message.answer("O'yin nomini yozib yuboring!", reply_markup=ReplyKeyboardRemove())
            await state.set_state(AddItem.waiting_for_name)

    else:
        await message.answer("Avval Android yoki PC → O'yinlar bo'limiga kiring, keyin /add yozing.")

@dp.message(AddItem.waiting_for_genre)
async def add_genre(message: Message, state: FSMContext):
    text = message.text

    if text in GENRES:
        await state.update_data(category=text, platform="android")
        await message.answer("O'yin nomini yozib yuboring!", reply_markup=ReplyKeyboardRemove())
        await state.set_state(AddItem.waiting_for_name)

    elif text in PC_GAME_GENRES:
        await state.update_data(category=text, platform="pc")
        await message.answer("O'yin nomini yozib yuboring!", reply_markup=ReplyKeyboardRemove())
        await state.set_state(AddItem.waiting_for_name)

    else:
        await message.answer("Menyudagi janrlardan birini tanlang!")

@dp.message(AddItem.waiting_for_name)
async def add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Izoh yozing:")
    await state.set_state(AddItem.waiting_for_description)

@dp.message(AddItem.waiting_for_description)
async def add_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer("Rasm yuboring:")
    await state.set_state(AddItem.waiting_for_photo)

@dp.message(AddItem.waiting_for_photo, F.photo)
async def add_photo(message: Message, state: FSMContext):
    await state.update_data(photo=message.photo[-1].file_id, files=[])  # bo'sh ro'yxat
    data = await state.get_data()
    
    if data.get("platform") == "pc" and data.get("category") == "games":
        await message.answer(
            "O'yin linkini yuboring yoki fayllarni yuboring.\n"
            "Bir nechta fayl yuborishingiz mumkin.\n"
            "Tayyor bo'lgach <b>✅ Tayyor</b> deb yozing.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "Fayllarni yuboring (APK, OBB va boshqalar).\n"
            "Nechta bo'lsa ham yuborishingiz mumkin.\n"
            "Barcha fayllarni yuborib bo'lgach <b>✅ Tayyor</b> deb yozing.",
            parse_mode="HTML"
        )
    await state.set_state(AddItem.waiting_for_file_or_link)

@dp.message(AddItem.waiting_for_file_or_link, F.document)
async def add_file_collect(message: Message, state: FSMContext):
    data = await state.get_data()
    files = data.get("files", [])
    files.append(message.document.file_id)
    await state.update_data(files=files)
    
    await message.answer(
        f"✅ Fayl qabul qilindi! (jami: {len(files)} ta)\n"
        f"Yana yuborishingiz mumkin yoki <b>✅ Tayyor</b> deb yozing.",
        parse_mode="HTML"
    )


@dp.message(AddItem.waiting_for_file_or_link, F.text)
async def add_file_finish(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    
    # Agar "tayyor" deb yozmasa va link bo'lsa (PC o'yinlari uchun)
    data = await state.get_data()
    files = data.get("files", [])
    
    if text in ["✅ tayyor", "tayyor", "✅"]:
        if not files and data.get("platform") == "android":
            await message.answer("Kamida bitta fayl yuboring!")
            return
        
        # Saqlash
        file_ids_json = json.dumps(files) if files else None
        link = None
        
        conn = sqlite3.connect('games_bot.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO items (platform, category, name, description, photo_id, file_id, link) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data['platform'], data['category'], data['name'], data['desc'], data['photo'], file_ids_json, link)
        )
        conn.commit()
        conn.close()
        
        await message.answer(
            f"✅ <b>{escape(data['name'])}</b> muvaffaqiyatli qo'shildi!\n"
            f"📦 Fayllar soni: {len(files)} ta",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    # Agar matn kelgan bo'lsa — bu link deb hisoblaymiz (PC o'yinlari uchun)
    if data.get("platform") == "pc" and data.get("category") == "games":
        link = message.text
        file_ids_json = json.dumps(files) if files else None
        
        conn = sqlite3.connect('games_bot.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO items (platform, category, name, description, photo_id, file_id, link) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data['platform'], data['category'], data['name'], data['desc'], data['photo'], file_ids_json, link)
        )
        conn.commit()
        conn.close()
        
        await message.answer(
            f"✅ <b>{escape(data['name'])}</b> muvaffaqiyatli qo'shildi!",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
        await state.clear()
    else:
        await message.answer("Fayl yuboring yoki <b>✅ Tayyor</b> deb yozing.", parse_mode="HTML")

# ========== /del (ADMIN) — o'chirish ==========
@dp.message(Command("del"), F.from_user.id == ADMIN_ID)
async def del_start(message: Message, state: FSMContext):
    builder = ReplyKeyboardBuilder()
    for g in GENRES:
        builder.add(KeyboardButton(text=g))
    builder.add(KeyboardButton(text="📲 PC Ilovalar"), KeyboardButton(text="🎮 PC O'yinlar"))
    builder.add(KeyboardButton(text="⬅️ Orqaga"))
    builder.adjust(2)
    await message.answer(
        "Qaysi bo'limdan o'yin/ilovani o'chirmoqchisiz?\nJanr yoki bo'limni tanlang:",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(DeleteItem.waiting_for_category)


@dp.message(DeleteItem.waiting_for_category, F.chat.type == "private")
async def del_choose_category(message: Message, state: FSMContext):
    text = message.text

    if text == "⬅️ Orqaga":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())
        return

    if text in GENRES:
        platform = "android"
        category = text
    elif text == "📲 PC Ilovalar":
        platform = "pc"
        category = "apps"
    elif text == "🎮 PC O'yinlar":
        platform = "pc"
        category = "games"
    else:
        await message.answer("Iltimos, menyudagi bo'limlardan birini tanlang!")
        return

    await state.update_data(platform=platform, category=category)

    kb = get_items_kb(platform, category)
    # Agar hech narsa bo'lmasa
    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM items WHERE platform=? AND category=?", (platform, category))
    count = cursor.fetchone()[0]
    conn.close()

    if count == 0:
        await message.answer("Bu bo'limda hozircha hech narsa yo'q.", reply_markup=main_menu_kb())
        await state.clear()
        return

    await message.answer(
        f"O'chirmoqchi bo'lgan o'yin/ilovani tanlang:\n({count} ta mavjud)",
        reply_markup=kb
    )
    await state.set_state(DeleteItem.waiting_for_item)


@dp.message(DeleteItem.waiting_for_item, F.chat.type == "private")
async def del_item(message: Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())
        return

    data = await state.get_data()
    platform = data.get("platform")
    category = data.get("category")
    name = message.text

    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM items WHERE name=? AND platform=? AND category=?",
        (name, platform, category)
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted > 0:
        await message.answer(
            f"✅ <b>{escape(name)}</b> muvaffaqiyatli o'chirildi!",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Bunday o'yin/ilova topilmadi. Qaytadan urinib ko'ring.",
            reply_markup=main_menu_kb()
        )

    await state.clear()

# ========== O'YIN / ILOVA KO'RSATISH ==========
# ========== BUYURTMA (ZAKAS) ==========
@dp.message(F.text.contains("Ilova/O'yin buyurtirish"), F.chat.type == "private")
async def order_start(message: Message, state: FSMContext):
    print("✅ order_start ISHLADI!")
    await message.answer("Buyurtma qilmoqchi bo'lgan o'yin yoki ilova nomini to'liq yozib qoldiring!")
    await state.set_state(OrderItem.waiting_for_name)

@dp.message(OrderItem.waiting_for_name, F.chat.type == "private")
async def order_name(message: Message, state: FSMContext):
    print("✅ order_name ISHLADI")
    username = message.from_user.username or "Username yo'q"
    user_id = message.from_user.id
    order_text = message.text

    await state.update_data(order_text=order_text, user_id=user_id)

    msg = (
        f"🎁 <b>Yangi buyurtma!</b>\n\n"
        f"👤 @{escape(username)}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📩 Buyurtma: {escape(order_text)}"
    )
    await bot.send_message(ADMIN_CHANNEL_ID, msg, parse_mode="HTML")

    await message.answer(
        "Yana biron bir fikringiz bormi?\nAgar bo'lmasa pastdagi tugmani bosing!",
        reply_markup=InlineKeyboardBuilder().button(
            text="✅ Buyurtma qilish", callback_data="confirm_order"
        ).as_markup()
    )
    await state.set_state(OrderItem.waiting_for_more)

@dp.callback_query(F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    print("✅ confirm_order ISHLADI")
    data = await state.get_data()
    username = callback.from_user.username or "Username yo'q"
    user_id = callback.from_user.id

    msg = (
        f"📦 <b>Foydalanuvchi buyurtmani so'ramoqda!</b>\n\n"
        f"👤 @{escape(username)}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📩 Buyurtma: {escape(data.get('order_text', ''))}"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 To'lov qilishini so'rash", callback_data=f"ask_payment_{user_id}")
    await bot.send_message(ADMIN_CHANNEL_ID, msg, reply_markup=kb.as_markup(), parse_mode="HTML")

    await callback.message.answer(
        "Iltimos o'yin/ilova faylini olishdan avval pastdagi tugmalar orqali to'lov qiling!",
        reply_markup=InlineKeyboardBuilder()
        .button(text="💵 Naxt orqali", callback_data=f"pay_cash_order_{user_id}")
        .button(text="💳 Karta orqali", callback_data=f"pay_card_order_{user_id}")
        .adjust(1).as_markup()
    )
    await callback.answer()

# ========== O'YIN / ILOVA KO'RSATISH ==========
@dp.message(F.text.in_(GENRES), F.chat.type == "private")
async def show_android_games(message: Message, state: FSMContext):
    print(f"✅ show_android_games → {message.text}")
    await state.update_data(platform="android", category=message.text)
    kb = get_items_kb("android", message.text)
    await message.answer(f"✅ {message.text} janridagi o'yinlar:", reply_markup=kb)

@dp.message(F.text.in_(PC_GAME_GENRES), F.chat.type == "private")
async def show_pc_games_by_genre(message: Message, state: FSMContext):
    await state.update_data(platform="pc", category=message.text)
    kb = get_items_kb("pc", message.text)
    await message.answer(f"✅ {message.text} janridagi PC o'yinlari:", reply_markup=kb)

# MUHIM: buyurtma tugmasini ushlamaslik uchun ~F.text.contains qo'shildi
@dp.message(
    F.text,
    F.chat.type == "private",
    StateFilter(None),
    ~F.text.contains("Ilova/O'yin buyurtirish")   # ← mana shu qator muhim
)
async def show_item_detail(message: Message, state: FSMContext):
    print("⚠️ show_item_detail ISHLADI")
    
    data = await state.get_data()
    platform = data.get("platform")
    category = data.get("category")
    
    if not platform or not category:
        return

    conn = sqlite3.connect('games_bot.db')
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, description, photo_id, file_id, link FROM items WHERE name=? AND platform=? AND category=?",
        (message.text, platform, category)
    )
    item = cursor.fetchone()
    conn.close()

    if not item:
        return

    item_id, name, desc, photo, file_id, link = item
    short_desc = desc[:900] + "..." if len(desc) > 900 else desc

    kb = InlineKeyboardBuilder()
    if platform == "android" or (platform == "pc" and category == "apps"):
        kb.button(text="📥 Yuklab olish", callback_data=f"download_{item_id}")
    else:
        kb.button(text="🔗 O'yin linkini olish", callback_data=f"download_{item_id}")

    await message.answer_photo(
        photo=photo,
        caption=f"🎮 <b>{escape(name)}</b>\n\n📝 {escape(short_desc)}",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
# ========== YUKLAB OLISH TUGMASI ==========
@dp.callback_query(F.data.startswith("download_"))
async def download_item(callback: CallbackQuery):
    item_id = callback.data.split("_")[1]
    
    kb = InlineKeyboardBuilder()
    kb.button(text="💵 Naxt orqali", callback_data=f"pay_cash_{item_id}")
    kb.button(text="💳 Karta orqali", callback_data=f"pay_card_{item_id}")
    kb.adjust(1)
    
    await callback.message.answer(
        "To'lov usulini tanlang:",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


# ========== NAXT ORQALI ==========
@dp.callback_query(F.data.startswith("pay_cash_"))
async def pay_cash(callback: CallbackQuery):
    parts = callback.data.split("_")
    item_id = parts[-1]          # oxirgi qism — item_id yoki user_id
    user = callback.from_user
    username = user.username or "Username yo'q"

    # Buyurtma (order) holatini ajratamiz
    is_order = "order" in callback.data

    if is_order:
        # Buyurtma uchun (fayl admin tomonidan yuboriladi)
        msg = (
            f"💵 <b>Naxt to'lov so'rovi (Buyurtma)!</b>\n\n"
            f"👤 @{escape(username)}\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"📦 Buyurtma ID: {item_id}"
        )
        kb = InlineKeyboardBuilder()
        kb.button(
            text="✅ Tasdiqlash",
            callback_data=f"admin_confirm_cash_{user.id}_{item_id}"
        )
        await bot.send_message(ADMIN_CHANNEL_ID, msg, reply_markup=kb.as_markup(), parse_mode="HTML")
        await callback.message.answer("✅ Adminga so'rov yuborildi. Tasdiqlangandan so'ng fayl yuboriladi.")
    else:
        # Oddiy o'yin/ilova
        conn = sqlite3.connect('games_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM items WHERE id=?", (item_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            await callback.answer("O'yin topilmadi!", show_alert=True)
            return

        name = row[0]
        msg = (
            f"💵 <b>Naxt to'lov so'rovi!</b>\n\n"
            f"👤 @{escape(username)}\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"🎮 O'yin/Ilova: <b>{escape(name)}</b>\n"
            f"🆔 Item ID: <code>{item_id}</code>"
        )
        kb = InlineKeyboardBuilder()
        kb.button(
            text="✅ Tasdiqlash",
            callback_data=f"admin_confirm_cash_{user.id}_{item_id}"
        )
        await bot.send_message(ADMIN_CHANNEL_ID, msg, reply_markup=kb.as_markup(), parse_mode="HTML")
        await callback.message.answer("✅ Adminga so'rov yuborildi. Tasdiqlangandan so'ng o'yin yuboriladi.")

    await callback.answer()
# KARTA
@dp.callback_query(F.data.startswith("pay_card_"))
async def pay_card(callback: CallbackQuery):
    parts = callback.data.split("_")
    target_id = parts[-1]

    text = (
        "Siz Payme, Alif, Click va boshqa ilovalardan to'lov qilishingiz mumkin!\n\n"
        f"💳 <b>Karta raqami:</b> <code>{KARTA_RAQAM}</code>\n"
        f"👤 <b>Ega:</b> {KARTA_EGASI}"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="1️⃣ To'lov qilish", callback_data=f"show_card_{target_id}")
    kb.button(text="2️⃣ To'lov qildim", callback_data=f"paid_{target_id}")
    kb.button(text="3️⃣ Fikr yozish", callback_data=f"feedback_{target_id}")
    kb.adjust(1)
    await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("show_card_"))
async def show_card(callback: CallbackQuery):
    await callback.message.answer(
        f"💳 <b>Karta:</b> <code>{KARTA_RAQAM}</code>\n"
        f"👤 <b>Ega:</b> {KARTA_EGASI}\n\n"
        "Eslatib o'tamiz: agar qurilmangizda to'lov qilish uchun ilova bo'lmasa, boshqa kishidan to'lov qildirib olishingiz mumkin. "
        "To'lov qilgan insondan chekni rasmga tushirib oling!",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("paid_"))
async def paid_check(callback: CallbackQuery, state: FSMContext):
    target_id = callback.data.split("_")[1]
    await state.update_data(pay_target=target_id)
    await callback.message.answer("Iltimos to'lov qilingan chek rasmini yuboring!")
    await state.set_state(Payment.waiting_for_check)
    await callback.answer()

@dp.message(Payment.waiting_for_check, F.photo)
async def receive_check(message: Message, state: FSMContext):
    data = await state.get_data()
    target_id = data.get("pay_target")
    username = message.from_user.username or "Username yo'q"
    user_id = message.from_user.id

    caption = (
        f"Hurmatli guruh egasi!\n\n"
        f"👤 @{escape(username)}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"📦 Target: {target_id}\n\n"
        f"Shu kishi yuborgan rasmni tekshirib ko'ring. Agar to'g'ri bo'lsa <b>Tasdiqlash</b> tugmasini bosing!"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash", callback_data=f"admin_confirm_card_{user_id}_{target_id}")
    
    await bot.send_photo(ADMIN_CHANNEL_ID, photo=message.photo[-1].file_id, caption=caption, reply_markup=kb.as_markup(), parse_mode="HTML")
    await message.answer("✅ Chek adminga yuborildi. Tekshirilgach javob beriladi.")
    await state.clear()

@dp.callback_query(F.data.startswith("feedback_"))
async def feedback_start(callback: CallbackQuery, state: FSMContext):
    await state.update_data(feedback_target=callback.data.split("_")[1])
    await callback.message.answer("Fikringizni yozib qoldiring:")
    await state.set_state(OrderItem.waiting_for_feedback)
    await callback.answer()

@dp.message(OrderItem.waiting_for_feedback)
async def feedback_done(message: Message, state: FSMContext):
    data = await state.get_data()
    username = message.from_user.username or "Username yo'q"
    msg = (
        f"💬 <b>Fikr:</b>\n\n"
        f"👤 @{escape(username)}\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"📩 {escape(message.text)}"
    )
    await bot.send_message(ADMIN_CHANNEL_ID, msg, parse_mode="HTML")
    await message.answer("Kechirasiz, yana biron bir fikringiz bo'lsa Fikr yozish tugmasini bosib yozib qoldirishingiz mumkin.")
    await state.clear()

# ========== ADMIN TASDIQLASH ==========
@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm(callback: CallbackQuery):
    parts = callback.data.split("_")
    # admin_confirm_cash_USERID_ITEMID  yoki  admin_confirm_card_USERID_ITEMID
    if len(parts) < 5:
        await callback.answer("Noto'g'ri ma'lumot!", show_alert=True)
        return

    confirm_type = parts[2]          # cash yoki card
    user_id = int(parts[3])
    target_id = parts[4]

    # --- Oddiy o'yin/ilova (item_id kichik son) ---
    if target_id.isdigit() and int(target_id) < 1000000:
        conn = sqlite3.connect('games_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, name, link FROM items WHERE id=?", (target_id,))
        item = cursor.fetchone()
        conn.close()

        if not item:
            await callback.answer("O'yin topilmadi!", show_alert=True)
            return

        file_data, name, link = item

        # file_id JSON ro'yxat yoki oddiy string bo'lishi mumkin
        file_ids = []
        if file_data:
            try:
                parsed = json.loads(file_data)
                if isinstance(parsed, list):
                    file_ids = parsed
                else:
                    file_ids = [str(parsed)]
            except (json.JSONDecodeError, TypeError):
                # Eski format — oddiy bitta file_id
                file_ids = [file_data]

        try:
            if file_ids:
                for i, fid in enumerate(file_ids, 1):
                    caption = f"✅ To'lovingiz tasdiqlandi!\n🎮 {name}" if i == 1 else f"📦 Qo'shimcha fayl ({i}/{len(file_ids)})"
                    await bot.send_document(chat_id=user_id, document=fid, caption=caption)
            elif link:
                await bot.send_message(user_id, f"✅ To'lovingiz tasdiqlandi!\n🔗 Link: {link}")
            else:
                await callback.answer("Fayl yoki link topilmadi!", show_alert=True)
                return

            await callback.message.edit_text(
                (callback.message.text or callback.message.caption or "") + "\n\n✅ FOYDALANUVCHIGA YUBORILDI"
            )
            await callback.answer("Muvaffaqiyatli yuborildi!")
        except Exception as e:
            error_text = str(e).lower()
            if "blocked" in error_text or "forbidden" in error_text or "chat not found" in error_text:
                await callback.answer("Foydalanuvchi botni bloklagan yoki start bosmagan!", show_alert=True)
            else:
                # Haqiqiy xatoni ko'rsatamiz (debug uchun)
                await callback.answer(f"Xato: {e}", show_alert=True)
                print(f"ADMIN_CONFIRM XATO: {e}")  # terminalda ko'rinadi

    else:
        # Buyurtma holati
        try:
            await bot.send_message(user_id, "Admin to'lovingizni tasdiqladi. Iltimos fayl kelishini kuting...")
            await bot.send_message(
                ADMIN_CHANNEL_ID,
                f"Iltimos buyurtma qilingan faylni tashlang!\nUser ID: <code>{user_id}</code>",
                parse_mode="HTML"
            )
            await callback.message.edit_text(
                (callback.message.text or "") + "\n\n✅ FOYDALANUVCHIGA XABAR YUBORILDI"
            )
            await callback.answer()
        except Exception as e:
            await callback.answer(f"Xato: {e}", show_alert=True)

# Admin reply (fayl yoki matn)
@dp.message(F.chat.id == ADMIN_CHANNEL_ID, F.reply_to_message)
async def admin_reply(message: Message):
    orig = message.reply_to_message.text or message.reply_to_message.caption or ""
    match = re.search(r"🆔 ID: <code>(\d+)</code>", orig) or re.search(r"ID: `?(\d+)`?", orig)
    if not match:
        return
    user_id = int(match.group(1))

    try:
        if message.document:
            await bot.send_document(user_id, document=message.document.file_id, caption=message.caption or "✅ Admin faylni yubordi")
            await message.reply("✅ Fayl foydalanuvchiga yuborildi.")
        elif message.photo:
            await bot.send_photo(user_id, photo=message.photo[-1].file_id, caption=message.caption or "✅ Admin rasm yubordi")
            await message.reply("✅ Rasm yuborildi.")
        elif message.text:
            await bot.send_message(user_id, f"👨‍💻 Admin: {message.text}")
            await message.reply("✅ Javob yuborildi.")
    except Exception as e:
        await message.reply(f"❌ Xato: {e}")

# ========== MAIN ==========
async def main():
    init_db()
    print("Bot ishlamoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())