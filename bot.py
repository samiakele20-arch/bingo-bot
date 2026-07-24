import logging
import re
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# BOT CONFIGURATION
BOT_TOKEN = "7961917711:AAE4S416E-10-W1T-1a_Vv8p4c1Qf4"
ADMIN_ID = 6870028741
MINI_APP_URL = "https://samiakele20-arch.github.io/bingo-bot/"

user_balances = {}
active_games = {}

logging.basicConfig(level=logging.INFO)

# Validate Bingo Patterns (Row, Column, Diagonals, and 4 Corners)
def check_bingo_patterns(card_grid, called_balls):
    called = set(called_balls)
    
    # 1. Check Rows (አግድም)
    for r in range(5):
        if all(card_grid[r*5 + c] in called or r*5 + c == 12 for c in range(5)):
            return True
            
    # 2. Check Columns (ቁልቁል)
    for c in range(5):
        if all(card_grid[r*5 + c] in called or r*5 + c == 12 for r in range(5)):
            return True

    # 3. Check Diagonals (ሰያፍ)
    if all(card_grid[i*5 + i] in called or i*5 + i == 12 for i in range(5)):
        return True
    if all(card_grid[i*5 + (4-i)] in called or i*5 + (4-i) == 12 for i in range(5)):
        return True

    # 4. Check 4 Corners (አራቱ ማዕዘኖች)
    corners = [0, 4, 20, 24]
    if all(card_grid[idx] in called or idx == 12 for idx in corners):
        return True

    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 0.0

    keyboard = [
        [InlineKeyboardButton("🔴 PLAY SAMBINGO 🎲", web_app=WebAppInfo(url=MINI_APP_URL))],
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit_info"), InlineKeyboardButton("💰 Balance", callback_data="check_balance")]
    ]
    await update.message.reply_text(
        f"ሰላም {update.effective_user.first_name}! ወደ SamBingo እንኳን ደህና መጡ።\n\nየአሁኑ ባላንስዎ: {user_balances[user_id]} ETB",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Dynamic Deposit Handler (ማንኛውንም የብር መጠን ለይቶ ለአድሚን የሚልክ)
async def handle_deposit_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text or update.message.caption or ""
    
    # በጽሁፉ ወይም በደረሰኙ ላይ ያለውን የብር መጠን ይፈልጋል
    numbers = re.findall(r'\d+', text)
    
    if numbers:
        amount = int(numbers[0])  # ተጫዋቹ ያስገባው ትክክለኛ መጠን (50, 100, 200...)
    else:
        amount = 10  # ነባሪ

    admin_keyboard = [
        [
            InlineKeyboardButton(f"✅ Approve ({amount} ETB)", callback_data=f"app_{user.id}_{amount}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user.id}")
        ]
    ]
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📥 **አዲስ የ Deposit ጥያቄ!**\n\nተጠቃሚ: {user.first_name}\nID: `{user.id}`\nያሰገባው መጠን: **{amount} ETB**",
        reply_markup=InlineKeyboardMarkup(admin_keyboard),
        parse_mode="Markdown"
    )
    await update.message.reply_text(f"✅ የ {amount} ETB ደረሰኝዎ ለአድሚን ተልኳል። ከተረጋገጠ በኋላ ባላንስዎ ላይ ይደመራል።")

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    action = data[0]
    user_id = int(data[1])

    if action == "app":
        amount = int(data[2])
        # ያሰገባው መጠን ብቻ ባላንሱ ላይ ይደመራል
        user_balances[user_id] = user_balances.get(user_id, 0.0) + amount
        await query.edit_message_text(f"✅ ተጸድቋል! {amount} ETB ለ ID `{user_id}` ተደምሯል።")
        await context.bot.send_message(chat_id=user_id, text=f"🎉 የ {amount} ETB Deposit ጥያቄዎ ጸድቋል! አዲስ ባላንስዎ: {user_balances[user_id]} ETB")

    elif action == "rej":
        await query.edit_message_text(f"❌ የ ID `{user_id}` የ Deposit ጥያቄ ውድቅ ተደርጓል።")
        await context.bot.send_message(chat_id=user_id, text="❌ የ Deposit ጥያቄዎ ውድቅ ተደርጓል። እባክዎን ትክክለኛ ደረሰኝ ይላኩ።")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^(app|rej)_"))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_deposit_request))
    app.run_polling()

if __name__ == '__main__':
    main()
