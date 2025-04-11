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
        reply = get_today_tomorrow_weather()
        reminder = "\n\n\u8acb稍待1-2\u5206\u9418\uff0c\u6a5f\u5668\u4eba\u6b63\u5728\u63a1\u96c6\u6700\u65b0\u5929\u6c23\u8cc7\u8a0a...\u5c0d\u4f60\u7684\u95dc\u5fc3\uff0c\u4e00\u5b9a\u6bd4\u96f2\u908a\u7684\u967d\u5149\u9084\u6696\u5fc3。"
        reply += reminder
    else:
        reply = (
            "\u2705 \u6b61\u8fce\u4f7f\u7528\u5929\u6c23\u63d0\u9192\u6a5f\u5668\u4eba \u2601\n"
            "─────────────────\n"
            "🔔 \u529f\u80fd\u4ecb\u7d39\uff1a\n"
            "1⃣ 輸\u5165『\u5929\u6c23』\u53ef\u67e5\u770b臺\u5317\u3001\u65b0\u5317\u4eca\u660e\u5929\u6c23\u72c0\u6cc1\n"
            "2⃣ \u6211\u6703\u70ba\u4f60\u5206\u6790\u662f\u5426\u9700\u8981\u5099\u5098\u6216\u7a7f\u5916\u5957\uff0c\u8b93\u51fa\u9580\u66f4\u6709\u5b89\u5fc3\u611f\n"
            "─────────────────\n"
            "💡 \u8a66\u8a66\u8f38\u5165\uff1a\u5929\u6c23"
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
    for i, loc in enumerate(locations):
        msgs.append(get_weather(loc, 0))
        msgs.append(get_weather(loc, 1))
    return "\n\n".join(msgs)

# === 天氣主體 ===
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
        time_start = weather_elements[0]['time'][day_index]['startTime'][:10]

        roc_date = datetime.strptime(time_start, "%Y-%m-%d")
        roc_year = roc_date.year - 1911
        date_str = f"{roc_year}年{roc_date.month}月{roc_date.day}日"

        suggest_text = suggest(pop, min_t, wx)

        return f"【{location} {date_str}】\n天氣：{wx}\n氣溫：{min_t}°C - {max_t}°C\n降雨機率：{pop}%\n建議：{suggest_text}"
    except Exception as e:
        return f"{location} 天氣資料錯誤: {e}"

# === 建議文字 ===
def suggest(pop, min_temp, wx):
    msg = []
    if "雨" in wx:
        if "大" in wx:
            msg.append("大雨預報，備好雨具與措備漸水防策 ☔☀")
        else:
            msg.append("有雨可能，請備傘或有防水裝備 ☔")
    elif pop > 10:
        msg.append("降雨機率較高，建議備傘 ☔")

    if min_temp < 22:
        msg.append("溫度較低，請多加一件外套 🫕")

    if not msg:
        msg.append("天氣良好，出門有好心情 ☀")
    return " ".join(msg)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
