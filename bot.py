import os
import json
import base64
import logging
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from notion import create_idea, create_task
import google_drive_tools
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_SPEECH_API_KEY = os.getenv("GOOGLE_SPEECH_API_KEY")

SAVE_DIR = "saved_voice"
OGG_FILE_URL_ROOT = "https://simplechen.xyz/voices/"
os.makedirs(SAVE_DIR, exist_ok=True)

# 日志
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ---------------- 工具函数 ----------------
def convert_ogg_to_text(filepath):
    api_key = GOOGLE_SPEECH_API_KEY
    with open(filepath, "rb") as f:
        audio_content = base64.b64encode(f.read()).decode("utf-8")

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

    resp = requests.post(url, headers=headers, data=json.dumps(data))
    if resp.status_code == 200:
        result = resp.json()
        if "results" in result:
            return result["results"][0]["alternatives"][0]["transcript"]
    return "未识别内容" + str(resp.status_code)

def save_message(text, filepath):
    # strUrl = google_drive_tools.upload_file(filepath)
    strUrl = filepath
    if text.startswith("灵感"):
        create_idea(content=text[2:], ptype="灵感", strUrl=strUrl,
                    create_date=datetime.today().strftime('%Y-%m-%d'))
    elif text.startswith("任务"):
        create_task(name=text[2:], status="Not Started", strUrl=strUrl)
    else:
        create_idea(content=text, ptype="未识别", strUrl=strUrl,
                    create_date=datetime.today().strftime('%Y-%m-%d'))

# ---------------- Telegram Handler ----------------
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user.first_name or "unknown_user"
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{user}_{timestamp}.ogg"
        filepath = os.path.join(SAVE_DIR, filename)

        await file.download_to_drive(custom_path=filepath)
        logging.info(f"已保存语音文件: {filepath}")

        message = convert_ogg_to_text(filepath)
        save_message(message, OGG_FILE_URL_ROOT + filename)
        await update.message.reply_text(message)
    except Exception as e:
        logging.error(f"voice_handler error: {e}")

# ---------------- 启动 Bot ----------------
def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.VOICE, voice_handler))

    WEBHOOK_URL = "https://simplechen.xyz/telegram"  # 替换成你的域名

    # run_webhook 是同步方法，会阻塞
    application.run_webhook(
        listen="0.0.0.0",
        port=5000,
        url_path="telegram",
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    main()
