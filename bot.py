import logging
import os
import sqlite3
from datetime import datetime, timedelta
from threading import Thread

from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ---------------------------------------------------------
# 1. FLASK SERVER (ለ Render 24/7 Port)
# ---------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Ethio Shop Builder Bot is Running 24/7!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# ---------------------------------------------------------
# 2. LOGGING CONFIGURATION
# ---------------------------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ---------------------------------------------------------
# 3. CONFIGURATION & CONSTANTS
# ---------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8770076033:AAGNZ-Obug4bN_Yb_MzPJzy2-La6fb_W7lg")
ADMIN_USER_ID = 5997262731  # የሃይሌ Admin User ID

ACCOUNT_HOLDER = "Hailemichael Mebrate"
TELEBIRR_NO = "0979484319"
AWASH_NO = "013201354775100"
DASHEN_NO = "5121945801011"
ABYSSINIA_NO = "226261346"

NAME, PHONE, ADDRESS, QUANTITY, PAYMENT_RECEIPT = range(5)

# ---------------------------------------------------------
# 4. DATABASE MANAGEMENT
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            expire_date TEXT,
            is_trial_used INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_user_sub(user_id):
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT expire_date, is_trial_used FROM subscriptions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def is_user_active(user_id):
    row = get_user_sub(user_id)
    if row and row[0]:
        expire_date = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < expire_date:
            return True, expire_date
    return False, None

def set_user_sub(user_id, days, mark_trial=False):
    expire_date = datetime.now() + timedelta(days=days)
    expire_str = expire_date.strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    if mark_trial:
        cursor.execute(
            "INSERT OR REPLACE INTO subscriptions (user_id, expire_date, is_trial_used) VALUES (?, ?, 1)",
            (user_id, expire_str)
        )
    else:
        row = get_user_sub(user_id)
        trial_status = row[1] if row else 0
        cursor.execute(
            "INSERT OR REPLACE INTO subscriptions (user_id, expire_date, is_trial_used) VALUES (?, ?, ?)",
            (user_id, expire_str, trial_status)
        )
    conn.commit()
    conn.close()
    return expire_str

# ---------------------------------------------------------
# 5. KEYBOARD MENUS
# ---------------------------------------------------------
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎁 የ 3 ቀን ነፃ ሙከራ (Free Trial)", callback_data="btn_trial")],
        [InlineKeyboardButton("💳 የክፍያ ፓኬጆች (Packages)", callback_data="btn_packages")],
        [InlineKeyboardButton("ℹ️ ስለ ቦቱ (About)", callback_data="btn_about")],
        [InlineKeyboardButton("📞 ድጋፍ እና እገዛ (Support)", callback_data="btn_info")]
    ]
    return InlineKeyboardMarkup(keyboard)

def package_keyboard():
    keyboard = [
        [InlineKeyboardButton("🥉 Bronze Package (150 ብር / 1 ወር)", callback_data="pkg_bronze")],
        [InlineKeyboardButton("🥈 Silver Package (300 ብር / 3 ወር)", callback_data="pkg_silver")],
        [InlineKeyboardButton("🥇 Gold Package (500 ብር / 6 ወር)", callback_data="pkg_gold")],
        [InlineKeyboardButton("💎 1 ዓመት Package (950 ብር / 12 ወር)", callback_data="pkg_yearly")],
        [InlineKeyboardButton("🔙 ወደ ዋናው ማውጫ", callback_data="btn_main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ---------------------------------------------------------
# 6. HANDLERS (START & BUTTONS)
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    first_name = user.first_name if user.first_name else "ወዳጄ"

    text = (
        f"ሰላም <b>{first_name}</b>! 👋\n\n"
        "🤖 <b>እንኳን ወደ አውቶማቲክ የቴሌግራም የትእዛዝ መቀበያ ቦት በደህና መጡ!</b>\n\n"
        "ይህ ቦት ለቻናልዎ ወይም ለግሩፕዎ አውቶማቲክ 🛒 <b>'Order Now'</b> አዝራር በመጨመር "
        "ከደንበኞችዎ የትእዛዝ መረጃዎችን ሰብስቦ ወደ እርሶ ያደርሳል፡፡\n\n"
        "እባክዎ ከታች ካሉት አማራጮች አንዱን ይምረጡ፦"
    )
    
    if update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
    elif update.callback_query:
        await update.callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "btn_main_menu":
        await start(update, context)

    elif data == "btn_trial":
        row = get_user_sub(user_id)
        if row and row[1] == 1:
            await query.message.edit_text(
                "❌ <b>የነፃ ሙከራ እድልዎን አስቀድመው ተቀምተዋል!</b>\n\n"
                "አገልግሎቱን መቀጠል ከፈለጉ እባክዎ የክፍያ ፓኬጆችን ይምረጡ፦",
                parse_mode="HTML",
                reply_markup=package_keyboard()
            )
        else:
            expire_str = set_user_sub(user_id, days=3, mark_trial=True)
            await query.message.edit_text(
                f"🎉 <b>እንኳን ደስ አለዎት! የ 3 ቀን ነፃ ሙከራዎ ተጀምሯል!</b>\n\n"
                f"📅 <b>አገልግሎቱ የሚያበቃበት ቀን፦</b> <code>{expire_str}</code>\n\n"
                "አሁን ቦቱን በቻናልዎ ወይም በግሩፕዎ ላይ Admin አድርገው በመጨመር መጠቀም መጀመር ይችላሉ! 🚀",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ዋናው ማውጫ", callback_data="btn_main_menu")]])
            )

    elif data == "btn_packages":
        await query.message.edit_text(
            "💳 <b>እባክዎ የሚፈልጉትን የደንበኝነት ፓኬጅ ይምረጡ፦</b>",
            parse_mode="HTML",
            reply_markup=package_keyboard()
        )

    elif data in ["pkg_bronze", "pkg_silver", "pkg_gold", "pkg_yearly"]:
        pkg_names = {
            "pkg_bronze": ("Bronze (1 ወር)", "150 ETB"),
            "pkg_silver": ("Silver (3 ወር)", "300 ETB"),
            "pkg_gold": ("Gold (6 ወር)", "500 ETB"),
            "pkg_yearly": ("1 ዓመት (12 ወር)", "950 ETB")
        }
        selected_pkg, price = pkg_names[data]
        context.user_data['selected_pkg'] = selected_pkg

        payment_text = (
            f"🛒 <b>የተመረጠው ፓኬጅ፦ {selected_pkg}</b>\n"
            f"💰 <b>ክፍያ፦ {price}</b>\n\n"
            f"👤 <b>የአካውንት ስም፦</b> <code>{ACCOUNT_HOLDER}</code>\n\n"
            f"📱 <b>Telebirr:</b> <code>{TELEBIRR_NO}</code>\n"
            f"🏦 <b>Awash Bank:</b> <code>{AWASH_NO}</code>\n"
            f"🏦 <b>Dashen Bank:</b> <code>{DASHEN_NO}</code>\n"
            f"🏦 <b>Bank of Abyssinia:</b> <code>{ABYSSINIA_NO}</code>\n\n"
            "ከላይ በተጠቀሱት አካውንቶች ክፍያውን ፈጽመው <b>የደረሰኙን ስክሪንሾት (Photo/Receipt)</b> እዚህ ይላኩልን፦"
        )
        await query.message.edit_text(payment_text, parse_mode="HTML")
        return PAYMENT_RECEIPT

    elif data == "btn_about":
        about_text = (
            "ℹ️ <b>ስለ ቦቱ መረጃ፦</b>\n\n"
            "ይህ ቦት የንግድ ቻናሎች እና ግሩፖች ምርቶቻቸውን በቀላሉ ለደንበኞች እንዲሸጡ የተሰራ አውቶሜሽን ሲስተም ነው፡፡\n\n"
            "✨ <b>ዋና ዋና ጥቅሞች፦</b>\n"
            "• በቻናልዎ በሚለቀቁ ፎቶዎች ስር የ 'Order Now' አዝራር አውቶማቲክ ይጨምራል።\n"
            "• የደንበኞችን የስም፣ ስልክ እና አድራሻ መረጃ በስርዓት ይሰበስባል።\n"
            "• ትእዛዞችን በቀጥታ ወደ እርሶ የግል ቴሌግራም ይልካል።\n"
            "• የ 24 ሰአት የደንበኞች ድጋፍ አለው።"
        )
        await query.message.edit_text(
            about_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ዋናው ማውጫ", callback_data="btn_main_menu")]])
        )

    elif data == "btn_info":
        info_text = (
            "📞 <b>ድጋፍ እና እገዛ (Support & Info)፦</b>\n\n"
            f"👤 <b>የቦቱ ባለቤት/አድሚን፦</b> {ACCOUNT_HOLDER}\n"
            "💬 <b>ለማንኛውም ጥያቄ ወይም እገዛ፦</b> @Haile_Admin\n"
            f"📞 <b>ስልክ፦</b> {TELEBIRR_NO}\n\n"
            "ማንኛውም አይነት ችግር ካጋጠመዎት በደስታ እንረዳዎታለን!"
        )
        await query.message.edit_text(
            info_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ዋናው ማውጫ", callback_data="btn_main_menu")]])
        )

    elif data.startswith("approve_sub_"):
        parts = data.split("_")
        target_user_id = int(parts[2])
        days = int(parts[3])

        expire_str = set_user_sub(target_user_id, days)

        if query.message.caption:
            await query.edit_message_caption(caption=query.message.caption + f"\n\n🟢 <b>ይህ አባል ለ {days} ቀናት አክቲቭ ሆኗል! (እስከ {expire_str})</b>", parse_mode="HTML")
        else:
            await query.edit_message_text(text=query.message.text + f"\n\n🟢 <b>ይህ አባል ለ {days} ቀናት አክቲቭ ሆኗል! (እስከ {expire_str})</b>", parse_mode="HTML")

        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"🎉 <b>ክፍያዎ ጸድቋል!</b>\n\nአገልግሎቱ ለ {days} ቀናት ተራዝሟል (እስከ {expire_str} ድረስ)። ቦቱን መጠቀም መቀጠል ይችላሉ!",
                parse_mode="HTML"
            )
        except Exception:
            pass

    elif data.startswith("approve_order_"):
        target_user_id = int(data.split("_")[2])
        if query.message.caption:
            await query.edit_message_caption(caption=query.message.caption + "\n\n🟢 <b>ትእዛዙ በአድሚን ጸድቋል!</b>", parse_mode="HTML")
        else:
            await query.edit_message_text(text=query.message.text + "\n\n🟢 <b>ትእዛዙ በአድሚን ጸድቋል!</b>", parse_mode="HTML")

        try:
            await context.bot.send_message(chat_id=target_user_id, text="🎉 <b>ትእዛዝዎ እና ክፍያዎ ጸድቋል!</b> በአጭር ጊዜ ውስጥ እናደርሳለን።", parse_mode="HTML")
        except Exception:
            pass

# ---------------------------------------------------------
# 7. CONVERSATION FLOW (ORDER FORM & RECEIPTS)
# ---------------------------------------------------------
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("📞 <b>ስልክ ቁጥርዎን ያስገቡ፦</b> (ለምሳሌ፦ 09xxxxxxxx)", parse_mode="HTML")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("📍 <b>አድራሻዎን ያስገቡ፦</b> (ከተማ/ክፍለ ከተማ)", parse_mode="HTML")
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text
    await update.message.reply_text("📦 <b>የሚፈልጉትን ብዛት (Quantity) ያስገቡ፦</b>", parse_mode="HTML")
    return QUANTITY

async def get_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['quantity'] = update.message.text
    user = update.effective_user

    summary = (
        "📥 <b>አዲስ የትእዛዝ መረጃ ደርሷል!</b>\n\n"
        f"👤 <b>ስም፦</b> {context.user_data.get('name')}\n"
        f"📞 <b>ስልክ፦</b> {context.user_data.get('phone')}\n"
        f"📍 <b>አድራሻ፦</b> {context.user_data.get('address')}\n"
        f"📦 <b>ብዛት፦</b> {context.user_data.get('quantity')}\n"
        f"🔗 <b>የተጠቃሚ ID:</b> <code>{user.id}</code>\n"
        f"👤 <b>Username:</b> @{user.username if user.username else 'የለውም'}\n"
    )

    await update.message.reply_text(
        "✅ <b>ትእዛዝዎ በትክክል ተመዝግቧል!</b>\n\nአድሚኑ መረጃውን ተመልክቶ በአጭር ጊዜ ውስጥ ያነጋግርዎታል። እናመሰግናለን! 🙏",
        parse_mode="HTML"
    )

    keyboard = [[InlineKeyboardButton("✅ ትእዛዙን አረጋግጥ (Approve)", callback_data=f"approve_order_{user.id}")]]
    try:
        await context.bot.send_message(chat_id=ADMIN_USER_ID, text=summary, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logging.error(f"Failed to send order to admin: {e}")

    return ConversationHandler.END

async def get_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo_file_id = update.message.photo[-1].file_id if update.message.photo else None
    pkg = context.user_data.get('selected_pkg', 'ያልተጠቀሰ')

    summary = (
        "📥 <b>አዲስ የክፍያ ደረሰኝ ደርሷል!</b>\n\n"
        f"📦 <b>የተመረጠው ፓኬጅ፦</b> {pkg}\n"
        f"👤 <b>የላኪው ስም፦</b> {user.full_name}\n"
        f"🔗 <b>የተጠቃሚ ID:</b> <code>{user.id}</code>\n"
        f"👤 <b>Username:</b> @{user.username if user.username else 'የለውም'}\n"
    )

    await update.message.reply_text(
        "✅ <b>የክፍያ ደረሰኝዎ ደርሶናል!</b>\n\nአድሚኑ ክፍያውን አረጋግቶ አካውንትዎን አክቲቭ ያደርግልዎታል። እናመሰግናለን! 🙏",
        parse_mode="HTML"
    )

    keyboard = [
        [InlineKeyboardButton("✅ 30 ቀን አክቲቭ አድርግ (Bronze)", callback_data=f"approve_sub_{user.id}_30")],
        [InlineKeyboardButton("✅ 90 ቀን አክቲቭ አድርግ (Silver)", callback_data=f"approve_sub_{user.id}_90")],
        [InlineKeyboardButton("✅ 180 ቀን አክቲቭ አድርግ (Gold)", callback_data=f"approve_sub_{user.id}_180")],
        [InlineKeyboardButton("✅ 365 ቀን አክቲቭ አድርግ (1 ዓመት)", callback_data=f"approve_sub_{user.id}_365")]
    ]

    try:
        if photo_file_id:
            await context.bot.send_photo(chat_id=ADMIN_USER_ID, photo=photo_file_id, caption=summary, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await context.bot.send_message(chat_id=ADMIN_USER_ID, text=summary + f"\n🧾 <b>ማስታወሻ፦</b> {update.message.text}", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logging.error(f"Failed to send receipt to admin: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ትእዛዙ ተሰርዟል። እንደገና ለመጀመር /start በሉ።")
    return ConversationHandler.END

# ---------------------------------------------------------
# 8. AUTOMATIC CHANNEL/GROUP POST BUTTON ATTACHER
# ---------------------------------------------------------
async def handle_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id if update.effective_user else None
    if not sender_id:
        return

    active, expire_date = is_user_active(sender_id)

    if active:
        keyboard = [[InlineKeyboardButton("🛒 Order Now / አሁኑኑ ይዘዙ", url=f"https://t.me/{context.bot.username}?start=order")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            if update.channel_post:
                await context.bot.edit_message_reply_markup(
                    chat_id=update.channel_post.chat_id,
                    message_id=update.channel_post.message_id,
                    reply_markup=reply_markup
                )
            elif update.message and (update.message.chat.type in ['group', 'supergroup']):
                await update.message.reply_text("🛒 <b>ይህን ምርት ለማዘዝ ከታች ያለውን አዝራር ይጫኑ፦</b>", parse_mode="HTML", reply_markup=reply_markup)
        except Exception as e:
            logging.error(f"Failed to attach order button: {e}")
    else:
        try:
            await context.bot.send_message(
                chat_id=sender_id,
                text=(
                    "⚠️ <b>የአገልግሎት ጊዜዎ ወይም የ 3 ቀን ነፃ ሙከራዎ አብቅቷል!</b>\n\n"
                    "በቻናልዎ/ግሩፕዎ ላይ የ 'Order Now' አዝራር መጨመር ለመቀጠል እባክዎ የክፍያ ፓኬጅ ይምረጡ፦"
                ),
                parse_mode="HTML",
                reply_markup=package_keyboard()
            )
        except Exception:
            pass

# ---------------------------------------------------------
# 9. ADMIN COMMANDS
# ---------------------------------------------------------
async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    try:
        target_user_id = int(context.args[0])
        days = int(context.args[1])
        
        expire_str = set_user_sub(target_user_id, days)

        await update.message.reply_text(f"✅ ተጠቃሚ <code>{target_user_id}</code> ለ {days} ቀናት አክቲቭ ሆኗል! (እስከ {expire_str})", parse_mode="HTML")
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"🎉 <b>ክፍያዎ ጸድቋል!</b>\n\nአገልግሎቱ ለ {days} ቀናት ተራዝሟል (እስከ {expire_str} ድረስ)። ቦቱን መጠቀም መቀጠል ይችላሉ!",
            parse_mode="HTML"
        )
    except Exception:
        await update.message.reply_text("❌ ስህተት፦ <code>/approve USER_ID DAYS</code> ብለው ያስገቡ።", parse_mode="HTML")

# ---------------------------------------------------------
# 10. MAIN FUNCTION
# ---------------------------------------------------------
def main():
    keep_alive()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .get_updates_connect_timeout(30.0)
        .get_updates_read_timeout(30.0)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(button_handler)
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quantity)],
            PAYMENT_RECEIPT: [MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, get_receipt)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("approve", approve_user))
    
    # Handle channel/group posts automatically
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_posts))

    application.run_polling(drop_pending_updates=True, bootstrap_retries=-1)

if __name__ == "__main__":
    main()
