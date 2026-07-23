import logging
import os
import sqlite3
from datetime import datetime, timedelta
from threading import Thread

from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Update
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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "123456789"))  # ያንተን Admin ID አድርገው

NAME, PHONE, ADDRESS, QUANTITY = range(4)

# ---------------------------------------------------------
# 4. HANDLER FUNCTIONS (የቦቱ ተግባራት)
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 እንኳን ወደ ትእዛዝ መቀበያ ቦት በደህና መጡ!\nእባክዎ ስምዎን ያስገቡ፦")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("ስልክ ቁጥርዎን ያስገቡ፦")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("አድራሻዎን ያስገቡ፦")
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text
    await update.message.reply_text("የሚፈልጉትን መጠን (ብዛት) ያስገቡ፦")
    return QUANTITY

async def get_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['quantity'] = update.message.text
    
    summary = (
        "📋 <b>የትእዛዝዎ ማጠቃለያ፦</b>\n\n"
        f"<b>ስም፦</b> {context.user_data['name']}\n"
        f"<b>ስልክ፦</b> {context.user_data['phone']}\n"
        f"<b>አድራሻ፦</b> {context.user_data['address']}\n"
        f"<b>ብዛት፦</b> {context.user_data['quantity']}\n\n"
        "እናመሰግናለን! ትእዛዝዎ በትክክል ተቀብለናል።"
    )
    await update.message.reply_text(summary, parse_mode="HTML")
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

async def handle_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            text=f"🎉 <b>ክፍያዎ ጸድቋል!</b>\n\nአገልግሎቱ ለ {days} ቀናት ተራዝሟል። ቦቱን በቻናልዎ/ግሩፕዎ ላይ መጠቀም ይችላሉ!",
            parse_mode="HTML"
        )
    except Exception:
        await update.message.reply_text("❌ ስህተት፦ <code>/approve USER_ID DAYS</code> ብለው ያስገቡ።", parse_mode="HTML")

# ---------------------------------------------------------
# 5. ERROR HANDLER
# ---------------------------------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Network / Network Error caught safely: {context.error}")

# ---------------------------------------------------------
# 6. MAIN FUNCTION
# ---------------------------------------------------------
def main():
    # 🟢 Render 24/7 PORT እንዲያገኝ Flask Server እናስነሳለን
    keep_alive()

    # Timeout የጊዜ ገደቦቹን ከፍ በማድረግ የProxy መዘግየትን የመቋቋም አቅም እንጨምራለን
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
        },
        fallbacks=[],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("approve", approve_user))

    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND, 
        handle_posts
    ))

    # Error Handler ማያያዝ
    application.add_error_handler(error_handler)

    print("🤖 ቦቱ ስራ ጀምሯል...")
    # Network ኤረር ሲያጋጥመው አውቶማቲክ ድጋሚ እንዲሞክር (bootstrap_retries=-1)
    application.run_polling(drop_pending_updates=True, bootstrap_retries=-1)

if __name__ == "__main__":
    main()
