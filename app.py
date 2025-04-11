from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import requests
import os
import datetime

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

    if user_msg == "天氣":
        reply = get_today_tomorrow_weather()
    else:
        reply = (
            "✅ 歡迎使用天氣提醒機器人 ☁\n"
            "──────────────\n"
            "🔔 功能介紹：\n"
            "1️⃣ 輸入『天氣』查詢今明兩天台北與新北的天氣\n"
            "2️⃣ 查詢結果可能需要稍候 1-2 分鐘喔\n"
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

# === 查詢今明天氣 ===
def get_today_tomorrow_weather():
    msgs = ["✅ 你的天氣預報來囉～\n（以下為民國日期）"]
    for loc in locations:
        msgs.append(f"\n【{loc}】")
        msgs.append(get_weather(loc, 0))  # 今日
        msgs.append(get_weather(loc, 1))  # 明日
    return "\n\n".join(msgs)

# === 取得天氣資料 ===
def get_weather(location, day_index):
    url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={cwb_api_key}&locationName={location}'
    res = requests.get(url)
    data = res.json()
    weather_elements = data['records']['location'][0]['weatherElement']

    wx = weather_elements[0]['time'][day_index]['parameter']['parameterName']
    pop = int(weather_elements[1]['time'][day_index]['parameter']['parameterName'])
    min_t = int(weather_elements[2]['time'][day_index]['parameter']['parameterName'])
    max_t = int(weather_elements[4]['time'][day_index]['parameter']['parameterName'])

    today = datetime.datetime.today()
    target_date = today + datetime.timedelta(days=day_index)
    roc_date = f"{target_date.year - 1911}/{target_date.month}/{target_date.day}"

    suggestion = []
    if pop > 70:
        suggestion.append("🌧️ 明顯降雨，請備妥雨具")
    elif pop > 30:
        suggestion.append("☁️ 降雨機率偏高，可備輕便雨具")
    elif pop > 10:
        suggestion.append("🌦️ 可能有短暫小雨")
    else:
        suggestion.append("☀️ 天氣穩定無雨")

    if min_t < 22:
        suggestion.append("🧥 記得穿外套避免著涼")

    return f"📅 {roc_date}（{'今日' if day_index == 0 else '明日'}）\n🌤 天氣：{wx}\n🌡️ 氣溫：{min_t}°C - {max_t}°C\n🌧️ 降雨機率：{pop}%\n☂️ 建議：{'、'.join(suggestion)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
