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

    if user_msg == "天氣":
        reply = get_today_tomorrow_weather() + "\n\n" + get_week_summary()
    else:
        reply = (
            "✅ 歡迎使用天氣提醒機器人 ☁\n"
            "──────────────\n"
            "🔔 功能介紹：\n"
            "1️⃣ 隨時輸入『天氣』即可查詢今明天氣與本週概況\n"
            "📌 資料讀取後約需 1~2 分鐘才會顯示，請耐心等待喔！\n"
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
    msg = []
    today = datetime.today()
    for loc in locations:
        line = f"【{loc}】"
        line += "\n" + get_weather(loc, 0, today)
        line += "\n" + get_weather(loc, 1, today + timedelta(days=1))
        msg.append(line)
    return "\n\n".join(msg)

def get_weather(location, day_index, date_obj):
    try:
        res = requests.get(
            f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={cwb_api_key}&locationName={location}'
        )
        data = res.json()
        if not data['records']['location']:
            return f"{location} 資料讀取失敗，可能暫時沒有天氣資料喔。"

        weather_elements = data['records']['location'][0]['weatherElement']

        wx = weather_elements[0]['time'][day_index]['parameter']['parameterName']
        pop = int(weather_elements[1]['time'][day_index]['parameter']['parameterName'])
        min_t = int(weather_elements[2]['time'][day_index]['parameter']['parameterName'])
        max_t = int(weather_elements[4]['time'][day_index]['parameter']['parameterName'])
        date_str = f"{date_obj.year - 1911}/{date_obj.month}/{date_obj.day}"

        rain_level = "☁ 小雨可能" if 10 < pop <= 30 else "🌧 有雨機率高" if pop > 30 else "☀ 幾乎不下雨"

        suggestion = []
        if pop > 10:
            suggestion.append("記得帶傘 ☔")
        if min_t < 22:
            suggestion.append("早晚偏涼，建議加件外套 🧥")
        if not suggestion:
            suggestion.append("天氣舒適，適合出門活動 🌤")

        return f"{date_str}（{'今日' if day_index==0 else '明日'}）\n天氣：{wx}  氣溫：{min_t}-{max_t}°C\n降雨：{pop}%（{rain_level}）\n貼心提醒：{'、'.join(suggestion)}"
    except Exception as e:
        return f"{location} 天氣資料讀取錯誤：{e}"

def get_week_summary():
    try:
        res = requests.get(
            f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-091?Authorization={cwb_api_key}&locationName=臺北市'
        )
        data = res.json()
        times = data['records']['locations'][0]['location'][0]['weatherElement'][0]['time']

        summary_text = analyze_week_weather(times)
        start = datetime.strptime(times[0]['startTime'], "%Y-%m-%dT%H:%M:%S+08:00")
        end = datetime.strptime(times[-1]['endTime'], "%Y-%m-%dT%H:%M:%S+08:00")
        date_range = f"{start.year - 1911}/{start.month}/{start.day}~{end.year - 1911}/{end.month}/{end.day}"

        return f"\n\n📅 雙北本週天氣概況（{date_range}）\n{summary_text}"
    except Exception as e:
        return "\n\n⚠️ 取得一週天氣資料失敗，請稍後再試"

def analyze_week_weather(times):
    rainy_days = 0
    sunny_days = 0
    unstable_days = 0
    temp_low = 99
    temp_high = -99

    for t in times:
        wx = t['elementValue'][0]['value']
        if any(x in wx for x in ['雷', '雨', '陣']):
            rainy_days += 1
        elif any(x in wx for x in ['晴', '多雲']):
            sunny_days += 1
        else:
            unstable_days += 1

        try:
            low = int(t['elementValue'][1]['value'])
            high = int(t['elementValue'][2]['value'])
            temp_low = min(temp_low, low)
            temp_high = max(temp_high, high)
        except:
            pass

    if rainy_days >= 5:
        return f"本週降雨偏多，建議攜帶雨具 🌧 氣溫約 {temp_low}~{temp_high}°C。"
    elif sunny_days >= 5:
        return f"本週大致晴朗 ☀ 氣溫介於 {temp_low}~{temp_high}°C，適合外出活動。"
    elif unstable_days >= 3:
        return f"天氣多變，有時晴時雨，請多注意氣象變化 🌦，氣溫 {temp_low}~{temp_high}°C。"
    else:
        return f"天氣普通，偶有短暫雨或陽光 ☁，氣溫落在 {temp_low}~{temp_high}°C。"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
