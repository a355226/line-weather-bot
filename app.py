from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, ReplyMessageRequest, TextMessage
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
            "1️⃣ 隨時輸入『天氣』，查詢今明兩天的雙北天氣與本週概況\n"
            "💡 查詢後請稍待 1~2 分鐘，如遇資料延遲敬請見諒\n"
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
    msgs = []
    for loc in locations:
        msgs.append(get_weather(loc, 0))
        msgs.append(get_weather(loc, 1))
    msgs.append(get_weekly_summary())
    return "\n\n".join(msgs)

# === 取得天氣 ===
def get_weather(location, day_index):
    url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={cwb_api_key}&locationName={location}'
    res = requests.get(url)
    data = res.json()
    weather_elements = data['records']['location'][0]['weatherElement']

    wx = weather_elements[0]['time'][day_index]['parameter']['parameterName']
    pop = weather_elements[1]['time'][day_index]['parameter']['parameterName']
    min_t = weather_elements[2]['time'][day_index]['parameter']['parameterName']
    max_t = weather_elements[4]['time'][day_index]['parameter']['parameterName']

    day = datetime.today() + timedelta(days=day_index)
    roc_date = f"{day.year - 1911}/{day.month}/{day.day}"

    message = f"【{location} {roc_date}】\n天氣：{wx}\n氣溫：{min_t}°C - {max_t}°C\n降雨機率：{pop}%\n建議：{suggest(int(pop), int(min_t))}"
    return message

# === 建議文字 ===
def suggest(pop, min_temp):
    msg = []
    if pop > 10:
        msg.append("降雨機率超過 10%，記得帶傘 ☔")
    if min_temp < 22:
        msg.append("氣溫偏低，記得穿外套 🧥")
    if not msg:
        msg.append("天氣良好，無需特別準備 ☀")
    return " ".join(msg)

# === 雙北本週概況 ===
def get_weekly_summary():
    try:
        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-063?Authorization={cwb_api_key}&locationName=臺北市"
        res = requests.get(url)
        data = res.json()
        times = data['records']['locations'][0]['location'][0]['weatherElement'][1]['time']

        summary = ""
        rainy_days = 0
        hot_days = 0
        cold_days = 0
        unstable_days = 0

        for t in times[:14]:
            pop = int(t['elementValue'][0]['value'])
            temp = int(t['elementValue'][1]['value'])

            if pop >= 70:
                rainy_days += 1
            elif pop >= 40:
                unstable_days += 1

            if temp >= 30:
                hot_days += 1
            elif temp < 18:
                cold_days += 1

        if rainy_days >= 5:
            summary = "本週雙北經常有雨，記得隨身帶傘☔，外出建議穿著防水衣物。"
        elif rainy_days >= 3:
            summary = "這週雙北常會有雨，尤其幾天降雨機率較高，建議隨身攜帶雨具。"
        elif unstable_days >= 4:
            summary = "本週天氣多變，午後陣雨機率高，記得查看即時天氣。"
        elif hot_days >= 4:
            summary = "雙北本週多為晴朗高溫天氣，建議外出注意防曬與補水☀。"
        elif cold_days >= 3:
            summary = "本週天氣偏涼，記得穿上保暖外套🧥，避免著涼。"
        else:
            summary = "這週雙北天氣普遍穩定，降雨少，適合外出活動。"

        today = datetime.today()
        end_day = today + timedelta(days=6)
        roc_range = f"{today.year - 1911}/{today.month}/{today.day}~{end_day.year - 1911}/{end_day.month}/{end_day.day}"

        return f"\n\n☁ 雙北本週天氣概況（{roc_range}）：\n{summary}"
    except Exception as e:
        print("週天氣資料錯誤：", e)
        return "\n\n⚠ 無法取得雙北本週天氣概況。"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
