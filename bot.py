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
from pydub import AudioSegment

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_SPEECH_API_KEY = os.getenv("GOOGLE_SPEECH_API_KEY")
BAIDU_API_KEY = os.getenv("BAIDU_API_KEY")
BAIDU_SECRET_KEY = os.getenv("BAIDU_SECRET_KEY")

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
    main_convert_ogg_to_text_baidu(filepath)
    
def main_convert_ogg_to_text_google(filepath):
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
    else:
        try:
            error_info = resp.json().get("error", {})
            code = error_info.get("code", resp.status_code)
            message = error_info.get("message", "Unknown error")
            status = error_info.get("status", "")
            return f"识别失败 [{code} - {status}]：{message}"
        except Exception as e:
            # 如果返回不是 JSON
            return f"识别失败 {resp.status_code}：无法解析错误信息 ({e}) - 原始返回: {resp.text}"

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

# 百度语音转文字服务
def main_convert_ogg_to_text_baidu(filepath):
    # ========== Step 0: 用户参数 ==========
    API_KEY = BAIDU_API_KEY
    SECRET_KEY = BAIDU_SECRET_KEY
    OGG_FILE = filepath
    WAV_FILE = 'voice.wav'

    # 转换音频
    convert_ogg_to_wav_baidu(OGG_FILE, WAV_FILE)

    # 获取token
    token = get_token_baidu(API_KEY, SECRET_KEY)

    # 调用识别接口
    result = recognize_baidu(WAV_FILE, token)

    # 输出结果
    if result.get("err_no") == 0:
        print("识别结果：", result["result"][0])
    else:
        print("识别失败：", result)

    # 可选：删除中间文件
    os.remove(WAV_FILE)


# ========== Step 1: 转换 OGG 到 WAV ==========
def convert_ogg_to_wav_baidu(ogg_path, wav_path):
    audio = AudioSegment.from_ogg(ogg_path)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)  # 16kHz, mono, 16bit
    audio.export(wav_path, format='wav')


# ========== Step 2: 获取 access_token ==========
def get_token_baidu(api_key, secret_key):
    token_url = 'https://openapi.baidu.com/oauth/2.0/token'
    params = {
        'grant_type': 'client_credentials',
        'client_id': api_key,
        'client_secret': secret_key
    }
    res = requests.get(token_url, params=params)
    return res.json().get("access_token")


# ========== Step 3: 调用百度语音识别 API ==========
def recognize_baidu(wav_path, token):
    with open(wav_path, 'rb') as f:
        speech_data = f.read()

    speech_base64 = base64.b64encode(speech_data).decode('utf-8')
    length = len(speech_data)

    data = {
        "format": "wav",
        "rate": 16000,
        "channel": 1,
        "cuid": "telegram-bot-device",
        "token": token,
        "speech": speech_base64,
        "len": length,
        "dev_pid": 1537  # 普通话输入法模型
    }

    url = "https://vop.baidu.com/server_api"
    headers = {"Content-Type": "application/json"}
    res = requests.post(url, headers=headers, data=json.dumps(data))
    return res.json()



if __name__ == "__main__":
    main()
