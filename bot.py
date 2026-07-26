import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Admin Telegram ID from notes
ADMIN_ID = 8607635094
# Replace with your actual Web App URL from Render/Vercel
WEB_APP_URL = "https://bingo-bot-dyex.onrender.com"

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
        f"áˆ°áˆ‹áˆ {user.full_name}! áŠ¥áŠ•áŠ³áŠ• á‹ˆá‹° Sambingo Bot á‰ á‹°áˆ…áŠ“ áˆ˜áŒ¡á¢\n\n"
        f"á‹«áˆá‹Žá‰µ á‰£áˆ‹áŠ•áˆµ: {get_user_balance(user.id)} Birr\n"
        "áŠ¥á‰£áŠ­á‹ŽáŠ• áŠ¨á‰³á‰½ áŠ«áˆ‰á‰µ áŠ áˆ›áˆ«áŒ®á‰½ áŠ áŠ•á‹±áŠ• á‹­áˆáˆ¨áŒ¡á¡"
    )

    keyboard = [
        [InlineKeyboardButton("ðŸŽ® Play 10 birr", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("ðŸ’³ Deposit", callback_data="deposit"),
         InlineKeyboardButton("ðŸ§ Withdraw", callback_data="withdraw")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "deposit":
        msg = (
            "ðŸ“¥ **Deposit áˆˆáˆ›á‹µáˆ¨áŒá¡**\n\n"
            "1. á‰  **0908676709** (CBE / Telebirr) á‰¥áˆ©áŠ• á‹«áˆµáŒˆá‰¡á¢\n"
            "2. á‹¨áˆ‹áŠ©á‰ á‰µáŠ• á‹°áˆ¨áˆ°áŠ/áŒ½áˆá (Copy áŠ á‹µáˆ­áŒˆá‹) á‹ˆá‹­áˆ Screenshot áˆˆá‹šáˆ á‰¦á‰µ á‹­áˆ‹áŠ©á¢"
        )
        await query.message.reply_text(msg, parse_mode="Markdown")

    elif query.data == "withdraw":
        context.user_data['state'] = 'awaiting_withdraw_info'
        await query.message.reply_text(
            "ðŸ§ **Withdraw áˆˆáˆ›á‹µáˆ¨áŒá¡**\n"
            "áŠ¥á‰£áŠ­á‹ŽáŠ• áˆ™áˆ‰ áˆµáˆá‹ŽáŠ• áŠ¥áŠ“ áˆµáˆáŠ­ á‰áŒ¥áˆ­á‹ŽáŠ• á‹­áˆ‹áŠ©á¡"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state = context.user_data.get('state')

    if state == 'awaiting_withdraw_info':
        info = update.message.text
        context.user_data['withdraw_info'] = info
        context.user_data['state'] = 'awaiting_withdraw_amount'
        await update.message.reply_text("áŠ¥á‰£áŠ­á‹ŽáŠ• áˆ›á‹áŒ£á‰µ á‹¨áˆšáˆáˆáŒ‰á‰µáŠ• á‹¨á‰¥áˆ­ áˆ˜áŒ áŠ• á‹«áˆµáŒˆá‰¡á¡")

    elif state == 'awaiting_withdraw_amount':
        try:
            amount = float(update.message.text)
            curr_bal = get_user_balance(user.id)
            if amount > curr_bal:
                await update.message.reply_text("âŒ á‰ á‰‚ á‰£áˆ‹áŠ•áˆµ á‹¨áˆˆá‹Žá‰µáˆá¢ áŠ¥á‰£áŠ­á‹ŽáŠ• á‰ á‹µáŒ‹áˆš á‹­áˆžáŠ­áˆ©á¢")
                context.user_data['state'] = None
                return

            info = context.user_data.get('withdraw_info', '')
            context.user_data['state'] = None
            await update.message.reply_text("á‹«á‰€áˆ¨á‰¡á‰µ á‹¨ Withdraw áŒ¥á‹«á‰„ áˆˆáŠ á‹µáˆšáŠ• á‰°áˆáŠ³áˆá¢ á‰ áŒ¥á‰‚á‰µ á‹°á‰‚á‰ƒá‹Žá‰½ á‹áˆµáŒ¥ á‹­áˆ¨áŒ‹áŒˆáŒ£áˆá¢")

            # Send to Admin
            admin_btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("âœ… Approve", callback_data=f"app_w_{user.id}_{amount}"),
                 InlineKeyboardButton("âŒ Reject", callback_data=f"rej_w_{user.id}_{amount}")]
            ])
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"ðŸš¨ **á‹¨ Withdraw áŒ¥á‹«á‰„**\ná‰°áŒ á‰ƒáˆš: {user.full_name} (@{user.username})\nID: {user.id}\náˆ˜áˆ¨áŒƒ: {info}\ná‹¨á‰°áŒ á‹¨á‰€á‹ á‰¥áˆ­: {amount} Birr",
                reply_markup=admin_btn,
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text("áŠ¥á‰£áŠ­á‹ŽáŠ• á‰µáŠ­áŠ­áˆˆáŠ› á‹¨á‰¥áˆ­ á‰áŒ¥áˆ­ á‹«áˆµáŒˆá‰¡á¢")

    else:
        # Assume screenshot or deposit text receipt
        await update.message.reply_text("á‹°áˆ¨áˆ°áŠá‹Ž á‰ áˆ˜áˆ˜áˆ­áˆ˜áˆ­ áˆ‹á‹­ áŠá‹á¢ áŠ¥á‰£áŠ­á‹ŽáŠ• á‰µáŠ•áˆ½ á‹­áŒ á‰¥á‰...")

        # Forward receipt to admin
        admin_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("âœ… Approve", callback_data=f"app_d_{user.id}"),
             InlineKeyboardButton("âŒ Reject", callback_data=f"rej_d_{user.id}")]
        ])
        
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"ðŸ“© **áŠ á‹²áˆµ á‹¨ Deposit á‹°áˆ¨áˆ°áŠ áŠ¨ {user.full_name} (@{user.username}) [ID: {user.id}]**")
        await update.message.forward(chat_id=ADMIN_ID)
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"á‹¨ Deposit á‰¥áˆ­ áˆ˜áŒ áŠ• áˆµáŠ•á‰µ á‹­áˆáŠ•? (áŒ¸á‹µá‰… áŠ¨á‰°áŒ«áŠ á‰ áŠ‹áˆ‹ á‹¨áˆšáŒ¨áˆ˜áˆ­ áˆ˜áŒ áŠ•):",
            reply_markup=admin_btn
        )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("app_d_"):
        user_id = int(data.split("_")[2])
        context.user_data[f"dep_user_{ADMIN_ID}"] = user_id
        await query.message.reply_text(f"áŠ¥á‰£áŠ­á‹ŽáŠ• áˆˆá‰°áŒ á‰ƒáˆš {user_id} á‹¨áˆšáŒ¨áˆ˜áˆ¨á‹áŠ• á‹¨á‰¥áˆ­ áˆ˜áŒ áŠ• á‰ á‰áŒ¥áˆ­ á‹«áˆµáŒˆá‰¡ (áˆáˆ³áˆŒ: 100):")

    elif data.startswith("rej_d_"):
        user_id = int(data.split("_")[2])
        await context.bot.send_message(chat_id=user_id, text="âŒ á‹¨ Deposit á‹°áˆ¨áˆ°áŠá‹Ž á‹á‹µá‰… á‰°á‹°áˆ­áŒ“áˆá¢")
        await query.edit_message_text("âŒ Deposit á‹á‹µá‰… á‰°á‹°áˆ­áŒ“áˆá¢")

    elif data.startswith("app_w_"):
        parts = data.split("_")
        user_id = int(parts[2])
        amount = float(parts[3])
        update_user_balance(user_id, -amount)
        await context.bot.send_message(chat_id=user_id, text=f"âœ… á‹¨ {amount} Birr Withdraw áŒ¥á‹«á‰„á‹Ž áŒ¸á‹µá‰‹áˆ! áŒˆáŠ•á‹˜á‰¡ á‰°áˆáŠ³áˆá¢")
        await query.edit_message_text("âœ… Withdraw áŒ¸á‹µá‰‹áˆá¢")

    elif data.startswith("rej_w_"):
        parts = data.split("_")
        user_id = int(parts[2])
        await context.bot.send_message(chat_id=user_id, text="âŒ á‹¨ Withdraw áŒ¥á‹«á‰„á‹Ž á‹á‹µá‰… á‰°á‹°áˆ­áŒ“áˆá¢")
        await query.edit_message_text("âŒ Withdraw á‹á‹µá‰… á‰°á‹°áˆ­áŒ“áˆá¢")

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
