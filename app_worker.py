import time
import schedule
import os
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
from app import get_today_tomorrow_weather, get_week_summary

channel_access_token = 'yRDHUt2i8Pg2uvOvPTVj9Mvg55FJYxPu562/d1JFcEOecGz3zbfn9pCJz9el41z1iSfdd0+pGDbGc82Ki++Y6WgiIrdBHb4l1TDo24fS85NIKkkrJVP2c9yk1BNOR08nvi5UlGb1ICaKcdjWIKlSxQdB04t89/1O/w1cDnyilFU='
configuration = Configuration(access_token=channel_access_token)

# 替換為你要推播的使用者 ID
target_user_ids = [
    "Uafc1366c2806bf46b2cc547d85a414d2",
    "U2ea36514bc2b27ad282b35f8c93eda5e"
]

def job():
    print("⏰ [Worker] 開始推播天氣...")
    try:
        part1 = get_today_tomorrow_weather()
        part2 = get_week_summary()
        message = part1 + "\n\n" + part2

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            for uid in target_user_ids:
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=uid,
                        messages=[TextMessage(text=message)]
                    )
                )
        print("✅ [Worker] 天氣推播完成！")
    except Exception as e:
        print("❌ [Worker Error]", str(e))

# 設定排程
schedule.every().day.at("11:00").do(job)
schedule.every().day.at("21:00").do(job)

if __name__ == "__main__":
    print("🚀 Worker 正在執行中...")
    while True:
        schedule.run_pending()
        time.sleep(1)
