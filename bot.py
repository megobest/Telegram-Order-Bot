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
# 1. FLASK DUMMY SERVER (ለ Render Web Service Port Requirement)
# ---------------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

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
# 3. GLOBAL VARIABLES & CONSTANTS
# ---------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8770076033:AAGNZ-Obug4bN_Yb_MzPJzy2-La6fb_W7lg")
ADMIN_USER_ID = 5997262731  # የሃይሌ Admin User ID

TELEBIRR_NO = "09xxxxxxxx"
CBE_BANK_NO = "1000xxxxxxxx"

NAME, PHONE, ADDRESS, QUANTITY, PAYMENT_RECEIPT = range(5)

# ---------------------------------------------------------
# 4. DATABASE SETUP & HELPER FUNCTIONS
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

def is_user_active(user_id):
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT expire_date FROM subscriptions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row and row[0]:
        expire_date = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        if datetime.now() < expire_date:
            return True, expire_date
    return False, None

def check_and_apply_trial(user_id):
    conn = sqlite3.connect("bot_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_trial_used FROM subscriptions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row or row[0] == 0:
        # የ 1 ቀን ነፃ Free Trial መስጠት
        expire_date = datetime.now() + timedelta(days=1)
        expire_str = expire_date.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT OR REPLACE INTO subscriptions (user_id, expire_date, is_trial_used) VALUES (?, ?, 1)",
            (user_id, expire_str)
        )
        conn.commit()
        conn.close()
        return True, expire_str
    
    conn.close()
    return False, None

# ---------------------------------------------------------
# 5. HANDLER FUNCTIONS (Conversation, Trial & Orders)
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # ነፃ ፍሪ ትራያል ማረጋገጥ
    trial_given, expire_str = check_and_apply_trial(user_id)
    
    trial_msg = ""
    if trial_given:
        trial_msg = f"🎁 <b>የ 1 ቀን ነፃ Free Trial ተሰጥቶዎታል!</b> (እስከ {expire_str} ድረስ አክቲቭ ነው)\n\n"
    
    await update.message.reply_text(
        f"{trial_msg}👋 <b>እንኳን ወደ ትእዛዝ መቀበያ ቦት በደህና መጡ!</b>\n\nእባክዎ ሙሉ <b>ስምዎን</b> ያስገቡ፦",
        parse_mode="HTML"
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("📞 <b>ስልክ ቁጥርዎን</b> ያስገቡ፦ (ለምሳሌ፦ 09xxxxxxxx)", parse_mode="HTML")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("📍 <b>አድራሻዎን</b> ያስገቡ፦ (ከተማ/ክፍለ ከተማ/ቀበሌ)", parse_mode="HTML")
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text
    await update.message.reply_text("📦 የሚፈልጉትን <b>ብዛት (Quantity)</b> ያስገቡ፦", parse_mode="HTML")
    return QUANTITY

async def get_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['quantity'] = update.message.text

    payment_text = (
        "💳 <b>የክፍያ መረጃ፦</b>\n\n"
        f"📱 <b>Telebirr:</b> <code>{TELEBIRR_NO}</code>\n"
        f"🏦 <b>CBE Bank:</b> <code>{CBE_BANK_NO}</code>\n\n"
        "እባክዎ ክፍያውን ፈጽመው <b>የደረሰኙን ስክሪንሾት (Photo/Receipt)</b> እዚህ ይላኩልን፦"
    )
    
    await update.message.reply_text(payment_text, parse_mode="HTML")
    return PAYMENT_RECEIPT

async def get_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo_file_id = update.message.photo[-1].file_id if update.message.photo else None

    summary = (
        "📥 <b>አዲስ ትእዛዝ እና የክፍያ ደረሰኝ ደርሷል!</b>\n\n"
        f"👤 <b>ስም፦</b> {context.user_data.get('name')}\n"
        f"📞 <b>ስልክ፦</b> {context.user_data.get('phone')}\n"
        f"📍 <b>አድራሻ፦</b> {context.user_data.get('address')}\n"
        f"📦 <b>ብዛት፦</b> {context.user_data.get('quantity')}\n"
        f"🔗 <b>የተጠቃሚ ID:</b> <code>{user.id}</code>\n"
        f"👤 <b>Username:</b> @{user.username if user.username else 'የለውም'}\n"
    )

    await update.message.reply_text(
        "✅ <b>ትእዛዝዎ እና የክፍያ ደረሰኝዎ በትክክል ደርሶናል!</b>\n\nአድሚኑ መረጃውን አረጋግጦ በአጭር ጊዜ ውስጥ ያነጋግርዎታል። እናመሰግናለን! 🙏",
        parse_mode="HTML"
    )

    keyboard = [
        [InlineKeyboardButton("✅ ትእዛዙን አረጋግጥ (Approve)", callback_data=f"approve_order_{user.id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if photo_file_id:
            await context.bot.send_photo(
                chat_id=ADMIN_USER_ID,
                photo=photo_file_id,
                caption=summary,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=summary + f"\n🧾 <b>የደረሰኝ ጽሁፍ፦</b> {update.message.text}",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
    except Exception as e:
        logging.error(f"ለአድሚን መረጃ መላክ አልተቻለም: {e}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ትእዛዙ ተሰርዟል። እንደገና ለመጀመር /start በሉ።")
    return ConversationHandler.END

# ---------------------------------------------------------
# 6. POSTS / CHANNEL HANDLER (ለቻናል እና ግሩፕ መልእክቶች)
# ---------------------------------------------------------
async def handle_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return

    active, expire_date = is_user_active(user_id)
    if not active:
        # አክቲቭ ካልሆነ/ጊዜው ካለቀ መልእክቱን ይከለክላል ወይም ማስጠንቀቂያ ይልካል
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠️ <b>የአገልግሎት ጊዜዎ አልቋል!</b>\n\nቦቱን በቻናልዎ/ግሩፕዎ መጠቀም ለመቀጠል እባክዎ ክፍያ ፈጽመው አገልግሎቱን ያድሱ።",
                parse_mode="HTML"
            )
        except Exception:
            pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("approve_order_"):
        target_user_id = int(query.data.split("_")[2])
        
        # ለአድሚኑ ማረጋገጫ መስጠት
        if query.message.caption:
            await query.edit_message_caption(
                caption=query.message.caption + "\n\n🟢 <b>ይህ ትእዛዝ በአድሚን ጸድቋል!</b>",
                parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                text=query.message.text + "\n\n🟢 <b>ይህ ትእዛዝ በአድሚን ጸድቋል!</b>",
                parse_mode="HTML"
            )

        # ለደንበኛው ማሳወቂያ መላክ
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text="🎉 <b>ክፍያዎ እና ትእዛዝዎ ጸድቋል!</b> በአጭር ጊዜ ውስጥ እናደርሳለን።",
                parse_mode="HTML"
            )
        except Exception:
            pass

async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    try:
        target_user_id = int(context.args[0])
        days = int(context.args[1])
        
        expire_date = datetime.now() + timedelta(days=days)
        expire_str = expire_date.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect("bot_users.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO subscriptions (user_id, expire_date, is_trial_used) VALUES (?, ?, 1)",
            (target_user_id, expire_str)
        )
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ ተጠቃሚ <code>{target_user_id}</code> ለ {days} ቀናት አክቲቭ ሆኗል!", parse_mode="HTML")
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"🎉 <b>ክፍያዎ ጸድቋል!</b>\n\nአገልግሎቱ ለ {days} ቀናት ተራዝሟል (እስከ {expire_str} ድረስ)።",
            parse_mode="HTML"
        )
    except Exception:
        await update.message.reply_text("❌ ስህተት፦ <code>/approve USER_ID DAYS</code> ብለው ያስገቡ።", parse_mode="HTML")

# ---------------------------------------------------------
# 7. ERROR HANDLER
# ---------------------------------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Error caught safely: {context.error}")

# ---------------------------------------------------------
# 8. MAIN FUNCTION
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
        entry_points=[CommandHandler("start", start)],
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
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("approve", approve_user))
    
    # የቻናል/ግሩፕ ልጥፎች መከታተያ Handler
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_posts))

    application.add_error_handler(error_handler)

    print("🤖 ቦቱ ስራ ጀምሯል...")
    application.run_polling(drop_pending_updates=True, bootstrap_retries=-1)

if __name__ == "__main__":
    main()
