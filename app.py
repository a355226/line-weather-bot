from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import requests
import os
from apscheduler.schedulers.background import BackgroundScheduler

# === 設定 ===
app = Flask(__name__)

channel_access_token = 'yRDHUt2i8Pg2uvOvPTVj9Mvg55FJYxPu562/d1JFcEOecGz3zbfn9pCJz9el41z1iSfdd0+pGDbGc82Ki++Y6WgiIrdBHb4l1TDo24fS85NIKkkrJVP2c9yk1BNOR08nvi5UlGb1ICaKcdjWIKlSxQdB04t89/1O/w1cDnyilFU='
channel_secret = 'bf209d4d55be8865f7a5ba2522665811'
cwb_api_key = 'CWA-A2775CB4-B52C-47CE-8943-9570AE61D448'
locations = ['臺北市', '新北市']

configuration = Configuration(access_token=channel_access_token)
handler = WebhookHandler(channel_secret)

@app.route("/", methods=['GET'])
def home():
    return "Line Bot is running"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except Exception as e:
        print("Webhook error:", e)
        abort(400)
    return 'OK'

# === 暫存 user_id
user_ids = set()

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_ids.add(event.source.user_id)
    user_msg = event.message.text.strip()

    if user_msg == "天氣":
        reply = get_today_tomorrow_weather()
    else:
        reply = (
            "✅ 歡迎使用天氣提醒機器人 ☁\n"
            "──────────────\n"
            "🔔 功能介紹：\n"
            "1️⃣ 每晚21:00 自動提醒 【台北市】 和 【新北市】 的明日天氣\n"
            "2️⃣ 隨時輸入『天氣』，查詢今明兩天天氣\n"
            "──────────────\n"
            "💡 試試輸入：天氣"
        )

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )

# === 查詢今明天氣

def get_today_tomorrow_weather():
    msgs = []
    for loc in locations:
        msgs.append(get_weather(loc, 0))  # 今日
        msgs.append(get_weather(loc, 1))  # 明日
    return "\n\n".join(msgs)

# === 取得天氣

def get_weather(location, day_index):
    url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={cwb_api_key}&locationName={location}'
    res = requests.get(url)
    data = res.json()
    weather_elements = data['records']['location'][0]['weatherElement']

    wx = weather_elements[0]['time'][day_index]['parameter']['parameterName']
    pop = weather_elements[1]['time'][day_index]['parameter']['parameterName']
    min_t = weather_elements[2]['time'][day_index]['parameter']['parameterName']
    max_t = weather_elements[4]['time'][day_index]['parameter']['parameterName']

    day = "今日" if day_index == 0 else "明日"

    message = f"【{location} {day}】\n天氣：{wx}\n氣溫：{min_t}°C - {max_t}°C\n降雨機率：{pop}%\n建議：{suggest(int(pop), int(min_t))}"
    return message

# === 建議文字

def suggest(pop, min_temp):
    msg = []
    if pop > 10:
        msg.append("降雨機率超過 10%，記得帶傘 ☔")
    if min_temp < 22:
        msg.append("氣溫偏低，記得穿外套 🧥")
    if not msg:
        msg.append("天氣良好，無需特別準備 ☀")
    return " ".join(msg)

# === 定時推播 ===

def job():
    messages = []
    for loc in locations:
        messages.append(get_weather(loc, 1))
    final_message = "\n\n".join(messages)
    print("定時推播：\n" + final_message)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        for uid in user_ids:
            line_bot_api.push_message(
                PushMessageRequest(
                    to=uid,
                    messages=[TextMessage(text=final_message)]
                )
            )

# === 排程 每天21:00 ===
scheduler = BackgroundScheduler()
scheduler.add_job(job, 'cron', hour=21, minute=0)
scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
