import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "7961917711:AAE4S416E-10-W1T-1a_Vv8p4c1Qf4"
ADMIN_ID = 6870028741
MINI_APP_URL = "https://samiakele20-arch.github.io/bingo-bot/"

user_balances = {}

logging.basicConfig(level=logging.INFO)

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

# ደረሰኝ ሲላክ በቀጥታ ለአድሚን በፎቶ መልክ የሚያስተላልፍ
async def handle_deposit_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    admin_keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"app_{user.id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user.id}")
        ]
    ]
    
    # ፎቶ ከሆነ ፎቶውን ለአድሚን ይልካል
    if update.message.photo:
        photo_id = update.message.photo[-1].file_id
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_id,
            caption=f"📥 **አዲስ የ Deposit ደረሰኝ!**\n\nተጠቃሚ: {user.first_name}\nID: `{user.id}`",
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode="Markdown"
        )
    else:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📥 **አዲስ የ Deposit ጥያቄ!**\n\nተጠቃሚ: {user.first_name}\nID: `{user.id}`\nጽሁፍ: {update.message.text}",
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode="Markdown"
        )
        
    await update.message.reply_text("✅ ደረሰኝዎ ለአድሚን ተልኳል። ከተረጋገጠ በኋላ ባላንስዎ ላይ ይደመራል።")

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    action = data[0]
    user_id = int(data[1])

    if action == "app":
        # በነባሪ ባላንሳቸውን ያድሳል
        user_balances[user_id] = user_balances.get(user_id, 0.0) + 50.0
        await query.edit_message_text(f"✅ ተጸድቋል! ለ ID `{user_id}` ብር ተደምሯል።")
        await context.bot.send_message(chat_id=user_id, text=f"🎉 የ Deposit ጥያቄዎ ጸድቋል! አዲስ ባላንስዎ: {user_balances[user_id]} ETB")

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
