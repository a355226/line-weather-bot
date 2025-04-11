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
configuration = Configuration(access_token=channel_access_token)
handler = WebhookHandler(channel_secret)
locations = ['臺北市', '新北市']

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
        try:
            reply = get_today_tomorrow_weather() + "\n\n" + get_week_summary()
        except:
            reply = "資料讀取失敗，請稍後再試～"
    else:
        reply = (
            "🌤 歡迎使用雙北天氣機器人 ☁️\n"
            "輸入「天氣」查詢今明預報及雙北一週天氣概況！\n"
            "⚠️ 傳送後請稍待 1～2 分鐘取得最新資料。"
        )

    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply)]
            )
        )

# === 天氣查詢主體 ===

def get_today_tomorrow_weather():
    msg = ""
    for loc in locations:
        data = fetch_weather_data(loc)
        msg += f"【{loc}】\n"
        for i in [0, 1]:
            date = parse_civil_date(data['records']['location'][0]['weatherElement'][0]['time'][i]['startTime'])
            wx = data['records']['location'][0]['weatherElement'][0]['time'][i]['parameter']['parameterName']
            pop = int(data['records']['location'][0]['weatherElement'][1]['time'][i]['parameter']['parameterName'])
            min_t = int(data['records']['location'][0]['weatherElement'][2]['time'][i]['parameter']['parameterName'])
            max_t = int(data['records']['location'][0]['weatherElement'][4]['time'][i]['parameter']['parameterName'])
            suggest = build_suggestion(pop, min_t)
            label = "今日" if i == 0 else "明日"
            msg += f"{label}（{date}）\n☁ 天氣：{wx}\n🌡 氣溫：{min_t}-{max_t}°C\n☔ 降雨：{pop}%\n🧾 建議：{suggest}\n\n"
    return msg.strip()

def get_week_summary():
    try:
        url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-063?Authorization={cwb_api_key}&locationName=臺北市"
        data = requests.get(url).json()
        weathers = data['records']['locations'][0]['location'][0]['weatherElement']
        min_temps = [int(t['elementValue'][0]['value']) for t in weathers[8]['time']]
        max_temps = [int(t['elementValue'][1]['value']) for t in weathers[8]['time']]
        pops = [int(t['elementValue'][0]['value']) for t in weathers[0]['time']]
        wxs = [t['elementValue'][0]['value'] for t in weathers[6]['time']]

        avg_min = sum(min_temps) / len(min_temps)
        avg_max = sum(max_temps) / len(max_temps)
        avg_pop = sum(pops) / len(pops)
        date_start = parse_civil_date(weathers[0]['startTime'])
        date_end = parse_civil_date(weathers[0]['endTime'], days_offset=6)
        desc = classify_week_weather(avg_min, avg_max, avg_pop, wxs)
        return f"📅 雙北本週天氣概況（{date_start}～{date_end}）\n{desc}"
    except:
        return "⚠️ 本週天氣概況暫時無法取得～"

# === 工具函數 ===

def fetch_weather_data(location):
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={cwb_api_key}&locationName={location}"
    return requests.get(url).json()

def parse_civil_date(dt_str, days_offset=0):
    dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S") + timedelta(days=days_offset)
    roc_year = dt.year - 1911
    return f"{roc_year}/{dt.month}/{dt.day}"

def build_suggestion(pop, min_t):
    tips = []
    if pop > 70:
        tips.append("降雨機率高，請務必帶傘 ☔")
    elif pop > 30:
        tips.append("可能會下雨，建議攜帶雨具 ☂")
    if min_t < 18:
        tips.append("早晚偏冷，記得加件外套 🧥")
    elif min_t < 22:
        tips.append("氣溫偏涼，建議穿長袖或外套 🧣")
    if not tips:
        tips.append("天氣穩定，輕便出門最適合 ☀")
    return "、".join(tips)

def classify_week_weather(min_t, max_t, avg_pop, wxs):
    rain_days = sum(1 for w in wxs if "雨" in w)
    result = []

    # 依據降雨天數
    if rain_days >= 6:
        result.append("幾乎天天下雨，外出請準備好雨具 ☔☁")
    elif rain_days >= 4:
        result.append("本週大多有雨，出門建議穿防水鞋或攜帶雨衣 ☔")
    elif rain_days >= 2:
        result.append("這週有幾天會下雨，請注意天氣變化 🧥☁")
    else:
        result.append("多為好天氣，適合戶外活動 ☀")

    # 平均降雨機率
    if avg_pop > 80:
        result.append("降雨機率高，記得隨身帶傘 ☔")
    elif avg_pop > 50:
        result.append("天氣不穩定，建議每天查看最新預報 ☁")
    elif avg_pop < 20:
        result.append("幾乎無雨，天氣穩定 ☀")

    # 氣溫狀況
    if max_t >= 34:
        result.append("天氣炎熱，出門防曬補水要做好 ☀🧴")
    elif min_t <= 15:
        result.append("清晨寒意明顯，建議早晚穿暖 🧤🧣")
    elif max_t - min_t >= 10:
        result.append("日夜溫差大，容易著涼要注意 🧥")

    # 額外綜合語氣
    if "雷" in "".join(wxs):
        result.append("偶有雷陣雨，外出活動請特別留意閃電風險 ⚡")
    elif any("晴" in w for w in wxs) and any("雨" in w for w in wxs):
        result.append("一週天氣變化大，晴雨交錯，出門建議多準備 ☀☁")

    return "\n".join(result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
