from flask import Flask, request
import os, logging, json, base64
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import google_drive_tools
from notion import create_idea, create_task
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_SPEECH_API_KEY = os.getenv("GOOGLE_SPEECH_API_KEY")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

SAVE_DIR = "saved_voice"
os.makedirs(SAVE_DIR, exist_ok=True)

app = Flask(__name__)

# ================== Telegram Bot ==================
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name or "unknown_user"
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{user}_{timestamp}.ogg"
    filepath = os.path.join(SAVE_DIR, filename)
    await file.download_to_drive(custom_path=filepath)
    print(f"✅ Saved voice file: {filepath}")

    message = convert_ogg_to_text(filepath)
    save_message(message, filepath)
    await update.message.reply_text(message)

application.add_handler(MessageHandler(filters.VOICE, voice_handler))

# ================== Webhook ==================
@app.route("/telegram", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        import asyncio
        asyncio.run(application.process_update(update))
    except Exception as e:
        with open("log.txt", "a") as f:
            f.write(f"{datetime.now()} - Exception: {e}\n")
        return "Internal Server Error", 500
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "Flask + Telegram webhook running!"

# ================== 工具函数 ==================
def convert_ogg_to_text(filepath):
    api_key = GOOGLE_SPEECH_API_KEY
    with open(filepath, "rb") as audio_file:
        audio_content = base64.b64encode(audio_file.read()).decode("utf-8")
    url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "config": {
            "encoding": "OGG_OPUS",
            "sampleRateHertz": 48000,
            "languageCode": "zh-CN",
            "enableAutomaticPunctuation": True,
        },
        "audio": {"content": audio_content},
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        result = response.json()
        if "results" in result:
            return result["results"][0]["alternatives"][0]["transcript"]
    return "无法识别语音"

def save_message(text, filepath):
    strUrl = google_drive_tools.upload_file(filepath)
    if text.startswith("灵感"):
        create_idea(content=text[2:], ptype="灵感", strUrl=strUrl, create_date=datetime.today().strftime('%Y-%m-%d'))
    elif text.startswith("任务"):
        create_task(name=text[2:], status="Not Started", strUrl=strUrl)
    else:
        create_idea(content=text, ptype="未识别", strUrl=strUrl, create_date=datetime.today().strftime('%Y-%m-%d'))

# ================== Flask 启动 ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
