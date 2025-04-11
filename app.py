from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import requests
import os
import datetime

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
            "1️⃣ 輸入『天氣』查詢臺北市與新北市的今明天氣\n"
            "2️⃣ 回覆將包含貼心穿搭建議與本週概況分析\n"
            "⚠️ 查詢後請稍待 1～2 分鐘，若稍後無回覆可重試\n"
            "──────────────"
        )

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )

def get_today_tomorrow_weather():
    reply = []
    today = get_weather('臺北市', 0)
    tomorrow = get_weather('臺北市', 1)
    if '資料讀取失敗' in today or '資料讀取失敗' in tomorrow:
        return "⚠️ 找不到中央氣象局天氣資料，請稍後再試。"

    reply.append("【臺北市】")
    reply.append(today)
    reply.append(tomorrow)
    reply.append("\n【新北市】")
    reply.append(get_weather('新北市', 0))
    reply.append(get_weather('新北市', 1))
    reply.append(get_week_summary('臺北市'))
    return "\n\n".join(reply)

def get_weather(location, day_index):
    try:
        print("📍 查詢地區：", location)
        url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={cwb_api_key}&locationName={location}'
        res = requests.get(url)
        data = res.json()
        weather = data['records']['location'][0]['weatherElement']
        wx = weather[0]['time'][day_index]['parameter']['parameterName']
        pop = int(weather[1]['time'][day_index]['parameter']['parameterName'])
        min_t = int(weather[2]['time'][day_index]['parameter']['parameterName'])
        max_t = int(weather[4]['time'][day_index]['parameter']['parameterName'])
        date = datetime.datetime.strptime(weather[0]['time'][day_index]['startTime'][:10], '%Y-%m-%d')
        roc_date = f"{date.year - 1911}/{date.month}/{date.day}"
        suggestion = []
        if pop > 80:
            suggestion.append("🌧 可能有豪大雨，記得帶傘與雨衣")
        elif pop > 50:
            suggestion.append("☂ 有明顯降雨機會，外出請帶傘")
        elif pop > 10:
            suggestion.append("🌦 有短暫降雨可能，可備雨具")
        else:
            suggestion.append("🌤 幾乎無雨，放心出門")
        if min_t < 22:
            suggestion.append("🧥 天氣偏涼，建議加件外套")
        return f"{roc_date} 天氣：{wx}，氣溫：{min_t}°C~{max_t}°C，降雨：{pop}%\n建議：{'、'.join(suggestion)}"
    except Exception as e:
        print("❗ 錯誤：", e)
        print("❗ 原始回應：", res.text)
        return "⚠️ 天氣資料讀取失敗"

def get_week_summary(location):
    try:
        url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-091?Authorization={cwb_api_key}&locationName={location}'
        res = requests.get(url)
        data = res.json()
        elements = data['records']['locations'][0]['location'][0]['weatherElement']
        pops = [int(t['value']) for t in elements[1]['time'][:7]]  # PoP12h
        wxs = [t['value'] for t in elements[0]['time'][:7]]  # Wx

        start = datetime.datetime.strptime(elements[0]['time'][0]['startTime'][:10], '%Y-%m-%d')
        end = datetime.datetime.strptime(elements[0]['time'][6]['endTime'][:10], '%Y-%m-%d')
        start_roc = f"{start.year - 1911}/{start.month}/{start.day}"
        end_roc = f"{end.year - 1911}/{end.month}/{end.day}"

        avg_pop = sum(pops) / len(pops)
        rain_days = sum(1 for p in pops if p > 40)

        summary = "☁ 【雙北本週天氣概況】 ({}~{})\n".format(start_roc, end_roc)

        if avg_pop > 80:
            summary += "整週雨勢明顯，請務必攜帶雨具並注意天氣變化。"
        elif rain_days >= 5:
            summary += "多雨的一週，外出請隨身攜傘與雨衣。"
        elif rain_days >= 3:
            summary += "部分時間可能降雨，週末前後要注意變天。"
        elif all('晴' in w or '多雲' in w for w in wxs):
            summary += "本週大致晴朗，適合出遊與曬衣服。"
        elif '雷' in ''.join(wxs):
            summary += "週內有機會出現雷陣雨，請注意午後天氣變化。"
        elif avg_pop < 20:
            summary += "本週為穩定晴朗天氣，可放心安排戶外活動。"
        else:
            summary += "本週天氣變化不大，偶有短暫降雨。"

        return summary
    except Exception as e:
        print("❗ 一週概況錯誤：", e)
        print("❗ 原始回應：", res.text)
        return "\n⚠️ 本週天氣概況資料讀取失敗"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
