
import os
import time
import json
import logging
import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, 
    InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler



# --- SOZLAMALAR ---
API_KEY = "8404752815:AAHgz0IIkmzWiplkGtXxH-Y0IKxaLzySRq0"  # Telegram Bot Token
ADMIN_ID = 8754614153
FRAGMENT_API_KEY = "5a16ed320f97f20a4076bbf1d2e2fc359c7bcd0d"  # Fragment API kalitingiz
FRAGMENT_BASE_URL = "https://fragment-api.uz/api/v1"
FOIZ = 2.63  # Ustiga qo'yiladigan foiz

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_KEY)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
# Render uchun soxta HTTP server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# Serverni orqa fonda (background thread) ishga tushirish
threading.Thread(target=run_dummy_server, daemon=True).start()
# --- FSM STATES ---
class UserState(StatesGroup):
    waiting_for_stars_amount = State()
    waiting_for_username = State()
    waiting_for_payment_amount = State()
    waiting_for_receipt = State()

class AdminState(StatesGroup):
    waiting_for_ref_reward = State()
    waiting_for_broadcast = State()
    waiting_for_channel = State()
    waiting_for_tizim = State()

# --- YORDAMCHI FUNKSIYALAR ---
def ensure_user_dirs(cid: int):
    os.makedirs(f"users/{cid}", exist_ok=True)
    os.makedirs("step", exist_ok=True)
    if not os.path.exists(f"users/{cid}/balance.txt"):
        with open(f"users/{cid}/balance.txt", "w") as f:
            f.write("0")
    if not os.path.exists(f"users/{cid}/kiritgan.txt"):
        with open(f"users/{cid}/kiritgan.txt", "w") as f:
            f.write("0")
    if not os.path.exists(f"users/{cid}/created.txt"):
        with open(f"users/{cid}/created.txt", "w") as f:
            f.write(str(int(time.time())))

def get_balance(cid: int) -> int:
    ensure_user_dirs(cid)
    try:
        with open(f"users/{cid}/balance.txt", "r") as f:
            return int(f.read().strip())
    except:
        return 0

def set_balance(cid: int, val: int):
    ensure_user_dirs(cid)
    with open(f"users/{cid}/balance.txt", "w") as f:
        f.write(str(val))

def get_kiritgan(cid: int) -> int:
    ensure_user_dirs(cid)
    try:
        with open(f"users/{cid}/kiritgan.txt", "r") as f:
            return int(f.read().strip())
    except:
        return 0

def set_kiritgan(cid: int, val: int):
    ensure_user_dirs(cid)
    with open(f"users/{cid}/kiritgan.txt", "w") as f:
        f.write(str(val))

def is_bot_active() -> bool:
    if os.path.exists("is_bot_active.txt"):
        with open("is_bot_active.txt", "r") as f:
            return f.read().strip() != "0"
    return True

# --- MENULAR ---
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌟 Stars olish")],
        [KeyboardButton(text="💵 Hisobim"), KeyboardButton(text="📥 Hisobni to'ldirish")],
        [KeyboardButton(text="💸 Pul ishlash")]
    ],
    resize_keyboard=True
)

back_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⏮️ Orqaga")]],
    resize_keyboard=True
)

# --- START VA ORQAGA ---
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    if not is_bot_active() and message.from_user.id != ADMIN_ID:
        await message.answer("🚧 Bot vaqtincha to'xtatilgan. Tez orada qaytadan ishga tushiriladi!")
        return

    await state.clear()
    cid = message.from_user.id
    ensure_user_dirs(cid)
    
    first_name = message.from_user.first_name or "Foydalanuvchi"
    import datetime
    vaqt = datetime.datetime.now().strftime("%H:%M %d/%m/%Y")

    text = (
        f"Assalomu Alaykum, <b>{first_name}</b>! 🌟\n\n"
        f"<blockquote>Bizning bot orqali arzon va sifatli <b>Telegram Stars</b> sotib olishingiz mumkin.\n"
        f"Botimizni tanlaganingizdan <b>hursandmiz</b>! </blockquote>\n\n"
        f"<i><b>{vaqt}</b></i>"
    )

    await message.answer(
        text=text,
        parse_mode="HTML",
        reply_markup=main_menu
    )

@router.message(F.text == "⏮️ Orqaga")
async def cmd_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bosh menyu:", reply_markup=main_menu)

# --- PUL ISHLASH (REFERAL) ---
@router.message(F.text == "💸 Pul ishlash")
async def cmd_earn(message: Message):
    cid = message.from_user.id
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={cid}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Do'stlarga ulashish", url=f"https://t.me/share/url?url={link}")]
    ])
    await message.answer(
        f"<b>📎 Sizning shaxsiy taklif havolangiz:</b>\n\n<code>{link}</code>\n\n"
        f"<b>Har bir taklif qilgan foydalanuvchi uchun sizga mukofot beriladi!</b>",
        parse_mode="HTML",
        reply_markup=kb
    )

# --- STARS SOTIB OLISH (FRAGMENT API) ---
@router.message(F.text == "🌟 Stars olish")
async def cmd_buy_stars(message: Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_stars_amount)
    await message.answer(
        "<b>📑 Sotib olmoqchi bo'lgan stars miqdorini yuboring:</b>\n<i>⚠️ Minimal: 50 ta, Maksimal: 10 000 000 ta</i>",
        parse_mode="HTML",
        reply_markup=back_menu
    )

@router.message(UserState.waiting_for_stars_amount)
async def process_stars_amount(message: Message, state: FSMContext):
    if message.text == "⏮️ Orqaga":
        await cmd_back(message, state)
        return
    
    if not message.text.isdigit():
        await message.answer("<b>🔢 Faqat raqamlardan foydalaning!</b>", parse_mode="HTML")
        return
    
    stars = int(message.text)
    if stars < 50 or stars > 10000000:
        await message.answer("<b>‼️ Stars miqdori 50 va 10 000 000 oralig'ida bo'lishi kerak!</b>", parse_mode="HTML")
        return
    
    await state.update_data(stars_amount=stars)
    await state.set_state(UserState.waiting_for_username)
    await message.answer(
        "<b>👤 Kimga yubormoqchisiz ❓\n🔗 Usernameni yuboring yoki o'zingizga olmoqchi bo'lsangiz o'zingizni userigizni yuboring ✅</b>\n\n"
        "<blockquote>📋 Na'muna: @durov yoki durov</blockquote>",
        parse_mode="HTML",
        reply_markup=back_menu
    )

@router.message(UserState.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    if message.text == "⏮️ Orqaga":
        await cmd_back(message, state)
        return
    
    raw_username = message.text.strip().replace("@", "")
    data = await state.get_data()
    stars = data.get("stars_amount")
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": FRAGMENT_API_KEY
    }
    payload = {"amount": stars}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{FRAGMENT_BASE_URL}/stars/pricing", json=payload, headers=headers) as resp:
                res_json = await resp.json()
                if resp.status == 200 and res_json.get("ok"):
                    # Fragment API javobi: result -> price -> usd
                    usd_price = float(res_json.get("result", {}).get("price", {}).get("usd", 0))
                    base_soom = usd_price * 12800  # 1 USD = 12800 so'm kurs bo'yicha
                    aniq_narx = base_soom + (base_soom * FOIZ / 100)
                else:
                    msg = res_json.get("message", "Narxni olib bo'lmadi")
                    await message.answer(f"<b>⚠️ Xatolik:</b> {msg}", parse_mode="HTML")
                    return
        except Exception as e:
            await message.answer(f"<b>⚠️ Fragment API serverida xatolik yuz berdi!</b>", parse_mode="HTML")
            return

    text = (
        f"<b>☑️ Qabul qilindi 👇</b>\n\n"
        f"<blockquote><b>🌟 Stars miqdori:</b> <u>{stars}</u>\n"
        f"<b>👤 Username:</b> @{raw_username}\n"
        f"<b>💰 Hisoblangan narx:</b> <u>{int(aniq_narx):,} so'm</u></blockquote>\n\n"
        f"<b>❗️ Agar stars narxi sizga ma'qul kelgan bo'lsa pastdagi «🛒 Sotib olish» tugmasini bosing ✅</b>"
    )
    
    # Callback data xavfsiz formatda yuboriladi (max 64 bayt limiti uchun)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Sotib olish", callback_data=f"stb_{stars}_{int(aniq_narx)}_{raw_username}")]
    ])
    
    await message.answer(text=text, parse_mode="HTML", reply_markup=kb)
    await state.clear()

@router.callback_query(F.data.startswith("stb_"))
async def callback_buy_action(call: CallbackQuery):
    # Callback_data ni xavfsiz ajratib olish (split maxsplit=3)
    try:
        _, stars_str, jami_str, username = call.data.split("_", 3)
        stars = int(stars_str)
        jami = int(jami_str)
    except Exception:
        await call.answer("Ma'lumotlarni o'qishda xatolik yuz berdi!", show_alert=True)
        return

    cid2 = call.message.chat.id
    balance = get_balance(cid2)
    
    if balance >= jami:
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": FRAGMENT_API_KEY
        }
        payload = {
            "username": username,
            "amount": stars
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{FRAGMENT_BASE_URL}/stars/buy", json=payload, headers=headers) as resp:
                    res_json = await resp.json()
                    if resp.status == 200 and res_json.get("ok"):
                        set_balance(cid2, balance - jami)
                        msg = res_json.get("message", "Stars muvaffaqiyatli yuborildi!")
                        await call.message.delete()
                        await call.message.answer(f"✅ <b>{msg}</b>", parse_mode="HTML")
                    else:
                        code = res_json.get("code", "XATO")
                        msg = res_json.get("message", "Xarid amalga oshmadi.")
                        await call.message.delete()
                        await call.message.answer(f"<b>‼️ Xatolik ({code}):</b> {msg}", parse_mode="HTML")
            except Exception:
                await call.message.delete()
                await call.message.answer("<b>‼️ Server bilan ulanishda kutilmagan xatolik!</b>", parse_mode="HTML")
    else:
        yetma = jami - balance
        await call.message.delete()
        await call.message.answer(
            f"<b>⛔️ Hisobingizda yetarli mablag' mavjud emas!</b>\n<i>💰 Sizga yana {yetma} so'm yetishmayapti</i>",
            parse_mode="HTML",
            reply_markup=main_menu
        )
    await call.answer()

# --- HISOBIM ---
@router.message(F.text == "💵 Hisobim")
async def cmd_my_account(message: Message):
    cid = message.from_user.id
    balance = get_balance(cid)
    kiritgan = get_kiritgan(cid)
    
    text = (
        f"<b>👤 Sizning shaxsiy kabinet</b>\n\n"
        f"🆔 <b>ID raqamingiz:</b> <code>{cid}</code>\n"
        f"💰 <b>Joriy balans:</b> <code>{balance} so'm</code>\n"
        f"💳 <b>Jami kiritilgan:</b> <code>{kiritgan} so'm</code>\n\n"
        f"🛡️ Maxfiylik va xavfsizlik kafolatlangan."
    )
    await message.answer(text=text, parse_mode="HTML", reply_markup=main_menu)

# --- HISOBNI TO'LDIRISH ---
@router.message(F.text == "📥 Hisobni to'ldirish")
async def cmd_top_up(message: Message):
    tizimlar_file = "tizimlar.json"
    tizim_list = []
    if os.path.exists(tizimlar_file):
        with open(tizimlar_file, "r") as f:
            try:
                tizim_list = json.load(f)
            except:
                tizim_list = []
    
    if not tizim_list:
        tizim_list = [{'nomi': 'Humo Card', 'karta': '9860120118578885'}]
        
    inline_kb = []
    for t in tizim_list:
        inline_kb.append([InlineKeyboardButton(text=f"🔰 {t['nomi']}", callback_data=f"tizim_{t['nomi']}_{t['karta']}")])
        
    await message.answer(
        "<b>💳 Quyidagi to'lov tizimlaridan birini tanlang:</b>\n"
        "<blockquote>Ushbu to'lov tizimlari botdagi eng xavfsiz to'lov tizimi</blockquote>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=inline_kb)
    )

@router.callback_query(F.data.startswith("tizim_"))
async def callback_select_tizim(call: CallbackQuery):
    _, tizim, karta = call.data.split("_", 2)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tashladim", callback_data=f"tash_{tizim}")]
    ])
    await call.message.delete()
    await call.message.answer(
        f"<b>📱 To'lov tizimi:</b> <u>{tizim}</u>\n"
        f"<b>💳 Karta raqami:</b> <code>{karta}</code>\n\n"
        f"<blockquote><i>⏳ Ushbu kartani nusxalab bank ilovalariga kirib o'zingizga kerakli summani tashlab pastdagi</i> «<b>✅ Tashladim</b>» <i>tugmasini ustiga bosing 👇</i></blockquote>",
        parse_mode="HTML",
        reply_markup=kb
    )
    await call.answer()

@router.callback_query(F.data.startswith("tash_"))
async def callback_tashladim(call: CallbackQuery, state: FSMContext):
    _, tizim = call.data.split("_", 1)
    await call.message.delete()
    await state.update_data(top_up_system=tizim)
    await state.set_state(UserState.waiting_for_payment_amount)
    await call.message.answer("<b>⁉️ Kartaga qancha summa tashlaganingizni yuboring:</b>", parse_mode="HTML", reply_markup=back_menu)
    await call.answer()

@router.message(UserState.waiting_for_payment_amount)
async def process_payment_amount(message: Message, state: FSMContext):
    if message.text == "⏮️ Orqaga":
        await cmd_back(message, state)
        return
    if not message.text.isdigit():
        await message.answer("<b>⚠️ Faqat raqamlardan foydalaning!</b>", parse_mode="HTML", reply_markup=back_menu)
        return
    
    summa = int(message.text)
    if summa < 1000:
        await message.answer("<b>‼️ Minimal pul kiritish miqdori: 1000 so'm</b>", parse_mode="HTML", reply_markup=back_menu)
        return
    
    await state.update_data(top_up_summa=summa)
    await state.set_state(UserState.waiting_for_receipt)
    await message.answer("<b>🖼 Endi shu kartaga pul tashlaganingiz haqidagi chek rasmini yuboring:</b>", parse_mode="HTML", reply_markup=back_menu)

@router.message(UserState.waiting_for_receipt, F.photo)
async def process_receipt_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    tizim = data.get("top_up_system")
    summa = data.get("top_up_summa")
    cid = message.from_user.id
    balance = get_balance(cid)
    
    photo_file_id = message.photo[-1].file_id
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tastiqlash", callback_data=f"tas_{cid}_{summa}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"bekor_{cid}_{summa}")]
    ])
    
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_file_id,
        caption=(
            f"<b>⌛ Hisob to'ldirish bo'yicha so'rov!</b>\n\n"
            f"<blockquote>💳 To'lov tizimi: <u>{tizim}</u>\n"
            f"<b>💸 To'ldirmoqchi bo'lgan summa:</b> {summa} so'm\n"
            f"<b>🆔 Foydalanuvchi ID raqami:</b> {cid}\n"
            f"<b>💰 Hisobi:</b> {balance} so'm</blockquote>"
        ),
        parse_mode="HTML",
        reply_markup=admin_kb
    )
    
    await message.answer("<b>✅ So'rovingiz administratorlarga yuborildi!</b>", parse_mode="HTML", reply_markup=main_menu)
    await state.clear()

@router.message(UserState.waiting_for_receipt)
async def process_receipt_not_photo(message: Message, state: FSMContext):
    if message.text == "⏮️ Orqaga":
        await cmd_back(message, state)
        return
    await message.answer("<b>‼️ Iltimos, faqat chek rasmini yuboring!</b>", parse_mode="HTML", reply_markup=back_menu)

@router.callback_query(F.data.startswith("tas_") | F.data.startswith("bekor_"))
async def admin_verify_payment(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Siz admin emassiz!", show_alert=True)
        return
        
    action, user_id_str, summa_str = call.data.split("_")
    user_id = int(user_id_str)
    summa = int(summa_str)
    
    if action == "tas":
        bal = get_balance(user_id)
        set_balance(user_id, bal + summa)
        kir = get_kiritgan(user_id)
        set_kiritgan(user_id, kir + summa)
        
        await call.message.delete()
        await call.message.answer("✅ Tastiqlandi!", parse_mode="HTML")
        await bot.send_message(user_id, f"<b>➕ Hisobingizga +{summa} so'm qo'shildi!</b>", parse_mode="HTML")
    else:
        await call.message.delete()
        await call.message.answer("❌ Tastiqlanmadi!", parse_mode="HTML")
        await bot.send_message(user_id, "<b>🚫 So'rovingiz tastiqlanmadi, sababi soxta chek tashlagansiz!</b>", parse_mode="HTML")
    await call.answer()

# --- ADMIN PANEL ---
@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    
    bot_active = "1"
    if os.path.exists("is_bot_active.txt"):
        with open("is_bot_active.txt", "r") as f:
            bot_active = f.read().strip()
    status_text = "🟢 Bot aktiv" if bot_active == "1" else "🔴 Bot nofaol"
    
    admin_menu = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📤 Xabar yuborish")],
            [KeyboardButton(text="🔗 Majburiy obuna"), KeyboardButton(text="💳 To'lov tizimlari")],
            [KeyboardButton(text="⚙️ Botni o'chirish/yoqish"), KeyboardButton(text="👥 Referal sozlamalari")],
            [KeyboardButton(text="⏮️ Orqaga")]
        ],
        resize_keyboard=True
    )
    await message.answer(f"<b>🛠 Admin Paneli</b>\n{status_text}", parse_mode="HTML", reply_markup=admin_menu)

# Admin: Statistika
@router.message(F.text == "📊 Statistika", F.from_user.id == ADMIN_ID)
async def admin_stats(message: Message):
    users_dir = "users"
    total_users = 0
    today_users = 0
    today_str = time.strftime("%Y-%m-%d")
    
    if os.path.exists(users_dir):
        dirs = [name for name in os.listdir(users_dir) if os.path.isdir(os.path.join(users_dir, name))]
        total_users = len(dirs)
        for u in dirs:
            created_file = f"users/{u}/created.txt"
            if os.path.exists(created_file):
                with open(created_file, "r") as f:
                    ctime = int(f.read().strip())
                    if time.strftime("%Y-%m-%d", time.localtime(ctime)) == today_str:
                        today_users += 1

    await message.answer(
        f"<b>📊 Statistika:</b>\n\n"
        f"👥 Jami foydalanuvchilar: <code>{total_users}</code>\n"
        f"🆕 Bugun qo'shilgan: <code>{today_users}</code>",
        parse_mode="HTML"
    )

# Admin: Xabar yuborish
@router.message(F.text == "📤 Xabar yuborish", F.from_user.id == ADMIN_ID)
async def admin_broadcast_prompt(message: Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_broadcast)
    await message.answer(
        "<b>📤 Xabar yuborish:</b>\n\n"
        "1. <b>Hammasiga</b> xabar yuborish uchun shunchaki matn yuboring.\n"
        "2. Bitta foydalanuvchiga yuborish uchun: <code>ID_RAQAM Xabar</code> ko'rinishida yuboring.",
        parse_mode="HTML",
        reply_markup=back_menu
    )

@router.message(AdminState.waiting_for_broadcast, F.from_user.id == ADMIN_ID)
async def admin_broadcast_process(message: Message, state: FSMContext):
    if message.text == "⏮️ Orqaga":
        await cmd_admin(message, state)
        return
        
    text = message.text
    if " " in text and text.split()[0].isdigit():
        target_id, msg = text.split(" ", 1)
        try:
            await bot.send_message(chat_id=int(target_id), text=msg, parse_mode="HTML")
            await message.answer(f"✅ {target_id} ga yuborildi!")
        except Exception as e:
            await message.answer(f"❌ Xatolik: {e}")
    else:
        users_dir = "users"
        sent = 0
        if os.path.exists(users_dir):
            dirs = [name for name in os.listdir(users_dir) if os.path.isdir(os.path.join(users_dir, name))]
            for uid in dirs:
                if uid.isdigit():
                    try:
                        await bot.send_message(chat_id=int(uid), text=text, parse_mode="HTML")
                        sent += 1
                    except Exception:
                        pass
        await message.answer(f"✅ {sent} ta foydalanuvchiga yuborildi!")
    await state.clear()

# Admin: Majburiy obuna
@router.message(F.text == "🔗 Majburiy obuna", F.from_user.id == ADMIN_ID)
async def admin_channel_prompt(message: Message, state: FSMContext):
    channel = "Mavjud emas"
    if os.path.exists("channel.txt"):
        with open("channel.txt", "r") as f:
            channel = f.read().strip()
            
    await state.set_state(AdminState.waiting_for_channel)
    await message.answer(
        f"<b>🔗 Majburiy obuna kanali:</b>\n<code>{channel}</code>\n\n"
        "Kanal usernameni (@...) yuboring yoki o'chirish uchun <code>0</code> yozing.",
        parse_mode="HTML",
        reply_markup=back_menu
    )

@router.message(AdminState.waiting_for_channel, F.from_user.id == ADMIN_ID)
async def admin_channel_process(message: Message, state: FSMContext):
    if message.text == "⏮️ Orqaga":
        await cmd_admin(message, state)
        return
        
    if message.text == "0":
        if os.path.exists("channel.txt"):
            os.remove("channel.txt")
        await message.answer("❌ Kanal olib tashlandi!")
    elif message.text.startswith("@"):
        with open("channel.txt", "w") as f:
            f.write(message.text)
        await message.answer(f"✅ Kanal saqlandi: {message.text}")
    else:
        await message.answer("⚠️ Username @ bilan boshlanishi kerak!")
    await state.clear()

# Admin: To'lov tizimlari
@router.message(F.text == "💳 To'lov tizimlari", F.from_user.id == ADMIN_ID)
async def admin_tizim_prompt(message: Message, state: FSMContext):
    tizimlar_file = "tizimlar.json"
    tizimlar = []
    if os.path.exists(tizimlar_file):
        with open(tizimlar_file, "r") as f:
            try:
                tizimlar = json.load(f)
            except:
                tizimlar = []
                
    list_str = "Mavjud tizimlar:\n"
    for t in tizimlar:
        list_str += f"• {t['nomi']} → {t['karta']}\n"
        
    await state.set_state(AdminState.waiting_for_tizim)
    await message.answer(
        f"<b>💳 To'lov tizimlari</b>\n\n{list_str}\n"
        "Yangi qo'shish uchun: <code>Nomi—KartaRaqami</code> (masalan: <code>Humo—9860246601773509</code>)\n"
        "O'chirish uchun: <code>del—Nomi</code>",
        parse_mode="HTML",
        reply_markup=back_menu
    )

@router.message(AdminState.waiting_for_tizim, F.from_user.id == ADMIN_ID)
async def admin_tizim_process(message: Message, state: FSMContext):
    if message.text == "⏮️ Orqaga":
        await cmd_admin(message, state)
        return
        
    tizimlar_file = "tizimlar.json"
    tizimlar = []
    if os.path.exists(tizimlar_file):
        with open(tizimlar_file, "r") as f:
            try:
                tizimlar = json.load(f)
            except:
                tizimlar = []
                
    text = message.text
    if text.startswith("del—"):
        nom = text.replace("del—", "")
        tizimlar = [t for t in tizimlar if t['nomi'] != nom]
        with open(tizimlar_file, "w") as f:
            json.dump(tizimlar, f)
        await message.answer(f"✅ {nom} o'chirildi!")
    elif "—" in text:
        nomi, karta = text.split("—", 1)
        if karta.isdigit():
            tizimlar.append({"nomi": nomi, "karta": karta})
            with open(tizimlar_file, "w") as f:
                json.dump(tizimlar, f)
            await message.answer(f"✅ {nomi} qo'shildi!")
        else:
            await message.answer("❌ Karta raqam faqat raqamlardan iborat bo'lishi kerak!")
    else:
        await message.answer("❌ Noto'g'ri format!")
    await state.clear()

# Admin: Referal sozlamalari
@router.message(F.text == "👥 Referal sozlamalari", F.from_user.id == ADMIN_ID)
async def admin_ref_prompt(message: Message, state: FSMContext):
    reward = 100
    if os.path.exists("ref_reward.txt"):
        with open("ref_reward.txt", "r") as f:
            try:
                reward = int(f.read().strip())
            except:
                pass
                
    await state.set_state(AdminState.waiting_for_ref_reward)
    await message.answer(
        f"<b>👥 Referal sozlamalari</b>\n\n"
        f"🔹 Hozirgi mukofot: <code>{reward} so'm</code>\n\n"
        "Yangi mukofot miqdorini yuboring (masalan: 150):",
        parse_mode="HTML",
        reply_markup=back_menu
    )

@router.message(AdminState.waiting_for_ref_reward, F.from_user.id == ADMIN_ID)
async def admin_ref_process(message: Message, state: FSMContext):
    if message.text == "⏮️ Orqaga":
        await cmd_admin(message, state)
        return
        
    if message.text.isdigit() and int(message.text) > 0:
        val = int(message.text)
        with open("ref_reward.txt", "w") as f:
            f.write(str(val))
        await message.answer(f"✅ Referal mukofoti o'zgartirildi: <b>{val} so'm</b>", parse_mode="HTML")
    else:
        await message.answer("❌ Iltimos, musbat raqam kiriting!")
    await state.clear()

# Admin: Botni o'chirish/yoqish
@router.message(F.text == "⚙️ Botni o'chirish/yoqish", F.from_user.id == ADMIN_ID)
async def admin_toggle_bot(message: Message):
    bot_active = "1"
    if os.path.exists("is_bot_active.txt"):
        with open("is_bot_active.txt", "r") as f:
            bot_active = f.read().strip()
            
    if bot_active == "1":
        with open("is_bot_active.txt", "w") as f:
            f.write("0")
        await message.answer("🔴 Bot hozir nofaol!")
    else:
        with open("is_bot_active.txt", "w") as f:
            f.write("1")
        await message.answer("🟢 Bot qayta faollashtirildi!")

# --- ISHGA TUSHIRISH ---
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


# Render uchun soxta HTTP server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# Serverni orqa fonda (background thread) ishga tushirish
threading.Thread(target=run_dummy_server, daemon=True).start()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())