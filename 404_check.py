import json
import requests
import time
import string
import random
import asyncio
import threading
from flask import Flask
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, ContextTypes  # Changed import

# === CONFIG ===
JSONBIN_API_KEY = "$2a$10$KXx5Yb2HF6z292WnEjQcY.P/WggIJ9sbwMXyhT9UmzFPtlyavGGlK"
JSONBIN_BIN_ID = "6877dbaf3052b733d10d94bc"
TELEGRAM_BOT_TOKEN = "7958166262:AAHP0UtNmeTHVezrDxibQoMuP00nmNr-fmw"
DOMAIN = "https://jarvis123563.github.io/404_check/"

# === INIT FLASK ===
app_flask = Flask(__name__)

@app_flask.route('/health')
def health():
    return "Bot is alive ✅", 200

threading.Thread(target=app_flask.run, kwargs={"host": "0.0.0.0", "port": 8080}, daemon=True).start()

# === INIT BOT ===
# Removed ApplicationBuilder and created Updater instead
updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
bot = updater.bot
dp = updater.dispatcher

# === /track COMMAND ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to the Link Tracker Bot!\n\n"
        "📌 This bot helps you shorten links and track how many people clicked them.\n\n"
        "🔧 How to use:\n"
        "1. Send /track followed by your link. Example:\n"
        "/track https://example.com\n"
        "/track <your link>\n"
        "2. You will receive a short link like:\n"
        "`https://yourdomain.com/abc123`\n"
        "3. Share this link! You will be notified when someone clicks it.\n\n"
        "ℹ️ The bot checks click stats every 10 seconds.\n"
        "🔗 All links are tracked privately and safely.\n\n",
        parse_mode="Markdown"
    )

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "anonymous"

    if not context.args:
        await update.message.reply_text("❌ Please send the link to track like this:\n/track https://example.com")
        return

    original_link = context.args[0]
    short_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    short_url = f"{DOMAIN}{short_code}"
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    bin_url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"
    headers = {"X-Master-Key": JSONBIN_API_KEY}

    try:
        res = requests.get(bin_url, headers=headers)
        data = res.json().get("record", {})
    except:
        data = {}

    data[short_code] = {
        "original_link": original_link,
        "owner_id": user_id,
        "owner_username": username,
        "created_at": timestamp,
        "clicks": 0
    }

    save_url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    requests.put(save_url, headers={"Content-Type": "application/json", "X-Master-Key": JSONBIN_API_KEY}, json=data)

    await update.message.reply_text(f"✅ Your short link:\n{short_url}")

# === CLICK NOTIFICATION CHECKER ===
last_clicks = {}

async def check_clicks():
    try:
        res = requests.get(
            f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest",
            headers={"X-Master-Key": JSONBIN_API_KEY}
        )
        data = res.json().get("record", {})

        for code, info in data.items():
            current_clicks = info.get("clicks", 0)
            previous_clicks = last_clicks.get(code, 0)

            if current_clicks > previous_clicks:
                diff = current_clicks - previous_clicks
                owner_id = info.get("owner_id")
                original_link = info.get("original_link")
                short_link = f"{DOMAIN}{code}"

                try:
                    await bot.send_message(
                        chat_id=owner_id,
                        text=(
                            f"📈 Someone clicked your tracked link!\n"
                            f"🔗 Link: {short_link}\n"
                            f"👁 Total Clicks: {current_clicks}"
                        )
                    )
                except Exception as e:
                    print(f"Failed to notify {owner_id}: {e}")

                last_clicks[code] = current_clicks
            elif code not in last_clicks:
                last_clicks[code] = current_clicks

    except Exception as e:
        print(f"Error in click checker: {e}")

# === MAIN ===
async def start_tracking():
    dp.add_handler(CommandHandler("track", track))
    dp.add_handler(CommandHandler("start", start))
    
    # Start polling in a background thread
    updater.start_polling()
    
    # Start the click checker loop
    while True:
        await check_clicks()
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(start_tracking())
