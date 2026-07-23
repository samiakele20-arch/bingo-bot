import os
import logging
import random
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)

# ------------------------------------
# 1. Dummy Web Server for Render Keep-Alive
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
# 2. Main Telegram Bingo Bot Logic
# ------------------------------------
TOKEN = '8691536980:AAGoA-CCwdTxOm43Wcj9Dovr1TFFc01O-s8'
ADMIN_IDS = [8607635094]
TELEBIRR_NO = "0908676709"

ENTRY_FEE = 10.0       # የመግቢያ ዋጋ
WINNER_SHARE = 8.0      # ለአሸናፊው ከእያንዳንዱ ሰው (2 ብር ላንተ ትርፍ)
MIN_PLAYERS = 5         # ዝቅተኛ ተጫዋች
MIN_DEPOSIT = 10.0      # አነስተኛ ዲፖዚት

user_balances = {}
waiting_lobby = []      # የመጠበቂያ ክፍል
active_game_players = []

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ዋናው መነሻ ገጽ (ከ ቀይ እና ሰማያዊ ቁልፎች ጋር)
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
        [InlineKeyboardButton("🔵 Deposite (ብር ለመሙላት)", callback_data='deposit')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text_message, reply_markup=reply_markup, parse_mode='Markdown')

# የካርድ መምረጫ እና የሎቢ ገጽ (ከ ቢጫ እና ሰማያዊ ቁልፎች ጋር)
async def show_card_selection(context: ContextTypes.DEFAULT_TYPE, player_ids):
    keyboard = [
        [InlineKeyboardButton("🟡 🃏 ካርድ ምረጥ / ተዘጋጅ", callback_data='select_card')],
        [InlineKeyboardButton("🔵 🔙 ወደ ዋናው ገጽ", callback_data='go_home')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    for pid in player_ids:
        try:
            await context.bot.send_message(
                chat_id=pid,
                text="🎮 **አዲስ ዙር!**\n\nእባክዎን ጨዋታው ከመጀመሩ በፊት ካርድዎን ይምረጡ፦",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception:
            pass

# የ 30 ሰከንድ ቆጣሪ ማስሄጃ
async def run_30s_lobby_timer(context: ContextTypes.DEFAULT_TYPE):
    for sec in range(30, 0, -5):
        for pid in list(waiting_lobby):
            try:
                await context.bot.send_message(
                    chat_id=pid,
                    text=f"⏳ ጨዋታው ለመጀመር **{sec} ሰከንድ** ቀርቷል!\n👥 ተጫዋቾች፦ {len(waiting_lobby)}/{MIN_PLAYERS}",
                    parse_mode='Markdown'
                )
            except Exception:
                pass
        await asyncio.sleep(5)
        
    if len(waiting_lobby) >= MIN_PLAYERS:
        global active_game_players
        active_game_players = list(waiting_lobby)
        waiting_lobby.clear()
        
        total_prize = len(active_game_players) * WINNER_SHARE
        for pid in active_game_players:
            try:
                await context.bot.send_message(
                    chat_id=pid,
                    text=f"🚀 **ጨዋታው ተጀምሯል!**\n🏆 የሽልማት መጠን፦ **{total_prize:.0f} ETB**",
                    parse_mode='Markdown'
                )
            except Exception:
                pass
    else:
        for pid in list(waiting_lobby):
            try:
                await context.bot.send_message(
                    chat_id=pid,
                    text=f"⚠️ ዝቅተኛ ተጫዋች ({MIN_PLAYERS}) ስላልሞላ ጨዋታው አልጀመረም። ተጨማሪ ተጫዋች እየተጠበቀ ነው..."
                )
            except Exception:
                pass

# አሸናፊ ሲኖር የ 10 ሰከንድ ማሳወቂያ
async def handle_game_winner(context: ContextTypes.DEFAULT_TYPE, winner_name, winner_id, prize_amount):
    user_balances[winner_id] = user_balances.get(winner_id, 0.0) + prize_amount
    players_to_notify = list(active_game_players)
    
    for sec in range(10, 0, -2):
        msg = (
            f"🎉 **ቢንጎ! ጨዋታው ተጠናቋል!** 🎉\n\n"
            f"🏆 **አሸናፊ፦** {winner_name}\n"
            f"💰 **የበላው ብር፦** `{prize_amount:.0f} ETB`\n\n"
            f"⏱️ ወደ ካርድ መምረጫ ገጽ ለመሄድ **{sec} ሰከንድ** ይቀራል..."
        )
        for pid in players_to_notify:
            try:
                await context.bot.send_message(chat_id=pid, text=msg, parse_mode='Markdown')
            except Exception:
                pass
        await asyncio.sleep(2)
        
    await show_card_selection(context, players_to_notify)
    asyncio.create_task(run_30s_lobby_timer(context))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == 'play_10':
        balance = user_balances.get(user_id, 0.0)
        
        if user_id in waiting_lobby:
            await query.message.reply_text("⚠️ እርስዎ አስቀድመው የመጠበቂያ ክፍል ውስጥ ይገኛሉ።")
            return

        if balance < ENTRY_FEE:
            await query.message.reply_text(f"❌ ለጨዋታው በቂ ሂሳብ የለዎትም። ቢያንስ {ENTRY_FEE:.0f} ETB ያስፈልጋል!")
            return

        user_balances[user_id] -= ENTRY_FEE
        waiting_lobby.append(user_id)
        
        if len(waiting_lobby) == 1:
            asyncio.create_task(run_30s_lobby_timer(context))

        await query.message.reply_text(
            f"✅ ተመዝግበዋል!\n"
            f"👥 የተመዘገቡ ተጫዋቾች፦ {len(waiting_lobby)}\n"
            f"⏱️ የ 30 ሰከንድ ቆጣሪ ተጀምሯል..."
        )

    elif data == 'go_home':
        balance = user_balances.get(user_id, 0.0)
        text_message = (
            "━━━━━━━━━━━━━━━━━━━\n"
            f"💰 **ቀሪ ሂሳብ (Balance):** `{balance:.2f} ETB`\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [
            [InlineKeyboardButton("🔴 PLAY  |  10 ETB", callback_data='play_10')],
            [InlineKeyboardButton("🔵 Deposite (ብር ለመሙላት)", callback_data='deposit')]
        ]
        await query.message.reply_text(text_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == 'deposit':
        context.user_data['waiting_for_receipt'] = True
        msg = (
            "📥 **የዲፖዚት መመሪያ፦**\n\n"
            f"1. በ telebirr ቁጥር **`{TELEBIRR_NO}`** አነስተኛ **{MIN_DEPOSIT:.0f} ብር** ያስገቡ።\n"
            "2. ክፍያ የፈጸሙበትን **ደረሰኝ (Screenshot)** እዚህ ይላኩ።\n\n"
            "⚠️ ደረሰኙ በአድሚን ተመርምሮ ሂሳብዎ ይሞላል!"
        )
        await query.message.reply_text(msg, parse_mode='Markdown')

    elif data.startswith('approve_'):
        if user_id not in ADMIN_IDS:
            await query.answer("❌ እርስዎ አድሚን አይደሉም!", show_alert=True)
            return
        
        target_user_id = int(data.split('_')[1])
        user_balances[target_user_id] = user_balances.get(target_user_id, 0.0) + 10.0
        
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ **ተፈቅዷል! (10 ETB ተጨምሯል)**")
        await context.bot.send_message(
            chat_id=target_user_id, 
            text="🎉 ዲፖዚትዎ ተረጋግጧል! ሂሳብዎ ተጨምሯል። /start ብለው ይጫወቱ።"
        )

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.user_data.get('waiting_for_receipt'):
        context.user_data['waiting_for_receipt'] = False
        photo_file_id = update.message.photo[-1].file_id
        
        await update.message.reply_text("⏳ ደረሰኝዎ ደርሶናል! አድሚኑ እስኪያረጋግጥ ድረስ ትንሽ ይጠብቁ።")
        
        keyboard = [[InlineKeyboardButton("✅ Approve (10 ETB)", callback_data=f'approve_{user_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        for admin_id in ADMIN_IDS:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo_file_id,
                caption=f"📥 **አዲስ የዲፖዚት ጥያቄ!**\n\nከ ተጠቃሚ ID: `{user_id}`",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

# ------------------------------------
# 3. Execution Block
# ------------------------------------
if __name__ == '__main__':
    # Keep-Alive ሰርቨሩን በተለየ thread ማስጀመር
    server_thread = Thread(target=run_health_check_server)
    server_thread.daemon = True
    server_thread.start()

    # ቦቱን ማስነስ
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    
    print("ቦቱ እና Keep-Alive ሰርቨሩ ስራ ጀምረዋል...")
    app.run_polling(poll_interval=1.0)
