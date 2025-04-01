from flask import Flask, request, abort
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, ReplyMessageRequest, TextMessage, QuickReply, QuickReplyItem
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import requests
import os
from apscheduler.schedulers.background import BackgroundScheduler

# === 設定 ===
app = Flask(__name__)
channel_access_token = 'yRDHUt2i8Pg2uvOvPTVj9Mvg55FJYxPu562/d1JFcEOecGz3zbfn9pCJz9el41z1iSfdd0+pGDbGc82Ki++Y6WgiIrdBHb4l1TDo24fS85NIKkkrJVP2c9yk1BNOR08nvi5UlGb1ICaKcdjWIKlSxQdB04t89/1O/w1cDnyilFU='
channel_secret = 'bf209d4d55be8865f7a5ba2522665811'
cwb_api_key = 'CWA-A2775CB4-B52C-47CE-8943-9570AE61D448'
configuration = Configuration(access_token=channel_access_token)
handler = WebhookHandler(channel_secret)

# === 暫存 ===
user_ids = set()
user_prefs = {}  # {user_id: '台北市'}
default_push_locations = ['臺北市', '新北市']

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
    uid = event.source.user_id
    user_ids.add(uid)
    user_msg = event.message.text.strip()

    reply = ""
    quick = make_quick_reply()

    if user_msg == "天氣":
        loc = user_prefs.get(uid, None)
        if loc:
            reply = get_full_weather(loc)
        else:
            reply = "還沒設定常用地區喔！請輸入：設定常用：台北市"

    elif user_msg.startswith("設定常用："):
        area = user_msg.replace("設定常用：", "").strip()
        if area:
            user_prefs[uid] = area
            reply = f"常用地區已設定為【{area}】！之後輸入「天氣」即可快速查詢。"
        else:
            reply = "設定失敗，請輸入：設定常用：地區名"

    elif user_msg in get_all_locations():
        reply = get_full_weather(user_msg)

    else:
        reply = (
            "✅ 歡迎使用專業幽默氣象小幫手 ☁\n"
            "──────────────\n"
            "📌 功能說明：\n"
            "1️⃣ 每日 12:00、21:00 自動推播雙北天氣\n"
            "2️⃣ 輸入『天氣』快速查看常用地區\n"
            "3️⃣ 輸入『台北市』、『大安區』或其他行政區名，直接查詢該地天氣\n"
            "4️⃣ 輸入『設定常用：台中市』可指定常用地區\n"
            "──────────────\n"
            "💡 試試輸入：天氣、大安區 或 設定常用：台北市"
        )

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply, quick_reply=quick)]
            )
        )

# === Quick Reply ===
def make_quick_reply():
    return QuickReply(items=[
        QuickReplyItem(action={'type': 'message', 'label': '台北市', 'text': '台北市'}),
        QuickReplyItem(action={'type': 'message', 'label': '新北市', 'text': '新北市'}),
        QuickReplyItem(action={'type': 'message', 'label': '我的常用', 'text': '天氣'}),
        QuickReplyItem(action={'type': 'message', 'label': '設定常用', 'text': '設定常用：'})
    ])

# === 查詢今明天氣 ===
def get_weather(location):
    try:
        res = requests.get(f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization=CWA-A2775CB4-B52C-47CE-8943-9570AE61D448&locationName={location}')
        data = res.json()
        weather_elements = data['records']['location'][0]['weatherElement']

        msg = []
        for i, label in zip([0, 1, 2, 3], ['今日白天', '今晚', '明日白天', '明晚']):
            wx = weather_elements[0]['time'][i]['parameter']['parameterName']
            pop = int(weather_elements[1]['time'][i]['parameter']['parameterName'])
            min_t = int(weather_elements[2]['time'][i]['parameter']['parameterName'])
            max_t = int(weather_elements[4]['time'][i]['parameter']['parameterName'])
            msg.append(f"【{location} {label}】\n天氣：{wx}  氣溫：{min_t}-{max_t}°C  降雨：{pop}%\n{build_suggestion(pop, min_t)}")
        return "\n\n".join(msg)

    except Exception as e:
        print("天氣資料錯誤：", e)
        return "找不到該地區資料，請確認輸入的地名是否正確。"
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host="0.0.0.0", port=port)
