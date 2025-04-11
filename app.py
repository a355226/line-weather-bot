from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import requests
import os
from datetime import datetime, timedelta
import json
from dateutil import parser

# === 設定 ===
app = Flask(__name__)
channel_access_token = 'yRDHUt2i8Pg2uvOvPTVj9Mvg55FJYxPu562/d1JFcEOecGz3zbfn9pCJz9el41z1iSfdd0+pGDbGc82Ki++Y6WgiIrdBHb4l1TDo24fS85NIKkkrJVP2c9yk1BNOR08nvi5UlGb1ICaKcdjWIKlSxQdB04t89/1O/w1cDnyilFU='
channel_secret = 'bf209d4d55be8865f7a5ba2522665811'
cwa_api_key = "CWA-A2775CB4-B52C-47CE-8943-9570AE61D448"
configuration = Configuration(access_token=channel_access_token)
handler = WebhookHandler(channel_secret)

locations = ['臺北市', '新北市']

@app.route("/", methods=['GET'])
def home():
    return "Line Bot is running"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    print("🟢 [Webhook 收到請求]")
    print("📦 [Webhook 原始訊息]：", body)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print("❌ [Webhook Exception]", str(e))
        print("📦 [Webhook Raw Body]：", body)
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    try:
        if getattr(event, "delivery_context", None) and event.delivery_context.is_redelivery:
            print("⚠️ [Redelivery] 舊訊息重送，不處理 reply")
            return

        print("🟢 [Webhook Triggered] 收到來自 LINE 的訊息事件")
        user_msg = event.message.text.strip()

        if user_msg == "天氣":
            part1 = ""
            part2 = ""
            try:
                print("🔍 [Debug] 使用者請求今明天氣", flush=True)
                part1 = get_today_tomorrow_weather()
                print("✅ [Debug] 今日與明日天氣取得成功", flush=True)
            except Exception as e1:
                print("❌ [Error] get_today_tomorrow_weather()：", str(e1), flush=True)
                part1 = "⚠️ 今明天氣資料無法取得。"

            try:
                print("🧪 [Debug] 開始處理 get_week_summary()", flush=True)
                part2 = get_week_summary()
                print("✅ [Debug] 一週天氣概況取得成功", flush=True)
            except Exception as e2:
                import traceback
                print("❌ [Error] get_week_summary()：", str(e2), flush=True)
                traceback.print_exc()
                part2 = "⚠️ 雙北本週天氣概況暫時無法取得。"

            reply = part1 + "\n\n" + part2

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

    except Exception as e:
        print("❌ [最終錯誤處理] handle_message 爆炸了！")
        print("📛 [錯誤內容]：", str(e))

# === 天氣查詢主體 ===

def get_today_tomorrow_weather():
    msg = ""
    for loc in locations:
        data = fetch_weather_data(loc)
        msg += f"【{loc}】\n"
        for i, label in zip([0, 2], ["今日", "明日"]):
            time_data = data['records']['location'][0]['weatherElement'][0]['time'][i]
            start_time = time_data['startTime']
            date = parse_civil_date(start_time)
            wx = time_data['parameter']['parameterName']
            pop = int(data['records']['location'][0]['weatherElement'][1]['time'][i]['parameter']['parameterName'])
            min_t = int(data['records']['location'][0]['weatherElement'][2]['time'][i]['parameter']['parameterName'])
            max_t = int(data['records']['location'][0]['weatherElement'][4]['time'][i]['parameter']['parameterName'])
            suggest = build_suggestion(pop, min_t)
            msg += f"{label}（{date}）\n☁ 天氣：{wx}\n🌡 氣溫：{min_t}-{max_t}°C\n☔ 降雨：{pop}%\n🧾 建議：{suggest}\n\n"
    return msg.strip()

def get_week_summary():
    print("🔍 [Debug] 呼叫中央氣象局 API 取得臺北市一週資料")
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-063?Authorization={cwa_api_key}&locationName=臺北市"
    response = requests.get(url)
    print(f"📦 [API] 回應狀態碼：{response.status_code}")
    data = response.json()

    elements = data['records']['Locations'][0]['Location'][0]['WeatherElement']
    available_names = [e['ElementName'] for e in elements]
    print("📄 [Debug] 可用欄位名稱：", available_names)

    wx_index = next(i for i, e in enumerate(elements) if '天氣現象' in e['ElementName'])
    pop_index = next(i for i, e in enumerate(elements) if '降雨機率' in e['ElementName'])
    min_index = next(i for i, e in enumerate(elements) if '最低溫度' in e['ElementName'])
    max_index = next(i for i, e in enumerate(elements) if '最高溫度' in e['ElementName'])
    uv_index = next(i for i, e in enumerate(elements) if '紫外線指數' in e['ElementName'])

    def extract_first_value(ev):
        try:
            return int(list(ev[0].values())[0])
        except:
            return 0

    def extract_str_value(ev):
        try:
            return list(ev[0].values())[0]
        except:
            return "?"

    min_temps = [extract_first_value(t['ElementValue']) for t in elements[min_index]['Time']]
    max_temps = [extract_first_value(t['ElementValue']) for t in elements[max_index]['Time']]
    pops = [extract_first_value(t['ElementValue']) for t in elements[pop_index]['Time']]
    wxs = [extract_str_value(t['ElementValue']) for t in elements[wx_index]['Time']]
    uv_indexes = [extract_first_value(t['ElementValue']) for t in elements[uv_index]['Time']]

    days = min(len(min_temps), len(max_temps), len(pops), len(wxs))

    avg_min = sum(min_temps[:days]) / days
    avg_max = sum(max_temps[:days]) / days
    avg_pop = sum(pops[:days]) / days
    max_uv = max(uv_indexes) if uv_indexes else 0

    date_start = parse_civil_date(elements[0]['Time'][0]['StartTime'])
    date_end = parse_civil_date(elements[0]['Time'][days - 1]['EndTime'])

    desc = classify_week_weather(avg_min, avg_max, avg_pop, wxs)
    if max_uv >= 7:
        desc += " 紫外線強度偏高，建議減少中午時段外出，做好防曬 ☀️🧴"
    elif max_uv >= 5:
        desc += " 紫外線屬中等偏強，記得補擦防曬、戴帽子 😎"

    return f"📅 雙北本週天氣概況（{date_start}～{date_end}）\n{desc}"

# === 工具函數 ===

def fetch_weather_data(location):
    print(f"🌐 [API] 抓取：{location}")
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={cwa_api_key}&locationName={location}"
    res = requests.get(url)
    print("📦 [API] 回應狀態碼：", res.status_code)
    return res.json()

def parse_civil_date(dt_str, days_offset=0):
    try:
        dt = parser.isoparse(dt_str)
    except ValueError:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    dt += timedelta(days=days_offset)
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

def classify_week_weather(min_t, max_t, avg_pop, wxs, uv_indexes, pops, dates):
    rain_days = sum(1 for w in wxs if "雨" in w)
    result = []

    # 🌧 降雨情境分析
    if rain_days >= 7:
        result.append("本週天天有雨，記得每天攜帶雨具 ☔")
    elif avg_pop > 80:
        result.append("本週降雨機率偏高，建議雨具隨身攜帶 ☁🌧")
    elif rain_days >= 5:
        result.append("本週多日有雨，外出請穿防水裝備 ☂")
    elif avg_pop < 20 and all("晴" in w for w in wxs):
        result.append("整週陽光普照，適合戶外活動 ☀️，注意防曬 🧴")
    else:
        result.append("天氣變化大，建議每日關注氣象 ☁")

    # 🧣 穿搭與氣溫建議
    if max_t >= 32:
        result.append("氣溫偏高，注意防中暑與補水 🌡️")
    if max_t - min_t >= 10:
        result.append("日夜溫差大，建議早晚加件外套 🧤")
    if min_t < 18:
        result.append("氣溫偏冷，特別注意保暖 🧥")
    if avg_pop > 60 and min_t < 20:
        result.append("天氣濕冷，穿著建議選擇保暖防潮衣物 💧🧥")
    elif min_t < 18 and all(p < 30 for p in pops):
        result.append("乾冷氣候，注意皮膚保濕與多補水 💧🧴")

    # 🌞 紫外線分析
    max_uv = max(uv_indexes) if uv_indexes else 0
    if max_uv >= 7:
        result.append("紫外線強烈，建議中午避免曝曬 ☀️🧴")
    elif max_uv >= 5:
        result.append("紫外線中等偏強，記得補擦防曬 😎")

    # 🎯 週末活動建議
    weekend_indices = [i for i, d in enumerate(dates) if parser.isoparse(d).weekday() in [5, 6]]
    if weekend_indices:
        wet = any("雨" in wxs[i] for i in weekend_indices)
        hot = any(max_t > 30 for i in weekend_indices)
        if not wet:
            result.append("本週末天氣穩定，適合安排戶外活動 🚴‍♂️🌳")
        else:
            result.append("週末可能有雨，建議規劃室內行程 ☔📚")

    return " ".join(result)

def most_common(lst):
    return max(set(lst), key=lst.count)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
