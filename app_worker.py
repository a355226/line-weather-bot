from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
from apscheduler.schedulers.blocking import BlockingScheduler
import requests

channel_access_token = 'yRDHUt2i8Pg2uvOvPTVj9Mvg55FJYxPu562/d1JFcEOecGz3zbfn9pCJz9el41z1iSfdd0+pGDbGc82Ki++Y6WgiIrdBHb4l1TDo24fS85NIKkkrJVP2c9yk1BNOR08nvi5UlGb1ICaKcdjWIKlSxQdB04t89/1O/w1cDnyilFU='
cwb_api_key = 'CWA-A2775CB4-B52C-47CE-8943-9570AE61D448'
user_ids = ['你的 LINE 使用者 ID']  # ⚠ 請填入你個人的 LINE UID
locations = ['臺北市', '新北市']

configuration = Configuration(access_token=channel_access_token)

def get_weather(loc, index):
    try:
        url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={cwb_api_key}&locationName={loc}'
        data = requests.get(url).json()
        weather = data['records']['location'][0]['weatherElement']
        wx = weather[0]['time'][index]['parameter']['parameterName']
        pop = int(weather[1]['time'][index]['parameter']['parameterName'])
        min_t = int(weather[2]['time'][index]['parameter']['parameterName'])
        max_t = int(weather[4]['time'][index]['parameter']['parameterName'])
        suggest = "☔ 記得帶傘" if pop > 10 else "🌤 無雨預期"
        if min_t < 22:
            suggest += "、🧥 外套保暖"
        return f"【{loc} {'今日' if index==0 else '明日'}】\n{wx} {min_t}-{max_t}°C 降雨 {pop}%\n建議：{suggest}"
    except:
        return f"{loc} 資料讀取失敗"

def push_weather():
    msgs = []
    for loc in locations:
        msgs.append(get_weather(loc, 0))
        msgs.append(get_weather(loc, 1))
    msg = '\n\n'.join(msgs)
    print("[推播]\n", msg)
    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        for uid in user_ids:
            api.push_message(PushMessageRequest(to=uid, messages=[TextMessage(text=msg)]))

scheduler = BlockingScheduler()
scheduler.add_job(push_weather, 'cron', hour=12, minute=0)
scheduler.add_job(push_weather, 'cron', hour=21, minute=0)
scheduler.start()
