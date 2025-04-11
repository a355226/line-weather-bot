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

# === 暫存 user_id ===
user_ids = set()

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_ids.add(event.source.user_id)
    user_msg = event.message.text.strip()

    if user_msg == "天氣":
        reply = get_all_weather()
    else:
        reply = (
            "✅ 歡迎使用天氣提醒機器人 ☁\n"
            "──────────────\n"
            "🔔 功能介紹：\n"
            "1️⃣ 輸入『天氣』，查詢台北與新北的今明天氣與本週天氣概況\n"
            "💡 查詢後請稍候約 1~2 分鐘，資料會自動回覆\n"
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

# === 主功能：回傳完整資訊 ===
def get_all_weather():
    result = []
    for loc in locations:
        result.append(get_weather(loc, 0))  # 今日
        result.append(get_weather(loc, 1))  # 明日
    result.append(get_weekly_summary())
    return "\n\n".join(result)

# === 查詢單日天氣（含建議） ===
def get_weather(location, day_index):
    try:
        url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={cwb_api_key}&locationName={location}'
        res = requests.get(url)
        data = res.json()
        weather_elements = data['records']['location'][0]['weatherElement']

        wx = weather_elements[0]['time'][day_index]['parameter']['parameterName']
        pop = int(weather_elements[1]['time'][day_index]['parameter']['parameterName'])
        min_t = int(weather_elements[2]['time'][day_index]['parameter']['parameterName'])
        max_t = int(weather_elements[4]['time'][day_index]['parameter']['parameterName'])

        base_date = datetime.now() + timedelta(days=day_index)
        roc_date = f"{base_date.year - 1911}/{base_date.month}/{base_date.day}"

        return (
            f"📍 {location} {roc_date}\n"
            f"天氣：{wx}\n"
            f"氣溫：{min_t}°C - {max_t}°C\n"
            f"降雨機率：{pop}%\n"
            f"建議：{suggest(pop, min_t)}"
        )
    except Exception as e:
        print("get_weather error:", e)
        return f"{location} 天氣資料取得失敗"

# === 建議判斷 ===
def suggest(pop, min_temp):
    msg = []
    if pop > 70:
        msg.append("☔ 降雨明顯，建議穿防水外套並攜帶雨具")
    elif pop > 40:
        msg.append("🌂 雨勢可能偏大，建議攜帶雨具")
    elif pop > 10:
        msg.append("🌦 有短暫陣雨機率，建議備傘以防萬一")
    else:
        msg.append("🌤 降雨機率低，天氣良好，無需攜帶雨具")

    if min_temp < 22:
        msg.append("🧥 氣溫偏涼，請適時穿搭保暖")

    return "、".join(msg)

# === 一週天氣分析與概況 ===
def get_weekly_summary():
    try:
        url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-089?Authorization={cwb_api_key}&locationName=臺北市'
        res = requests.get(url)
        data = res.json()
        elements = data['records']['locations'][0]['location'][0]['weatherElement']
        wx_values = [e['elementValue'][0]['value'] for e in elements if e['elementName'] == 'Wx'][0:7]
        pop_values = [int(e['elementValue'][0]['value']) for e in elements if e['elementName'] == 'PoP6h'][0:14]
        tmin_values = [int(e['elementValue'][0]['value']) for e in elements if e['elementName'] == 'MinT'][0:7]
        tmax_values = [int(e['elementValue'][0]['value']) for e in elements if e['elementName'] == 'MaxT'][0:7]

        today = datetime.now()
        end = today + timedelta(days=6)
        roc_range = f"{today.year - 1911}/{today.month}/{today.day} ~ {end.year - 1911}/{end.month}/{end.day}"

        avg_pop = sum(pop_values) / len(pop_values)
        avg_min = sum(tmin_values) / len(tmin_values)

        if avg_pop > 70:
            summary = "本週雨勢偏大，記得隨身攜帶雨具，出門注意安全"
        elif avg_pop > 40:
            summary = "本週易有局部陣雨，建議備傘以防突雨"
        elif avg_pop > 10:
            summary = "偶有短暫降雨，晴雨參半，攜帶輕便雨具較安心"
        else:
            summary = "天氣整體穩定，多為晴朗或多雲，是出遊好時機"

        if avg_min < 20:
            summary += "，早晚偏涼，記得穿暖一點喔"

        return f"📅 雙北本週天氣概況（{roc_range}）\n{summary}"

    except Exception as e:
        print("get_weekly_summary error:", e)
        return "📅 雙北本週天氣概況：資料讀取失敗"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
