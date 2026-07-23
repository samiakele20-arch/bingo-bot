import os
import asyncio
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update

# Logging setup
logging.basicConfig(level=logging.INFO)

# Dummy Web Server for Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("እንኳን ወደ Bingo Bot በሰላም መጡ!")

# Main function
if __name__ == "__main__":
    # Start web server in background thread so Render stays alive
    Thread(target=run_health_check_server, daemon=True).start()

    # Paste your Telegram Bot Token here if needed, or use environment variable
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "8691536980:AAGoA-CCwdTxOm43Wcj9Dovr1TFFc01O-s8")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    logging.info("Starting bot...")
    app.run_polling()
