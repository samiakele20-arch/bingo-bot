import os
import logging
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
# 2. Main Bot Configuration & Logic
# ------------------------------------
TOKEN = '8691536980:AAGoA-CCwdTxOm43Wcj9Dovr1TFFc01O-s8'
ADMIN_IDS = [8607635094]
TELEBIRR_NO = "0908676709"

ENTRY_FEE = 10.0
MIN_DEPOSIT = 10.0
MIN_WITHDRAW = 100.0

user_balances = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 5x5 የቢንጎ ካርድ ማመንጫ ፈንክሽን
def generate_bingo_card():
    col_b = random.sample(range(1, 16), 5)
    col_i = random.sample(range(16, 31), 5)
    col_n = random.sample(range(31, 46), 5)
    col_g = random.sample(range(46, 61), 5)
    col_o = random.sample(range(61, 76), 5)
    
    card_str = "🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧\n"
    card_str += "  **B**   |  **I**   |  **N**  |  **G**  |  **O**  \n"
    card_str += "───────────────\n"
    
    for row in range(5):
        b = f"{col_b[row]:02d}"
        i = f"{col_i[row]:02d}"
        n = "⭐" if row == 2 else f"{col_n[row]:02d}"
        g = f"{col_g[row]:02d}"
        o = f"{col_o[row]:02d}"
        card_str += f" `{b}` | `{i}` | `{n}` | `{g}` | `{o}` \n"
        
    card_str += "🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧"
    return card_str

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = user_balances.get(user_id, 0.0)
    
    text_message = (
        "━━━━━━━━━━━━━━━━━━━\n"
        f"💰 **ቀሪ ሂሳብ (Balance):** `{balance:.2f} ETB`\n"
        "━━━━━━━━━━━━━━━━━━━"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔴 PLAY  |  10 ETB", callback_data='play_10')],
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

    # PLAY ሲነካ ወደ Room ይገባል (ብር ገና አይቀነስም!)
    if data == 'play_10':
        balance = user_balances.get(user_id, 0.0)

        if balance < ENTRY_FEE:
            await query.message.reply_text(f"❌ ለጨዋታው በቂ ሂሳብ የለዎትም። ቢያንስ {ENTRY_FEE:.0f} ETB ያስፈልጋል!")
            return

        # የካርድ መምረጫ Room ባትኖች (Orange Theme)
        card_keyboard = [
            [
                InlineKeyboardButton("🟧 Card #1", callback_data='select_card_1'),
                InlineKeyboardButton("🟧 Card #2", callback_data='select_card_2')
            ],
            [
                InlineKeyboardButton("🟧 Card #3", callback_data='select_card_3'),
                InlineKeyboardButton("🟧 Card #4", callback_data='select_card_4')
            ],
            [InlineKeyboardButton("🎲 Random Card (በዘፈቀደ መምረጫ)", callback_data='select_card_random')],
            [InlineKeyboardButton("🔙 ወደ ዋናው ገጽ ተመለስ", callback_data='back_to_start')]
        ]
        reply_markup = InlineKeyboardMarkup(card_keyboard)

        await query.message.reply_text(
            "🟠 **ወደ ቢንጎ ካርድ መምረጫ ክፍል እንኳን ደህና መጡ!** 🟠\n\n"
            f"💰 የእርስዎ አሁናዊ ቀሪ ሂሳብ፦ `{balance:.2f} ETB`\n"
            f"🎫 የጨዋታው ዋጋ፦ **10 ETB**\n\n"
            "👇 እባክዎን ለመጫወት የሚፈልጉትን የካርድ ቁጥር ይምረጡ፦",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    # ካርድ ሲመረጥ ብቻ 10 ብር ተቀንሶ ካርዱ ይወጣል
    elif data.startswith('select_card_'):
        balance = user_balances.get(user_id, 0.0)
        
        if balance < ENTRY_FEE:
            await query.message.reply_text("❌ የላከው ሂሳብ በቂ አይደለም! እባክዎን አስቀድመው ዲፖዚት ያድርጉ።")
            return

        # 10 ብሩ አሁን ይቀነሳል
        user_balances[user_id] -= ENTRY_FEE
        card_num = data.split('_')[2]
        
        bingo_card_text = generate_bingo_card()
        
        card_title = "🎲 Random Bingo Card" if card_num == 'random' else f"🎴 Bingo Card #{card_num}"
        
        msg = (
            f"🎉 **ካርድዎ በትክክል ተመርጧል!**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 **{card_title}**\n\n"
            f"{bingo_card_text}\n\n"
            f"✅ **10 ETB ከቀሪ ሂሳብዎ ተቀንሷል።**\n"
            f"💰 አሁናዊ ቀሪ ሂሳብዎ፦ `{user_balances[user_id]:.2f} ETB`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            "⏳ *ጨዋታው ተጫዋቾች ተሟልተው ሲጀምሩ ቁጥሮች መውጣት ይጀምራሉ...*"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 ወደ ዋናው ገጽ ተመለስ", callback_data='back_to_start')]]
        await query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == 'back_to_start':
        await start(update, context)

    elif data == 'deposit':
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

    # ADMIN: Withdraw Approve
    elif data.startswith('approve_wd_'):
        if user_id not in ADMIN_IDS:
            await query.answer("❌ እርስዎ አድሚን አይደሉም!", show_alert=True)
            return
        
        parts = data.split('_')
        target_user_id = int(parts[2])
        amount = float(parts[3])

        current_bal = user_balances.get(target_user_id, 0.0)
        if current_bal >= amount:
            user_balances[target_user_id] -= amount
            await query.edit_message_text(text=f"{query.message.text}\n\n✅ **የማውጣት ጥያቄው ጸድቋል! ብሩ ተቀንሷል።**")
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"🎉 የ **{amount:.0f} ETB** የብር ማውጣት ጥያቄዎ ጸድቆ በ Telebirr ተልኳል! እናመሰግናለን።"
            )
        else:
            await query.answer("❌ ተጠቃሚው በቂ ሂሳብ የለውም!", show_alert=True)

    # ADMIN: Withdraw Reject
    elif data.startswith('reject_wd_'):
        if user_id not in ADMIN_IDS:
            await query.answer("❌ እርስዎ አድሚን አይደሉም!", show_alert=True)
            return
        
        target_user_id = int(data.split('_')[2])
        await query.edit_message_text(text=f"{query.message.text}\n\n❌ **የማውጣት ጥያቄው ውድቅ ተደርጓል!**")
        await context.bot.send_message(
            chat_id=target_user_id,
            text="❌ የብር ማውጣት ጥያቄዎ ውድቅ ተደርጓል። ለተጨማሪ መረጃ አድሚኑን ያናግሩ።"
        )

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

    elif action == 'withdraw':
        context.user_data['waiting_for_action'] = None
        req_text = update.message.text
        
        await update.message.reply_text("⏳ የብር ማውጣት ጥያቄዎ ለአድሚን ተልኳል! አድሚኑ ብሩን አስተላልፎ እስኪያጸድቅ ይጠብቁ።")
        
        try:
            amount = float([s for s in req_text.split() if s.isdigit()][0])
        except Exception:
            amount = MIN_WITHDRAW

        keyboard = [
            [
                InlineKeyboardButton("✅ Approve Transfer", callback_data=f'approve_wd_{user_id}_{amount}'),
                InlineKeyboardButton("❌ Reject", callback_data=f'reject_wd_{user_id}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        for admin_id in ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"📤 **አዲስ የብር ማውጣት (Withdrawal) ጥያቄ!**\n\n"
                    f"👤 ተጠቃሚ ID: `{user_id}`\n"
                    f"📝 የመልእክት ዝርዝር፦\n`{req_text}`"
                ),
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
