import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Admin Telegram ID from notes
ADMIN_ID = 8607635094
# Replace with your actual Web App URL from Render/Vercel
WEB_APP_URL = "https://your-bingo-app.onrender.com"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('bingo_bot.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            balance REAL DEFAULT 0.0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            status TEXT,
            receipt_info TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user_balance(user_id):
    conn = sqlite3.connect('bingo_bot.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0.0

def update_user_balance(user_id, amount):
    conn = sqlite3.connect('bingo_bot.db')
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect('bingo_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, balance) VALUES (?, ?, ?, 0.0)",
              (user.id, user.username or "", user.full_name))
    conn.commit()
    conn.close()

    welcome_text = (
        f"ሰላም {user.full_name}! እንኳን ወደ Sambingo Bot በደህና መጡ።\n\n"
        f"ያልዎት ባላንስ: {get_user_balance(user.id)} Birr\n"
        "እባክዎን ከታች ካሉት አማራጮች አንዱን ይምረጡ፡"
    )

    keyboard = [
        [InlineKeyboardButton("🎮 Play 10 birr", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit"),
         InlineKeyboardButton("🏧 Withdraw", callback_data="withdraw")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "deposit":
        msg = (
            "📥 **Deposit ለማድረግ፡**\n\n"
            "1. በ **0908676709** (CBE / Telebirr) ብሩን ያስገቡ።\n"
            "2. የላኩበትን ደረሰኝ/ጽሁፍ (Copy አድርገው) ወይም Screenshot ለዚሁ ቦት ይላኩ።"
        )
        await query.message.reply_text(msg, parse_mode="Markdown")

    elif query.data == "withdraw":
        context.user_data['state'] = 'awaiting_withdraw_info'
        await query.message.reply_text(
            "🏧 **Withdraw ለማድረግ፡**\n"
            "እባክዎን ሙሉ ስምዎን እና ስልክ ቁጥርዎን ይላኩ፡"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state = context.user_data.get('state')

    if state == 'awaiting_withdraw_info':
        info = update.message.text
        context.user_data['withdraw_info'] = info
        context.user_data['state'] = 'awaiting_withdraw_amount'
        await update.message.reply_text("እባክዎን ማውጣት የሚፈልጉትን የብር መጠን ያስገቡ፡")

    elif state == 'awaiting_withdraw_amount':
        try:
            amount = float(update.message.text)
            curr_bal = get_user_balance(user.id)
            if amount > curr_bal:
                await update.message.reply_text("❌ በቂ ባላንስ የለዎትም። እባክዎን በድጋሚ ይሞክሩ።")
                context.user_data['state'] = None
                return

            info = context.user_data.get('withdraw_info', '')
            context.user_data['state'] = None
            await update.message.reply_text("ያቀረቡት የ Withdraw ጥያቄ ለአድሚን ተልኳል። በጥቂት ደቂቃዎች ውስጥ ይረጋገጣል።")

            # Send to Admin
            admin_btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"app_w_{user.id}_{amount}"),
                 InlineKeyboardButton("❌ Reject", callback_data=f"rej_w_{user.id}_{amount}")]
            ])
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🚨 **የ Withdraw ጥያቄ**\nተጠቃሚ: {user.full_name} (@{user.username})\nID: {user.id}\nመረጃ: {info}\nየተጠየቀው ብር: {amount} Birr",
                reply_markup=admin_btn,
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text("እባክዎን ትክክለኛ የብር ቁጥር ያስገቡ።")

    else:
        # Assume screenshot or deposit text receipt
        await update.message.reply_text("ደረሰኝዎ በመመርመር ላይ ነው። እባክዎን ትንሽ ይጠብቁ...")

        # Forward receipt to admin
        admin_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"app_d_{user.id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"rej_d_{user.id}")]
        ])
        
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"📩 **አዲስ የ Deposit ደረሰኝ ከ {user.full_name} (@{user.username}) [ID: {user.id}]**")
        await update.message.forward(chat_id=ADMIN_ID)
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"የ Deposit ብር መጠን ስንት ይሁን? (ጸድቅ ከተጫነ በኋላ የሚጨመር መጠን):",
            reply_markup=admin_btn
        )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("app_d_"):
        user_id = int(data.split("_")[2])
        context.user_data[f"dep_user_{ADMIN_ID}"] = user_id
        await query.message.reply_text(f"እባክዎን ለተጠቃሚ {user_id} የሚጨመረውን የብር መጠን በቁጥር ያስገቡ (ምሳሌ: 100):")

    elif data.startswith("rej_d_"):
        user_id = int(data.split("_")[2])
        await context.bot.send_message(chat_id=user_id, text="❌ የ Deposit ደረሰኝዎ ውድቅ ተደርጓል።")
        await query.edit_message_text("❌ Deposit ውድቅ ተደርጓል።")

    elif data.startswith("app_w_"):
        parts = data.split("_")
        user_id = int(parts[2])
        amount = float(parts[3])
        update_user_balance(user_id, -amount)
        await context.bot.send_message(chat_id=user_id, text=f"✅ የ {amount} Birr Withdraw ጥያቄዎ ጸድቋል! ገንዘቡ ተልኳል።")
        await query.edit_message_text("✅ Withdraw ጸድቋል።")

    elif data.startswith("rej_w_"):
        parts = data.split("_")
        user_id = int(parts[2])
        await context.bot.send_message(chat_id=user_id, text="❌ የ Withdraw ጥያቄዎ ውድቅ ተደርጓል።")
        await query.edit_message_text("❌ Withdraw ውድቅ ተደርጓል።")

def main():
    # Insert Telegram Bot Token here
    TOKEN = "8843682933:AAFm81z7Z5sd-5PSSYEgRDtMRvMJu9n7Oxw"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click, pattern="^(deposit|withdraw)$"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(app_d_|rej_d_|app_w_|rej_w_)"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
