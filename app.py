from datetime import datetime

def get_weather(location, day_index):
    url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={cwb_api_key}&locationName={location}'
    res = requests.get(url)
    data = res.json()
    weather_elements = data['records']['location'][0]['weatherElement']

    time_data = weather_elements[0]['time'][day_index]
    date_str = time_data['startTime'][:10]  # 取 YYYY-MM-DD
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    roc_date = f"{date_obj.year - 1911}/{date_obj.month}/{date_obj.day}"  # 民國年月日

    wx = time_data['parameter']['parameterName']
    pop = int(weather_elements[1]['time'][day_index]['parameter']['parameterName'])
    min_t = int(weather_elements[2]['time'][day_index]['parameter']['parameterName'])
    max_t = int(weather_elements[4]['time'][day_index]['parameter']['parameterName'])

    rain_strength = ""
    if any(keyword in wx for keyword in ["雷雨", "豪雨", "大雨"]):
        rain_strength = "☔ 雨勢較大，請特別注意行程安排與穿著！"

    message = (
        f"【{location}（{roc_date}）】\n"
        f"天氣：{wx}\n氣溫：{min_t}°C - {max_t}°C\n"
        f"降雨機率：{pop}%\n建議：{suggest(pop, min_t)}"
    )

    if rain_strength:
        message += f"\n{rain_strength}"

    return message
