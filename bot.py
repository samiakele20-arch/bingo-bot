import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)

# ------------------------------------
# 1. Keep-Alive Web Server for Render
# ------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# ------------------------------------
# 2. Main Bot Configuration
# ------------------------------------
TOKEN = '8691536980:AAGoA-CCwdTxOm43Wcj9Dovr1TFFc01O-s8'
ADMIN_IDS = [8607635094]
TELEBIRR_NO = "0908676709"

# የ GitHub Pages Mini App ሊንክህ
WEB_APP_URL = "https://samiakele20-arch.github.io/bingo-bot/"

MIN_DEPOSIT = 10.0
MIN_WITHDRAW = 100.0

user_balances = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = user_balances.get(user_id, 0.0)
    
    text_message = (
        "━━━━━━━━━━━━━━━━━━━\n"
        f"💰 **ቀሪ ሂሳብ (Balance):** `{balance:.2f} ETB`\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "🎮 **SamBingo Mini App ለመጫወት ከታች ያለውን ቁልፍ ይጫኑ!**"
    )
    
    keyboard = [
        # Mini App መክፈቻ WebApp Button
        [InlineKeyboardButton("🔴 PLAY SAMBINGO 🎲", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("🔵 Deposit (ብር ለመሙላት)", callback_data='deposit')],
        [InlineKeyboardButton("🟢 Withdraw (ብር ለማውጣት)", callback_data='withdraw')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(text_message, reply_markup=reply_markup, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.message.reply_text(text_message, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == 'deposit':
        context.user_data['waiting_for_action'] = 'deposit'
        msg = (
            "📥 **የዲፖዚት መመሪያ፦**\n\n"
            f"1. በ telebirr ቁጥር **`{TELEBIRR_NO}`** አነስተኛ **{MIN_DEPOSIT:.0f} ብር** ያስገቡ።\n"
            "2. ክፍያ የፈጸሙበትን **ደረሰኝ (Screenshot)** ወይም **የባንክ SMS መልእክት (Copy Paste)** አድርገው እዚህ ይላኩ።\n\n"
            "⚠️ ደረሰኙ በአድሚን ተመርምሮ ሂሳብዎ ይሞላል!"
        )
        await query.message.reply_text(msg, parse_mode='Markdown')

    elif data == 'withdraw':
        balance = user_balances.get(user_id, 0.0)
        if balance < MIN_WITHDRAW:
            await query.message.reply_text(
                f"❌ **ያልተሟላ የብር መጠን!**\n\n"
                f"አነስተኛው የብር ማውጫ መጠን **{MIN_WITHDRAW:.0f} ETB** ነው።\n"
                f"የእርስዎ አሁናዊ ቀሪ ሂሳብ፦ `{balance:.2f} ETB`"
            )
            return

        context.user_data['waiting_for_action'] = 'withdraw'
        msg = (
            "📤 **የብር ማውጫ (Withdrawal) መመሪያ፦**\n\n"
            f"💰 የእርስዎ ቀሪ ሂሳብ፦ `{balance:.2f} ETB`\n"
            f"🔹 አነስተኛ ማውጫ መጠን፦ **{MIN_WITHDRAW:.0f} ETB**\n\n"
            "እባክዎን **የሚያወጡትን የብር መጠን** እና **የ Telebirr ስልክ ቁጥርዎን** በአንድ ላይ ጽፈው ይላኩ።\n\n"
            "*(ምሳሌ፦ `100 Telebirr 0912345678`)*"
        )
        await query.message.reply_text(msg, parse_mode='Markdown')

    # ADMIN: Deposit Approve
    elif data.startswith('approve_dep_'):
        if user_id not in ADMIN_IDS:
            await query.answer("❌ እርስዎ አድሚን አይደሉም!", show_alert=True)
            return
        
        target_user_id = int(data.split('_')[2])
        user_balances[target_user_id] = user_balances.get(target_user_id, 0.0) + 10.0
        
        if query.message.caption:
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ **ተፈቅዷል! (10 ETB ተጨምሯል)**")
        else:
            await query.edit_message_text(text=f"{query.message.text}\n\n✅ **ተፈቅዷል! (10 ETB ተጨምሯል)**")
            
        try:
            await context.bot.send_message(
                chat_id=target_user_id, 
                text="🎉 ዲፖዚትዎ ተረጋግጧል! 10 ETB ሂሳብዎ ላይ ተጨምሯል። /start ብለው ቀሪ ሂሳብዎን ማየት ይችላሉ።"
            )
        except Exception as e:
            logging.error(f"Failed to send msg: {e}")

    # ADMIN: Deposit Reject
    elif data.startswith('reject_dep_'):
        if user_id not in ADMIN_IDS:
            await query.answer("❌ እርስዎ አድሚን አይደሉም!", show_alert=True)
            return
        
        target_user_id = int(data.split('_')[2])
        
        if query.message.caption:
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n❌ **ውድቅ ተደርጓል (Rejected)!**")
        else:
            await query.edit_message_text(text=f"{query.message.text}\n\n❌ **ውድቅ ተደርጓል (Rejected)!**")
            
        try:
            await context.bot.send_message(
                chat_id=target_user_id, 
                text="❌ የላኩት ደረሰኝ ውድቅ ተደርጓል። እባክዎን ትክክለኛ ደረሰኝ ይላኩ።"
            )
        except Exception as e:
            logging.error(f"Failed to send msg: {e}")

# User Message Handling
async def handle_user_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    action = context.user_data.get('waiting_for_action')

    if action == 'deposit':
        context.user_data['waiting_for_action'] = None
        await update.message.reply_text("⏳ ደረሰኝዎ ደርሶናል! አድሚኑ እስኪያረጋግጥ ድረስ ትንሽ ይጠብቁ።")
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve (10 ETB)", callback_data=f'approve_dep_{user_id}'),
                InlineKeyboardButton("❌ Reject", callback_data=f'reject_dep_{user_id}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.message.photo:
            photo_file_id = update.message.photo[-1].file_id
            for admin_id in ADMIN_IDS:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_file_id,
                    caption=f"📥 **አዲስ የዲፖዚት ጥያቄ (Photo)!**\n\nከ ተጠቃሚ ID: `{user_id}`",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        elif update.message.text:
            receipt_text = update.message.text
            for admin_id in ADMIN_IDS:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"📥 **አዲስ የዲፖዚት ጥያቄ (Text SMS)!**\n\nከ ተጠቃሚ ID: `{user_id}`\n\n**መልእክት፦**\n{receipt_text}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )

# ------------------------------------
# 3. Execution Block
# ------------------------------------
if __name__ == '__main__':
    server_thread = Thread(target=run_health_check_server)
    server_thread.daemon = True
    server_thread.start()

    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_user_messages))
    
    print("ቦቱ በትክክል መስራት ጀምሯል...")
    app.run_polling(poll_interval=1.0)
