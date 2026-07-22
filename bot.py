import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------
# 1. መረጃዎችህ እና መቼቶች
# ---------------------------------------------------------
BOT_TOKEN = "8770076033:AAGNZ-Obug4bN_Yb_MzPJzy2-La6fb_W7lg"
BOT_USERNAME = "SaaS_Order_Manager_bot"

# ያንተ Order Hub Group ID እና Admin Telegram ID
ADMIN_CHAT_ID = -1004366552032  
ADMIN_USER_ID = 5997262731

# የውይይት ደረጃዎች
NAME, PHONE, ADDRESS, QUANTITY = range(4)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

# ---------------------------------------------------------
# 2. Database ማዘጋጃ (SQLite)
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

# ---------------------------------------------------------
# 3. የ /start እና የሜኑ Handlers
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user = update.effective_user

    if args and args[0].startswith("order_"):
        raw_info = args[0].replace("order_", "")
        parts = raw_info.split("_")
        chat_id_clean = parts[0]
        msg_id_clean = parts[1] if len(parts) > 1 else ""

        context.user_data['chat_id_clean'] = chat_id_clean
        context.user_data['msg_id_clean'] = msg_id_clean
        
        await update.message.reply_text(
            "🛍️ <b>እንኳን ወደ ማዘዣው ገጽ በደህና መጡ!</b>\n\n"
            "ትዕዛዝዎን ለማጠናቀቅ እባክዎ <b>ሙሉ ስምዎን</b> ያስገቡ፦",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
        return NAME

    keyboard = [
        [InlineKeyboardButton("🎁 የ 3 ቀን ነፃ ሙከራ (Free Trial)", callback_data="free_trial")],
        [InlineKeyboardButton("💳 የክፍያ ፓኬጆች (Packages)", callback_data="packages")],
        [InlineKeyboardButton("ℹ️ ስለ ቦቱ (About)", callback_data="about")],
        [InlineKeyboardButton("📞 ድጋፍ እና አከፋፈል (Info)", callback_data="payment_info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"ሰላም {user.first_name}! 👋\n\n"
        "🤖 <b>እንኳን ወደ አውቶማቲክ የቴሌግራም የትዕዛዝ መቀበያ ቦት በደህና መጡ!</b>\n\n"
        "ይህ ቦት ለቻናልዎ ወይም ለግሩፕዎ አውቶማቲክ <b>'🛒 Order Now'</b> በተን በመጨመር "
        "ከደንበኞችዎ የትዕዛዝ መረጃዎችን ሰብስቦ ወደ እርስዎ ያደርሳል።\n\n"
        "እባክዎ ከታች ካሉት አማራጮች አንዱን ይምረጡ፦",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    return ConversationHandler.END

# ---------------------------------------------------------
# 4. የCallback Buttons አስተናጋጅ
# ---------------------------------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "free_trial":
        conn = sqlite3.connect("bot_users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT is_trial_used FROM subscriptions WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row and row[0] == 1:
            await query.edit_message_text(
                "⚠️ <b>የነፃ ሙከራ እድልዎን ተጠቅመዋል!</b>\n\n"
                "አገልግሎቱን መቀጠል ለመቀጠል እባክዎ የክፍያ ፓኬጆችን ይመልከቱ።",
                parse_mode="HTML"
            )
        else:
            expire_date = datetime.now() + timedelta(days=3)
            expire_str = expire_date.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT OR REPLACE INTO subscriptions (user_id, expire_date, is_trial_used) VALUES (?, ?, 1)",
                (user_id, expire_str)
            )
            conn.commit()
            await query.edit_message_text(
                "🎉 <b>እንኳን ደስ አለዎት!</b>\n\n"
                "የ 3 ቀን ነፃ የሙከራ ጊዜዎ ተጀምሯል! አሁኑኑ ቦቱን በቻናልዎ ወይም በግሩፕዎ ላይ <b>Admin</b> አድርገው በመጨመር መጠቀም መጀመር ይችላሉ።",
                parse_mode="HTML"
            )
        conn.close()

    elif query.data == "packages":
        text = (
            "💳 <b>የክፍያ ፓኬጆች (Subscription Packages)</b>\n\n"
            "🥉 <b>Bronze:</b> 150 ብር (ለ 1 ወር)\n"
            "🥈 <b>Silver:</b> 300 ብር (ለ 3 ወር)\n"
            "🥇 <b>Gold:</b> 500 ብር (ለ 6 ወር)\n"
            "💎 <b>VIP (Yearly):</b> 900 ብር (ለ 1 ዓመት / 12 ወር) 🔥 <i>ትልቅ ቅናሽ</i>\n\n"
            "ለክፍያ መረጃ <b>'📞 ድጋፍ እና አከፋፈል'</b> የሚለውን በተን ይጫኑ።"
        )
        await query.edit_message_text(text, parse_mode="HTML")

    elif query.data == "about":
        text = (
            "ℹ️ <b>ስለ ቦቱ አሰራር፦</b>\n\n"
            "1. ቦቱን በቻናልዎ ወይም በግሩፕዎ ላይ <b>Admin</b> አድርገው ይጨምሩት።\n"
            "2. ፖስት በሚደረግበት ጊዜ ቦቱ አውቶማቲክ <b>'🛒 አሁኑኑ ይዘዙ (Order)'</b> የሚል በተን ይጨምራል።\n"
            "3. ደንበኛው በተኑን ሲነካ ቦቱ ስም፣ ስልክ፣ አድራሻ እና ብዛት ተቀብሎ ቀጥታ ወደ Order Hub ያደርሳል!"
        )
        await query.edit_message_text(text, parse_mode="HTML")

    elif query.data == "payment_info":
        text = (
            "👤 <b>የአካውንት ባለቤት:</b> Hailemichael Mebrate\n\n"
            "🏦 <b>የባንክ አካውንቶች፦</b>\n"
            "• <b>Telebirr:</b> <code>0979484319</code>\n"
            "• <b>Awash Bank:</b> <code>013201354775100</code>\n"
            "• <b>Dashen Bank:</b> <code>5121945801011</code>\n"
            "• <b>Abyssinia Bank:</b> <code>226261346</code>\n\n"
            "📌 <b>ማሳሰቢያ፦</b> ክፍያ ፈፅመው ሲጨርሱ የደረሰኝ ፎቶ (Receipt Screenshot) ወደዚሁ ቦት ይላኩ።"
        )
        await query.edit_message_text(text, parse_mode="HTML")

# ---------------------------------------------------------
# 5. የትዕዛዝ መረጃዎች መቀበያ (Order Form)
# ---------------------------------------------------------
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("ጥሩ! አሁን ደግሞ <b>የስልክ ቁጥርዎን</b> ያስገቡ፦", parse_mode="HTML")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("አመሰግናለሁ! አሁን <b>የሚኖሩበትን አድራሻ (ከተማ/ክፍለ ከተማ)</b> ያስገቡ፦", parse_mode="HTML")
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text
    await update.message.reply_text("በጣም ጥሩ! በመጨረሻም <b>ስንት ብዛት</b> ማዘዝ ይፈልጋሉ?፦", parse_mode="HTML")
    return QUANTITY

async def get_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['quantity'] = update.message.text
    user = update.effective_user
    
    name = context.user_data.get('name', 'ያልተገለጸ')
    phone = context.user_data.get('phone', 'ያልተገለጸ')
    address = context.user_data.get('address', 'ያልተገለጸ')
    quantity = context.user_data.get('quantity', 'ያልተገለጸ')
    chat_id_clean = context.user_data.get('chat_id_clean', '')

    channel_info_text = f"ID: -{chat_id_clean}"
    try:
        chat_obj = await context.bot.get_chat(int(f"-{chat_id_clean}"))
        c_title = chat_obj.title
        c_user = f"@{chat_obj.username}" if chat_obj.username else "Private"
        channel_info_text = f"<b>{c_title}</b> ({c_user}) | ID: <code>-{chat_id_clean}</code>"
    except Exception as e:
        logging.error(f"Error getting chat details: {e}")

    await update.message.reply_text("✅ <b>ትዕዛዝዎ በስኬት ተልኳል!</b>\nበቅርቡ እናነጋግርዎታለን።", parse_mode="HTML")

    admin_message = (
        "🚨 <b>አዲስ ትዕዛዝ ደርሷል!</b> 🚨\n\n"
        f"👤 <b>የደንበኛ ስም:</b> {name}\n"
        f"📞 <b>ስልክ:</b> <code>{phone}</code>\n"
        f"📍 <b>አድራሻ:</b> {address}\n"
        f"🔢 <b>ብዛት:</b> {quantity}\n\n"
        f"📢 <b>የመጣበት ቻናል/Group:</b> {channel_info_text}\n"
        f"💬 <b>የደንበኛው Telegram:</b> @{user.username if user.username else 'የለውም'} (ID: <code>{user.id}</code>)"
    )

    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error sending order: {e}")

    return ConversationHandler.END

# ---------------------------------------------------------
# 6. በ ቻናል እና በ Group ፖስቶች ላይ አውቶማቲክ በተን መጨመሪያ
# ---------------------------------------------------------
async def handle_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post or update.message
    if not message:
        return

    chat = message.chat

    inline_keyboard = [[
        InlineKeyboardButton(
            "🛒 አሁኑኑ ይዘዙ (Order)", 
            url=f"https://t.me/{BOT_USERNAME}?start=order_{abs(chat.id)}_{message.message_id}"
        )
    ]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard)

    # 1. ከ Channel የመጣ ፖስት ከሆነ
    if update.channel_post:
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=chat.id,
                message_id=message.message_id,
                reply_markup=reply_markup
            )
        except Exception as e:
            try:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="👇 <b>ትዕዛዝ ለመስጠት ከታች ያለውን በተን ይጫኑ፦</b>",
                    reply_to_message_id=message.message_id,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            except Exception as inner_e:
                logging.error(f"Channel fallback error: {inner_e}")

    # 2. ከ Group የመጣ መልእክት ከሆነ
    elif update.message and chat.type in ['group', 'supergroup']:
        if message.from_user and message.from_user.id == context.bot.id:
            return
        try:
            await context.bot.send_message(
                chat_id=chat.id,
                text="👇 <b>ትዕዛዝ ለመስጠት ከታች ያለውን በተን ይጫኑ፦</b>",
                reply_to_message_id=message.message_id,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Group button error: {e}")

# ---------------------------------------------------------
# 7. አድሚን ክፍያ ሲያጸድቅ (Approval Command)
# ---------------------------------------------------------
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
# 8. Network Error ኤረር ማቀቢያ Handler (ከCrash ለመከላከል)
# ---------------------------------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Network / Network Error caught safely: {context.error}")

# ---------------------------------------------------------
# 9. Main Function (በታመነ Timeout እና Retry አደረጃጀት)
# ---------------------------------------------------------
def main():
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