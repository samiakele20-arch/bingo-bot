import logging
import re
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "7961917711:AAE4S416E-10-W1T-1a_Vv8p4c1Qf4"
ADMIN_ID = 6870028741
MINI_APP_URL = "https://samiakele20-arch.github.io/bingo-bot/"

DB_FILE = "balances.json"

# ባላንስ እንዳይጠፋ በፋይል ውስጥ ማስቀመጫ functions
def load_balances():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_balances(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

user_balances = load_balances()

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_balances:
        user_balances[user_id] = 0.0
        save_balances(user_balances)

    current_bal = user_balances[user_id]
    url_with_balance = f"{MINI_APP_URL}?balance={current_bal}"

    keyboard = [
        [InlineKeyboardButton("🔴 PLAY SAMBINGO 🎲", web_app=WebAppInfo(url=url_with_balance))],
        [InlineKeyboardButton("💳 Deposit (ብር ለመሙላት)", callback_data="deposit_info")],
        [InlineKeyboardButton("🟢 Withdraw (ብር ለማውጣት)", callback_data="withdraw_info")]
    ]
    await update.message.reply_text(
        f"ሰላም {update.effective_user.first_name}! ወደ SamBingo እንኳን ደህና መጡ።\n\n💰 **የአሁኑ ባላንስዎ: {current_bal} ETB**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def deposit_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # ጽሁፉ ከ "አነስተኛ 10 ብር" ነፃ ሆኗል
    msg = (
        "📥 **የዲፖዚት መመሪያ:-**\n\n"
        "1. በ Telebirr ቁጥር `0908676709` የፈለጉትን የብር መጠን ያስገቡ።\n"
        "2. የላኩበትን ደረሰኝ (Screenshot) ወይም የባንክ SMS መልእክት Copy አድርገው እዚህ ይላኩ።\n\n"
        "⚠️ ደረሰኙ በአድሚን ተመርምሮ ሂሳብዎ ይሞላል!"
    )
    await query.message.reply_text(msg, parse_mode="Markdown")

async def handle_deposit_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.caption or update.message.text or ""
    
    # Telebirr እና CBE SMS ውስጥ ያለውን የብር መጠን በደንብ ይለያል (ምሳሌ: ETB 25.0, 50.00 ETB, etc)
    match = re.search(r'(?:ETB|ብር)\s*([\d\.]+)|([\d\.]+)\s*(?:ETB|ብር)', text, re.IGNORECASE)
    detected_amount = 0.0
    if match:
        val_str = match.group(1) or match.group(2)
        try:
            detected_amount = float(val_str)
        except:
            detected_amount = 0.0

    btn_text = f"✅ Approve ({detected_amount} ETB)" if detected_amount > 0 else "✅ Approve"

    admin_keyboard = [
        [
            InlineKeyboardButton(btn_text, callback_data=f"app_{user.id}_{detected_amount}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user.id}")
        ]
    ]

    if update.message.photo:
        photo_id = update.message.photo[-1].file_id
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_id,
            caption=f"📥 **አዲስ የ Deposit ደረሰኝ (Photo)!**\n\nተጠቃሚ: {user.first_name}\nID: `{user.id}`",
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode="Markdown"
        )
    else:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📥 **አዲስ የ Deposit ጥያቄ!**\n\nተጠቃሚ: {user.first_name}\nID: `{user.id}`\n\n**ጽሁፍ፦**\n`{text}`",
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode="Markdown"
        )
        
    await update.message.reply_text("⏳ ደረሰኝዎ ለአድሚን ተልኳል! ተመርምሮ ሂሳብዎ ይሞላል።")

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    action = data[0]
    user_id = str(data[1])

    if action == "app":
        amount = float(data[2]) if len(data) > 2 else 0.0
        
        # ባላንስ ላይ ይጨምራል፤ ለዘለቄታውም Save ያደርገዋል
        current = user_balances.get(user_id, 0.0)
        user_balances[user_id] = current + amount
        save_balances(user_balances)

        new_balance = user_balances[user_id]

        await query.edit_message_text(f"✅ ተጸድቋል! {amount} ETB ለ ID `{user_id}` ተደምሯል። አጠቃላይ ባላንስ: {new_balance} ETB")
        
        # ለተጠቃሚው አዲሱን ባላንስ ይልካል
        await context.bot.send_message(
            chat_id=int(user_id), 
            text=f"🎉 የ Deposit ጥያቄዎ ጸድቋል!\n\n💰 የተጨመረ: **{amount} ETB**\n💵 አጠቃላይ ባላንስዎ: **{new_balance} ETB**\n\nአዲሱን ባላንስ በ Mini App ለማየት **/start** ብለው ድጋሚ ይክፈቱ።",
            parse_mode="Markdown"
        )

    elif action == "rej":
        await query.edit_message_text(f"❌ የ ID `{user_id}` ጥያቄ ውድቅ ተደርጓል።")
        await context.bot.send_message(chat_id=int(user_id), text="❌ ደረሰኝዎ ውድቅ ተደርጓል። እባክዎን ትክክለኛ ደረሰኝ ይላኩ።")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deposit_info, pattern="^deposit_info$"))
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^(app|rej)_"))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_deposit_request))
    app.run_polling()

if __name__ == '__main__':
    main()
