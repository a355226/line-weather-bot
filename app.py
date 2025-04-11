from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

channel_access_token = 'yRDHUt2i8Pg2uvOvPTVj9Mvg55FJYxPu562/d1JFcEOecGz3zbfn9pCJz9el41z1iSfdd0+pGDbGc82Ki++Y6WgiIrdBHb4l1TDo24fS85NIKkkrJVP2c9yk1BNOR08nvi5UlGb1ICaKcdjWIKlSxQdB04t89/1O/w1cDnyilFU='
channel_secret = 'bf209d4d55be8865f7a5ba2522665811'
cwb_api_key = 'CWA-A2775CB4-B52C-47CE-8943-9570AE61D448'
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
        reply = get_today_tomorrow_weather() + "\n\n" + get_week_summary()
    else:
        reply = (
            "✅ 歡迎使用天氣提醒機器人 ☁\n"
            "──────────────\n"
            "🔔 功能介紹：\n"
            "輸入『天氣』查詢今明天氣與本週天氣概況\n"
            "📌 查詢後請稍候1-2分鐘接收完整回覆\n"
            "──────────────\n"
            "💡 試試輸入：天氣"
        )

    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )

def get_today_tomorrow_weather():
    locations = ['臺北市', '新北市']
    result = ""
    for loc in locations:
        result += f"【{loc}】\n"
        for i in [0, 1]:
            result += get_weather(loc, i) + "\n"
        result += "\n"
    return result.strip()

def get_weather(location, day_index):
    url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={cwb_api_key}&locationName={location}'
    try:
        res = requests.get(url)
        data = res.json()
        weather = data['records']['location'][0]['weatherElement']
        wx = weather[0]['time'][day_index]['parameter']['parameterName']
        pop = int(weather[1]['time'][day_index]['parameter']['parameterName'])
        min_t = int(weather[2]['time'][day_index]['parameter']['parameterName'])
        max_t = int(weather[4]['time'][day_index]['parameter']['parameterName'])
        date_str = weather[0]['time'][day_index]['startTime'][:10]
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        roc_date = f"{dt.year - 1911}/{dt.month}/{dt.day}"
        rain_msg = "☔ 有備無患" if pop > 50 else "🌂 可攜帶摺傘" if pop > 10 else "☀ 無雨預期"
        temp_msg = "🧥 請留意保暖" if min_t < 22 else "👕 穿著輕便"
        return f"{roc_date}：{wx}，{min_t}-{max_t}°C，降雨 {pop}%\n建議：{rain_msg}，{temp_msg}"
    except:
        return f"{location} 天氣資料讀取失敗"

def get_week_summary():
    url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-091?Authorization={cwb_api_key}&locationName=臺北市'
    try:
        res = requests.get(url)
        data = res.json()
        wxs = data['records']['locations'][0]['location'][0]['weatherElement'][0]['time'][:7]
        pops = data['records']['locations'][0]['location'][0]['weatherElement'][1]['time'][:7]
        temps = data['records']['locations'][0]['location'][0]['weatherElement'][2]['time'][:7]

        rain_days = [int(p['elementValue'][0]['value']) > 40 for p in pops]
        sunny_days = ["晴" in w['elementValue'][0]['value'] for w in wxs]
        max_temps = [int(t['elementValue'][0]['value']) for t in temps]
        min_temps = [int(t['elementValue'][1]['value']) for t in temps]

        start = datetime.strptime(wxs[0]['startTime'][:10], "%Y-%m-%d")
        end = datetime.strptime(wxs[-1]['endTime'][:10], "%Y-%m-%d")
        date_range = f"{start.year - 1911}/{start.month}/{start.day}~{end.year - 1911}/{end.month}/{end.day}"

        summary = ""
        if all(rain_days):
            summary = "整週陰雨綿綿，出門請務必攜帶雨具 ☔"
        elif all(sunny_days):
            summary = "本週陽光普照，是外出踏青的好時機 ☀"
        elif sum(rain_days) >= 4:
            summary = "雨天偏多，建議以室內行程為主，雨具請備齊。"
        elif max(max_temps) > 30:
            summary = "本週白天溫度偏高，戶外活動請注意防曬與水分補充 🌞"
        elif min(min_temps) < 18:
            summary = "早晚溫差大，記得攜帶外套保暖 🧥"
        else:
            summary = "天氣變化較大，晴雨交替，請彈性安排行程。"

        return f"──────────────\n📆 雙北本週天氣概況（{date_range}）\n{summary}"
    except:
        return "──────────────\n📆 雙北本週天氣概況\n⚠ 無法取得資料，請稍後再試。"
