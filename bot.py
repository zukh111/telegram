"""
Ilmla Ta'lim Markazi — Telegram Bot
=====================================
Features:
  - Uzbek language UI
  - Student registration (Full name, Phone, Age, Course)
  - Admin notifications on each registration
  - Admin panel: stats, broadcast, student list
  - FAQ section
  - Admin contact info display
"""

import logging
import sqlite3
from datetime import datetime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes,
    filters
)

# ──────────────────────────────────────────────
#  CONFIG  —  BULARNI O'ZGARTIRING
# ──────────────────────────────────────────────
BOT_TOKEN = "8780819051:AAFAAU_Laq67yUaFyq3HLtOsE8yKekR_wtk"          # @BotFather dan oling
OWNER_ID  = 6702104500                      # Sizning Telegram ID raqamingiz

ADMIN_INFO = {
    "name":     "Sardor Toshmatov",
    "phone":    "+998 90 123 45 67",
    "telegram": "@sardor_ilmla",
    "hours":    "Du-Sha: 09:00-18:00",
}

COURSES = ["English", "IT"]

# ──────────────────────────────────────────────
#  STATES
# ──────────────────────────────────────────────
REG_NAME, REG_PHONE, REG_AGE, REG_COURSE = range(4)

# ──────────────────────────────────────────────
#  LOGGING
# ──────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("ilmla_bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  DATABASE
# ──────────────────────────────────────────────
DB_PATH = "ilmla.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id         INTEGER,
            username      TEXT,
            full_name     TEXT,
            phone         TEXT,
            age           INTEGER,
            course        TEXT,
            registered_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS faq (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer   TEXT
        )
    """)
    c.execute("SELECT COUNT(*) FROM faq")
    if c.fetchone()[0] == 0:
        faqs = [
            ("Darslar qachon boshlanadi?",  "Har oyning 1-sanasidan yangi guruhlar tashkil etiladi."),
            ("Narxlar qancha?",             "English kursi: 350,000 som/oy. IT kursi: 450,000 som/oy."),
            ("Manzil qayerda?",             ADMIN_INFO["address"]),
            ("Ish vaqtlari?",               ADMIN_INFO["hours"]),
            ("Sinov darsi bormi?",          "Ha! Birinchi dars bepul va majburiyatsiz."),
        ]
        c.executemany("INSERT INTO faq (question, answer) VALUES (?,?)", faqs)
    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect(DB_PATH)

# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────
def is_admin(uid):
    return uid == OWNER_ID

def main_menu(uid):
    rows = [
        ["📝 Ro'yxatdan o'tish", "📚 Kurslar haqida"],
        ["❓ FAQ",                "📞 Admin bilan bog'lanish"],
    ]
    if is_admin(uid):
        rows.append(["⚙️ Admin panel"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Statistika",           callback_data="adm_stats")],
        [InlineKeyboardButton("👥 O'quvchilar ro'yxati", callback_data="adm_list")],
        [InlineKeyboardButton("📢 Xabar yuborish",       callback_data="adm_broadcast")],
        [InlineKeyboardButton("❓ FAQ boshqaruv",         callback_data="adm_faq")],
    ])

# ──────────────────────────────────────────────
#  /start
# ──────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🎓 *Ilmla Ta'lim Markaziga xush kelibsiz!*\n\n"
        f"Salom, {user.first_name}! 👋\n"
        f"Quyidagi menyudan birini tanlang:",
        parse_mode="Markdown",
        reply_markup=main_menu(user.id)
    )

# ──────────────────────────────────────────────
#  COURSES INFO
# ──────────────────────────────────────────────
async def courses_info(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *Ilmla'dagi kurslar:*\n\n"
        "🇬🇧 *English kursi*\n"
        "- Darajalar: Beginner - Advanced\n"
        "- Dars: hafta 3 marta (1.5 soat)\n"
        "- Narx: 350,000 so'm/oy\n\n"
        "💻 *IT kursi*\n"
        "- Yo'nalishlar: Python, Web, UI/UX\n"
        "- Dars: hafta 3 marta (2 soat)\n"
        "- Narx: 450,000 so'm/oy",
        parse_mode="Markdown"
    )

# ──────────────────────────────────────────────
#  ADMIN CONTACT
# ──────────────────────────────────────────────
async def admin_contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ai = ADMIN_INFO
    await update.message.reply_text(
        "📞 *Admin bilan bog'lanish:*\n\n"
        f"👤 Ism: {ai['name']}\n"
        f"📱 Telefon: `{ai['phone']}`\n"
        f"💬 Telegram: {ai['telegram']}\n"
        f"📍 Manzil: {ai['address']}\n"
        f"🕐 Ish vaqti: {ai['hours']}",
        parse_mode="Markdown"
    )

# ──────────────────────────────────────────────
#  FAQ
# ──────────────────────────────────────────────
async def faq_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    faqs = conn.execute("SELECT id, question FROM faq").fetchall()
    conn.close()
    if not faqs:
        await update.message.reply_text("Hozircha FAQ mavjud emas.")
        return
    buttons = [[InlineKeyboardButton(q, callback_data=f"faq_{fid}")] for fid, q in faqs]
    await update.message.reply_text(
        "❓ *Savolni tanlang:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def faq_answer_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    fid = int(q.data.split("_")[1])
    conn = get_db()
    row = conn.execute("SELECT question, answer FROM faq WHERE id=?", (fid,)).fetchone()
    conn.close()
    if row:
        await q.edit_message_text(
            f"❓ *{row[0]}*\n\n💡 {row[1]}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="faq_back")
            ]])
        )

async def faq_back_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    conn = get_db()
    faqs = conn.execute("SELECT id, question FROM faq").fetchall()
    conn.close()
    buttons = [[InlineKeyboardButton(q2, callback_data=f"faq_{fid}")] for fid, q2 in faqs]
    await q.edit_message_text(
        "❓ *Savolni tanlang:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ──────────────────────────────────────────────
#  REGISTRATION
# ──────────────────────────────────────────────
CANCEL_KB = ReplyKeyboardMarkup([["❌ Bekor qilish"]], resize_keyboard=True)

async def reg_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    exists = conn.execute("SELECT id FROM students WHERE tg_id=?", (update.effective_user.id,)).fetchone()
    conn.close()
    if exists:
        await update.message.reply_text(
            "✅ Siz allaqachon ro'yxatdan o'tgansiz!\nSavollar uchun adminга murojaat qiling.",
            reply_markup=main_menu(update.effective_user.id)
        )
        return ConversationHandler.END
    await update.message.reply_text(
        "📝 *Ro'yxatdan o'tish*\n\nIsm va familiyangizni kiriting:\n_(Masalan: Sardor Toshmatov)_",
        parse_mode="Markdown",
        reply_markup=CANCEL_KB
    )
    return REG_NAME

async def reg_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await reg_cancel(update, ctx)
    ctx.user_data["name"] = update.message.text.strip()
    await update.message.reply_text(
        "📱 Telefon raqamingizni yuboring:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Raqamni ulashish", request_contact=True)], ["❌ Bekor qilish"]],
            resize_keyboard=True
        )
    )
    return REG_PHONE

async def reg_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await reg_cancel(update, ctx)
    if update.message.contact:
        phone = update.message.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone
    else:
        phone = update.message.text.strip()
    ctx.user_data["phone"] = phone
    await update.message.reply_text("🎂 Yoshingizni kiriting: _(Masalan: 17)_",
                                    parse_mode="Markdown", reply_markup=CANCEL_KB)
    return REG_AGE

async def reg_age(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await reg_cancel(update, ctx)
    t = update.message.text.strip()
    if not t.isdigit() or not (5 <= int(t) <= 99):
        await update.message.reply_text("⚠️ To'g'ri yosh kiriting (5-99):")
        return REG_AGE
    ctx.user_data["age"] = int(t)
    course_rows = [[c] for c in COURSES] + [["❌ Bekor qilish"]]
    await update.message.reply_text(
        "📚 Qaysi kursga yozilmoqchisiz?",
        reply_markup=ReplyKeyboardMarkup(course_rows, resize_keyboard=True)
    )
    return REG_COURSE

async def reg_course(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Bekor qilish":
        return await reg_cancel(update, ctx)
    course = update.message.text.strip()
    if course not in COURSES:
        await update.message.reply_text("⚠️ Ro'yxatdan kursni tanlang.")
        return REG_COURSE

    user = update.effective_user
    now  = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_db()
    conn.execute(
        "INSERT INTO students (tg_id,username,full_name,phone,age,course,registered_at) VALUES (?,?,?,?,?,?,?)",
        (user.id, user.username or "", ctx.user_data["name"],
         ctx.user_data["phone"], ctx.user_data["age"], course, now)
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ *Tabriklaymiz! Ro'yxatdan o'tdingiz!*\n\n"
        f"👤 {ctx.user_data['name']}\n"
        f"📱 {ctx.user_data['phone']}\n"
        f"🎂 {ctx.user_data['age']} yosh\n"
        f"📚 {course}\n\n"
        f"Adminlarimiz tez orada bog'lanishadi. 🎓",
        parse_mode="Markdown",
        reply_markup=main_menu(user.id)
    )

    # Notify owner
    try:
        ulink = f"@{user.username}" if user.username else f"ID: {user.id}"
        await ctx.bot.send_message(
            OWNER_ID,
            f"🔔 *Yangi o'quvchi!*\n\n"
            f"👤 {ctx.user_data['name']}\n"
            f"📱 `{ctx.user_data['phone']}`\n"
            f"🎂 {ctx.user_data['age']} yosh\n"
            f"📚 {course}\n"
            f"💬 {ulink}\n"
            f"🕐 {now}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"Owner xabardor qilishda xato: {e}")

    ctx.user_data.clear()
    return ConversationHandler.END

async def reg_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.", reply_markup=main_menu(update.effective_user.id))
    return ConversationHandler.END

# ──────────────────────────────────────────────
#  ADMIN PANEL
# ──────────────────────────────────────────────
async def admin_panel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Ruxsat yo'q.")
        return
    await update.message.reply_text(
        "⚙️ *Admin paneli*",
        parse_mode="Markdown",
        reply_markup=admin_kb()
    )

async def admin_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(q.from_user.id):
        await q.edit_message_text("⛔ Ruxsat yo'q.")
        return

    data = q.data

    if data == "adm_stats":
        conn = get_db()
        total   = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        courses = conn.execute("SELECT course, COUNT(*) FROM students GROUP BY course").fetchall()
        today   = conn.execute(
            "SELECT COUNT(*) FROM students WHERE registered_at LIKE ?",
            (datetime.now().strftime("%Y-%m-%d") + "%",)
        ).fetchone()[0]
        conn.close()
        lines = "\n".join(f"  {c}: *{n}* ta" for c, n in courses)
        await q.edit_message_text(
            f"📊 *Statistika*\n\n"
            f"Jami: *{total}*\n"
            f"Bugun: *{today}*\n\n"
            f"Kurslar:\n{lines}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="adm_back")]])
        )

    elif data == "adm_list":
        conn = get_db()
        rows = conn.execute(
            "SELECT full_name,phone,age,course,registered_at FROM students ORDER BY id DESC LIMIT 20"
        ).fetchall()
        conn.close()
        if not rows:
            text = "Hali o'quvchilar yo'q."
        else:
            lines = [f"{i}. *{n}* | {p} | {a} yosh | {c}\n   _{d}_"
                     for i, (n, p, a, c, d) in enumerate(rows, 1)]
            text = "👥 *So'nggi 20 o'quvchi:*\n\n" + "\n\n".join(lines)
        await q.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="adm_back")]])
        )

    elif data == "adm_broadcast":
        await q.edit_message_text(
            "📢 Barcha o'quvchilarga yuboriladigan xabarni yozing:\n\n_(Bekor qilish: /cancel)_",
            parse_mode="Markdown"
        )
        ctx.user_data["broadcast"] = True

    elif data == "adm_faq":
        conn = get_db()
        faqs = conn.execute("SELECT id, question FROM faq").fetchall()
        conn.close()
        text = "❓ *FAQ ro'yxati:*\n\n"
        for fid, fq in faqs:
            text += f"[{fid}] {fq}\n"
        text += "\nYangi qo'shish: /addfaq Savol | Javob\nO'chirish: /delfaq ID"
        await q.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="adm_back")]])
        )

    elif data == "adm_back":
        await q.edit_message_text(
            "⚙️ *Admin paneli*",
            parse_mode="Markdown",
            reply_markup=admin_kb()
        )

# ──────────────────────────────────────────────
#  BROADCAST
# ──────────────────────────────────────────────
async def handle_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.user_data.get("broadcast"):
        return False
    ctx.user_data.pop("broadcast")
    msg = update.message.text
    conn = get_db()
    ids = [r[0] for r in conn.execute("SELECT DISTINCT tg_id FROM students").fetchall()]
    conn.close()
    sent = fail = 0
    for uid in ids:
        try:
            await ctx.bot.send_message(uid, f"📢 *Ilmla Ta'lim Markazi:*\n\n{msg}", parse_mode="Markdown")
            sent += 1
        except:
            fail += 1
    await update.message.reply_text(
        f"✅ Yuborildi!\n✔️ Muvaffaqiyatli: {sent}\n❌ Xatolik: {fail}",
        reply_markup=main_menu(update.effective_user.id)
    )
    return True

# ──────────────────────────────────────────────
#  /addfaq  /delfaq
# ──────────────────────────────────────────────
async def add_faq(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    text = update.message.text.replace("/addfaq", "").strip()
    if "|" not in text:
        await update.message.reply_text("Format: /addfaq Savol | Javob")
        return
    q, a = [x.strip() for x in text.split("|", 1)]
    conn = get_db()
    conn.execute("INSERT INTO faq (question,answer) VALUES (?,?)", (q, a))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Qo'shildi:\n❓ {q}\n💡 {a}")

async def del_faq(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    text = update.message.text.replace("/delfaq", "").strip()
    if not text.isdigit():
        await update.message.reply_text("Format: /delfaq ID")
        return
    conn = get_db()
    conn.execute("DELETE FROM faq WHERE id=?", (int(text),))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ FAQ [{text}] o'chirildi.")

# ──────────────────────────────────────────────
#  /cancel
# ──────────────────────────────────────────────
async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.", reply_markup=main_menu(update.effective_user.id))
    return ConversationHandler.END

# ──────────────────────────────────────────────
#  GENERAL MESSAGE HANDLER
# ──────────────────────────────────────────────
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await handle_broadcast(update, ctx):
        return
    t = update.message.text
    if t == "📚 Kurslar haqida":
        await courses_info(update, ctx)
    elif t == "📞 Admin bilan bog'lanish":
        await admin_contact(update, ctx)
    elif t == "❓ FAQ":
        await faq_menu(update, ctx)
    elif t == "⚙️ Admin panel":
        await admin_panel(update, ctx)
    else:
        await update.message.reply_text(
            "Menyudan birini tanlang 👇",
            reply_markup=main_menu(update.effective_user.id)
        )

# ──────────────────────────────────────────────
#  MAIN  —  plain def, no asyncio.run needed
# ──────────────────────────────────────────────
def main():
    init_db()
    logger.info("Ilmla bot ishga tushmoqda...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    reg_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Ro'yxatdan o'tish$"), reg_start)],
        states={
            REG_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            REG_PHONE:  [MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, reg_phone)],
            REG_AGE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_age)],
            REG_COURSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_course)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex("^❌ Bekor qilish$"), reg_cancel),
        ]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("addfaq", add_faq))
    app.add_handler(CommandHandler("delfaq", del_faq))
    app.add_handler(reg_conv)
    app.add_handler(CallbackQueryHandler(faq_answer_cb, pattern=r"^faq_\d+$"))
    app.add_handler(CallbackQueryHandler(faq_back_cb,   pattern=r"^faq_back$"))
    app.add_handler(CallbackQueryHandler(admin_cb,      pattern=r"^adm_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
