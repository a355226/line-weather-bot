from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import requests
import os
from datetime import datetime, timedelta
import json
from dateutil import parser

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
            part1, part2 = "", ""
            try:
                print("🔍 [Debug] 使用者請求今明天氣")
                part1 = get_today_tomorrow_weather()
                print("✅ [Debug] 今日與明日天氣取得成功")
            except Exception as e1:
                print("❌ [Error] get_today_tomorrow_weather()：", str(e1))
                part1 = "⚠️ 今明天氣資料無法取得。"

            try:
                print("🧪 [Debug] 開始處理 get_week_summary()")
                part2 = get_week_summary()
                print("✅ [Debug] 一週天氣概況取得成功")
            except Exception as e2:
                import traceback
                print("❌ [Error] get_week_summary()：", str(e2))
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
        print("❌ [最終錯誤處理] handle_message 爆炸了！", str(e))

def get_today_tomorrow_weather():
    print("🚀 進入 get_today_tomorrow_weather()")
    msg = "【雙北地區】\n"
    location = "臺北市"
    print(f"📍 處理地區：{location}")
    data = fetch_weather_data(location)

    times = data['records']['location'][0]['weatherElement'][0]['time']
    all_datetimes = [t['startTime'] for t in times]
    print("🕒 [Debug] 全部時間欄位：", all_datetimes)

    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    today_str = today.strftime("%Y-%m-%d")
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")

    for target_date, label in [(today_str, "今日"), (tomorrow_str, "明日")]:
        found = False
        for i, t in enumerate(times):
            start = t['startTime'][:10]
            if start == target_date:
                wx = data['records']['location'][0]['weatherElement'][0]['time'][i]['parameter']['parameterName']
                pop = int(data['records']['location'][0]['weatherElement'][1]['time'][i]['parameter']['parameterName'])
                min_t = int(data['records']['location'][0]['weatherElement'][2]['time'][i]['parameter']['parameterName'])
                max_t = int(data['records']['location'][0]['weatherElement'][4]['time'][i]['parameter']['parameterName'])
                date = parse_civil_date(t['startTime'])
                suggest = build_suggestion(pop, min_t)
                msg += f"{label}（{date}）\n☁ 天氣：{wx}\n🌡 氣溫：{min_t}-{max_t}°C\n☔ 降雨：{pop}%\n🧾 建議：{suggest}\n\n"
                found = True
                break
        if not found:
            if label == "明日":
                msg += f"{label}：⚠️ 預報尚未更新，凌晨 6 點後再查詢 🌙\n\n"
            else:
                msg += f"{label}：⚠️ 無法正確取得預報資料。\n\n"

    return msg.strip()


    
def find_index_by_date(times, target_date):
    for i, t in enumerate(times):
        try:
            dt = parser.isoparse(t['startTime']).date()
            if dt == target_date:
                return i
        except:
            continue
    return None

def get_week_summary():
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-063?Authorization={cwa_api_key}&locationName=臺北市"
    response = requests.get(url)
    data = response.json()
    elements = data['records']['Locations'][0]['Location'][0]['WeatherElement']

    wx_index = next(i for i, e in enumerate(elements) if '天氣現象' in e['ElementName'])
    pop_index = next(i for i, e in enumerate(elements) if '降雨機率' in e['ElementName'])
    min_index = next(i for i, e in enumerate(elements) if '最低溫度' in e['ElementName'])
    max_index = next(i for i, e in enumerate(elements) if '最高溫度' in e['ElementName'])
    uv_index = next(i for i, e in enumerate(elements) if '紫外線指數' in e['ElementName'])

    def extract_first_value(ev):
        try: return int(list(ev[0].values())[0])
        except: return 0

    def extract_str_value(ev):
        try: return list(ev[0].values())[0]
        except: return "?"

    times = [t['StartTime'] for t in elements[wx_index]['Time']]
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

    desc = classify_week_weather(avg_min, avg_max, avg_pop, wxs, uv_indexes, pops, times)
    weekend = weekend_activity_advice(wxs, pops, times)

    return f"📅 雙北本週天氣概況（{date_start}～{date_end}）\n{desc}\n\n{weekend}"

def fetch_weather_data(location):
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={cwa_api_key}&locationName={location}"
    res = requests.get(url)
    return res.json()

def parse_civil_date(dt_str, days_offset=0):
    dt = parser.isoparse(dt_str) + timedelta(days=days_offset)
    return f"{dt.year - 1911}/{dt.month}/{dt.day}"

def build_suggestion(pop, min_t):
    tips = []
    if pop > 70: tips.append("降雨機率高，請務必帶傘 ☔")
    elif pop > 30: tips.append("可能會下雨，建議攜帶雨具 ☂")
    if min_t < 18: tips.append("早晚偏冷，記得加件外套 🧥")
    elif min_t < 22: tips.append("氣溫偏涼，建議穿長袖或外套 🧣")
    if not tips: tips.append("天氣穩定，輕便出門最適合 ☀")
    return "、".join(tips)

def classify_week_weather(min_t, max_t, avg_pop, wxs, uv_indexes, pops, dates):
    result = []
    rain_days = sum(1 for w in wxs if "雨" in w)
    if avg_pop > 80: result.append("本週多雨，幾乎天天會下雨 ☔")
    elif avg_pop > 50: result.append("這週時晴時雨，建議雨具隨身攜帶 ☁🌧")
    elif rain_days >= 5: result.append("大多日子有雨，外出建議穿防水鞋 ☂")
    elif avg_pop < 20 and all("晴" in w for w in wxs): result.append("整週陽光普照 ☀️，適合出遊，注意防曬 🧴")
    else: result.append("天氣變化大，建議每日留意天氣預報 📡")

    if max_t >= 32: result.append("氣溫偏高，要注意防中暑與防曬 🌡️")
    elif min_t < 18: result.append("早晚溫差大，要注意保暖 🧥")
    elif max_t - min_t >= 10: result.append("日夜溫差大，注意衣物調整 🧣🧤")

    if max(uv_indexes) >= 7:
        result.append("紫外線強度偏高，請減少曝曬並防曬 ☀️🧴")

    return " ".join(result)

def weekend_activity_advice(wxs, pops, times):
    from collections import defaultdict

    advice_dict = defaultdict(list)
    weekday_map = {5: "六", 6: "日"}

    for i, dt_str in enumerate(times):
        try:
            dt = datetime.fromisoformat(dt_str)
            wd = dt.weekday()
            if wd in [5, 6]:  # 週六或週日
                key = dt.strftime("%m/%d") + f"（{weekday_map[wd]}）"

                if pops[i] >= 50:
                    advice_dict[key].append("可能會下雨，建議以室內活動為主 ☔")
                elif pops[i] >= 15 or "雨" in wxs[i]:
                    advice_dict[key].append("天氣稍不穩定，可安排輕鬆行程 🌤")
                else:
                    advice_dict[key].append("適合外出踏青 🚴")
        except:
            continue

    # 移除重複、每日期只顯示一句
    summary = []
    for date_key in sorted(advice_dict):
        unique = list(dict.fromkeys(advice_dict[date_key]))
        summary.append(f"{date_key} {unique[0]}")

    if not summary:
        return "🏖️ 本週週末天氣資料不足，建議持續關注預報 🧐"

    return "🏖️ 週末活動建議：\n" + "\n".join(summary)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
