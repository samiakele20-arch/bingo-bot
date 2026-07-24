import logging
import re
import json
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

    # Mini App ሲከፈት የሰውየውን ባላንስ አብሮ ይልካል
    url_with_balance = f"{MINI_APP_URL}?balance={user_balances[user_id]}"

    keyboard = [
        [InlineKeyboardButton("🔴 PLAY SAMBINGO 🎲", web_app=WebAppInfo(url=url_with_balance))],
        [InlineKeyboardButton("💳 Deposit (ብር ለመሙላት)", callback_data="deposit_info")],
        [InlineKeyboardButton("🟢 Withdraw (ብር ለማውጣት)", callback_data="withdraw_info")]
    ]
    await update.message.reply_text(
        f"ሰላም {update.effective_user.first_name}! ወደ SamBingo እንኳን ደህና መጡ።\n\n💰 **የአሁኑ ባላንስዎ: {user_balances[user_id]} ETB**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def deposit_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = (
        "📥 **የዲፖዚት መመሪያ:-**\n\n"
        "1. በ telebirr ቁጥር `0908676709` አነስተኛ 10 ብር ያስገቡ።\n"
        "2. ክፍያ የፈጸሙበትን ደረሰኝ (Screenshot) ወይም የባንክ SMS መልእክት (Copy Paste) አድርገው እዚህ ይላኩ።\n\n"
        "⚠️ ደረሰኙ በአድሚን ተመርምሮ ሂሳብዎ ይሞላል!"
    )
    await query.message.reply_text(msg, parse_mode="Markdown")

# SMS ወይም ፎቶ ሲላክ ትክክለኛውን የብር መጠን ለይቶ ማወቅ
async def handle_deposit_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.caption or update.message.text or ""
    
    # SMS ውስጥ "ETB 90.00" ወይም "90 ETB" የሚለውን ይፈልጋል
    amount = 0
    match = re.search(r'(?:ETB|Birr|ብር)\s*([\d\.,]+)|([\d\.,]+)\s*(?:ETB|Birr|ብር)', text, re.IGNORECASE)
    if match:
        val = match.group(1) or match.group(2)
        try:
            amount = float(val.replace(',', ''))
        except:
            amount = 0

    if amount <= 0:
        amount = 10 # ነባሪ ካልተገኘ

    admin_keyboard = [
        [
            InlineKeyboardButton(f"✅ Approve ({amount} ETB)", callback_data=f"app_{user.id}_{amount}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user.id}")
        ]
    ]

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📥 **አዲስ የ Deposit ጥያቄ!**\n\nተጠቃሚ: {user.first_name}\nID: `{user.id}`\nየላከው ጽሁፍ:\n`{text}`\n\nተለይቶ የታወቀ መጠን: **{amount} ETB**",
        reply_markup=InlineKeyboardMarkup(admin_keyboard),
        parse_mode="Markdown"
    )
    await update.message.reply_text("⏳ ደረሰኝዎ ደርሷል! አድሚኑ እስኪያረጋግጥ ድረስ ትንሽ ይጠበቁ።")

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    action = data[0]
    user_id = int(data[1])

    if action == "app":
        amount = float(data[2])
        user_balances[user_id] = user_balances.get(user_id, 0.0) + amount
        await query.edit_message_text(f"✅ ተጸድቋል! {amount} ETB ለ ID `{user_id}` ተደምሯል።")
        await context.bot.send_message(
            chat_id=user_id, 
            text=f"🎉 ዲፖዚትዎ ተረጋግጧል! **{amount} ETB** ሂሳብዎ ላይ ተጨምሯል።\nእባክዎን **/start** ብለው አዲስ የጨዋታ ሊንክ ይክፈቱ።",
            parse_mode="Markdown"
        )

    elif action == "rej":
        await query.edit_message_text(f"❌ የ ID `{user_id}` ጥያቄ ውድቅ ተደርጓል።")
        await context.bot.send_message(chat_id=user_id, text="❌ ደረሰኝዎ ውድቅ ተደርጓል። እባክዎን ትክክለኛ ደረሰኝ ይላኩ።")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(deposit_info, pattern="^deposit_info$"))
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^(app|rej)_"))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_deposit_request))
    app.run_polling()

if __name__ == '__main__':
    main()
