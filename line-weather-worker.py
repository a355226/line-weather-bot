from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
import requests
import os
from apscheduler.schedulers.blocking import BlockingScheduler

# === 設定 ===
channel_access_token = 'yRDHUt2i8Pg2uvOvPTVj9Mvg55FJYxPu562/d1JFcEOecGz3zbfn9pCJz9el41z1iSfdd0+pGDbGc82Ki++Y6WgiIrdBHb4l1TDo24fS85NIKkkrJVP2c9yk1BNOR08nvi5UlGb1ICaKcdjWIKlSxQdB04t89/1O/w1cDnyilFU='
cwb_api_key = 'CWA-A2775CB4-B52C-47CE-8943-9570AE61D448'
locations = ['臺北市', '新北市']

configuration = Configuration(access_token=channel_access_token)

# === 暫存 user_id (這邊要改成 Render 上環境變數或其他安全存取，示範先寫死) ===
user_ids = set()
try:
    with open("user_ids.txt", "r") as f:
        user_ids = set(line.strip() for line in f.readlines())
except FileNotFoundError:
    print("尚未建立 user_ids.txt，定時推播無對象")

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

    day = "今日" if day_index == 0 else "明日"

    message = f"【{location} {day}】\n天氣：{wx}\n氣溫：{min_t}°C - {max_t}°C\n降雨機率：{pop}%\n建議：{suggest(int(pop), int(min_t))}"
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

# === 定時推播邏輯 ===
def job_push():
    messages = []
    for loc in locations:
        messages.append(get_weather(loc, 1))
    final_message = "\n\n".join(messages)
    print("[定時推播] 晚上21:00推播")
    broadcast(final_message)


def job_noon():
    messages = []
    for loc in locations:
        messages.append(get_weather(loc, 0))
        messages.append(get_weather(loc, 1))
    final_message = "\n\n".join(messages)
    print("[定時推播] 中午12:00推播")
    broadcast(final_message)

# === 推播發送 ===
def broadcast(message):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        for uid in user_ids:
            line_bot_api.push_message(
                PushMessageRequest(
                    to=uid,
                    messages=[TextMessage(text=message)]
                )
            )

# === APScheduler ===
scheduler = BlockingScheduler()
scheduler.add_job(job_push, 'cron', hour=21, minute=0)
scheduler.add_job(job_noon, 'cron', hour=12, minute=0)
scheduler.start()
