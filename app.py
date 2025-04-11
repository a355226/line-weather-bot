from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import requests
import os
from datetime import datetime, timedelta

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

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_msg = event.message.text.strip()
    print("收到來自用戶：", event.source.user_id)

    if user_msg == "天氣":
        reply = get_today_tomorrow_weather()
    else:
        reply = (
            "✅ 歡迎使用天氣提醒機器人 ☁\n"
            "──────────────\n"
            "🔔 功能介紹：\n"
            "1️⃣ 輸入『天氣』即可查詢今明天氣資訊\n"
            "2️⃣ 回應結果約需 1~2 分鐘，請耐心稍候 🌈\n"
            "──────────────\n"
            "💡 快試試輸入：天氣"
        )

    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )

def get_today_tomorrow_weather():
    msgs = []
    for idx, label in enumerate(["今日", "明日"]):
        date = (datetime.now() + timedelta(days=idx)).strftime("%Y/%-m/%-d")
        for loc in locations:
            msgs.append(get_weather(loc, idx, label, date))
    return "\n\n".join(msgs)

def get_weather(location, day_index, label, date):
    url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={cwb_api_key}&locationName={location}'
    res = requests.get(url)
    data = res.json()
    weather_elements = data['records']['location'][0]['weatherElement']

    wx = weather_elements[0]['time'][day_index]['parameter']['parameterName']
    pop = int(weather_elements[1]['time'][day_index]['parameter']['parameterName'])
    min_t = int(weather_elements[2]['time'][day_index]['parameter']['parameterName'])
    max_t = int(weather_elements[4]['time'][day_index]['parameter']['parameterName'])

    rain_desc = "☀ 幾乎不會下雨"
    if pop >= 70:
        rain_desc = "⛈ 有明顯降雨，記得帶傘與防水裝備"
    elif pop >= 30:
        rain_desc = "🌧 有機會下雨，建議攜帶折傘"
    elif pop > 10:
        rain_desc = "🌂 降雨機率稍高，可攜帶輕便雨具"

    temp_tip = "🧥 今晚偏涼，記得穿外套" if min_t < 22 else "👕 氣溫舒適，穿著輕便即可"

    return f"【{location} {label}（{convert_to_roc(date)}）】\n天氣：{wx}\n氣溫：{min_t}°C - {max_t}°C\n降雨機率：{pop}%\n{rain_desc}，{temp_tip}"

def convert_to_roc(date_str):
    parts = date_str.split('/')
    roc_year = int(parts[0]) - 1911
    return f"{roc_year}/{parts[1]}/{parts[2]}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
