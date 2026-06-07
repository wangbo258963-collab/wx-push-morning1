import random
from time import localtime
from requests import get, post
from datetime import datetime, date
from zhdate import ZhDate
import sys
import ast


def get_color():
    return "#" + "%06x" % random.randint(0, 0xFFFFFF)


def exit_with_error(message):
    print(message)
    sys.exit(1)


def get_access_token():
    app_id = config["app_id"]
    app_secret = config["app_secret"]

    url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    )

    result = get(url, timeout=10).json()
    print("access_token接口返回：", result)

    if "access_token" not in result:
        exit_with_error("获取access_token失败，请检查app_id和app_secret是否正确")

    return result["access_token"]


def get_weather(region):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    key = config["weather_key"]

    region_url = (
        "https://geoapi.qweather.com/v2/city/lookup"
        f"?location={region}&key={key}"
    )

    response = get(region_url, headers=headers, timeout=10).json()
    print("城市查询接口返回：", response)

    if response.get("code") == "404":
        exit_with_error("推送消息失败，请检查地区名是否有误")
    elif response.get("code") == "401":
        exit_with_error("推送消息失败，请检查和风天气key是否正确")
    elif "location" not in response:
        exit_with_error(f"获取地区失败：{response}")

    location_id = response["location"][0]["id"]

    weather_url = (
        "https://devapi.qweather.com/v7/weather/now"
        f"?location={location_id}&key={key}"
    )

    response = get(weather_url, headers=headers, timeout=10).json()
    print("天气接口返回：", response)

    if "now" not in response:
        exit_with_error(f"获取天气失败：{response}")

    weather = response["now"]["text"]
    temp = response["now"]["temp"] + "℃"
    wind_dir = response["now"]["windDir"]

    return weather, temp, wind_dir


def get_birthday(birthday, year, today):
    birthday_year = birthday.split("-")[0]

    if birthday_year[0] == "r":
        lunar_month = int(birthday.split("-")[1])
        lunar_day = int(birthday.split("-")[2])

        try:
            birthday_date = ZhDate(year, lunar_month, lunar_day).to_datetime().date()
        except TypeError:
            exit_with_error("请检查农历生日日期是否正确")

        birthday_month = birthday_date.month
        birthday_day = birthday_date.day
        year_date = date(year, birthday_month, birthday_day)

    else:
        birthday_month = int(birthday.split("-")[1])
        birthday_day = int(birthday.split("-")[2])
        year_date = date(year, birthday_month, birthday_day)

    if today > year_date:
        if birthday_year[0] == "r":
            next_birthday = ZhDate(year + 1, lunar_month, lunar_day).to_datetime().date()
            birth_date = date(year + 1, next_birthday.month, next_birthday.day)
        else:
            birth_date = date(year + 1, birthday_month, birthday_day)

        birth_day = str(birth_date - today).split(" ")[0]

    elif today == year_date:
        birth_day = 0

    else:
        birth_day = str(year_date - today).split(" ")[0]

    return birth_day


def get_ciba():
    url = "http://open.iciba.com/dsapi/"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    response = get(url, headers=headers, timeout=10).json()

    note_en = response["content"]
    note_ch = response["note"]

    return note_ch, note_en


def send_message(to_user, access_token, region_name, weather, temp, wind_dir, note_ch, note_en):
    url = (
        "https://api.weixin.qq.com/cgi-bin/message/template/send"
        f"?access_token={access_token}"
    )

    week_list = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]

    year = localtime().tm_year
    month = localtime().tm_mon
    day = localtime().tm_mday

    today = datetime.date(datetime(year=year, month=month, day=day))
    week = week_list[today.isoweekday() % 7]

    love_year = int(config["love_date"].split("-")[0])
    love_month = int(config["love_date"].split("-")[1])
    love_day = int(config["love_date"].split("-")[2])

    love_date = date(love_year, love_month, love_day)
    love_days = str(today - love_date).split(" ")[0]

    birthdays = {}

    for key, value in config.items():
        if key.startswith("birth"):
            birthdays[key] = value

    data = {
        "touser": to_user,
        "template_id": config["template_id"],
        "url": "",
        "topcolor": "#FF0000",
        "data": {
            "date": {
                "value": f"{today} {week}",
                "color": get_color()
            },
            "region": {
                "value": region_name,
                "color": get_color()
            },
            "weather": {
                "value": weather,
                "color": get_color()
            },
            "temp": {
                "value": temp,
                "color": get_color()
            },
            "wind_dir": {
                "value": wind_dir,
                "color": get_color()
            },
            "love_day": {
                "value": love_days,
                "color": get_color()
            },
            "note_en": {
                "value": note_en,
                "color": get_color()
            },
            "note_ch": {
                "value": note_ch,
                "color": get_color()
            }
        }
    }

    for key, value in birthdays.items():
        birth_day = get_birthday(value["birthday"], year, today)

        if birth_day == 0:
            birthday_data = f"今天{value['name']}生日哦，祝{value['name']}生日快乐！"
        else:
            birthday_data = f"距离{value['name']}的生日还有{birth_day}天"

        data["data"][key] = {
            "value": birthday_data,
            "color": get_color()
        }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    response = post(url, headers=headers, json=data, timeout=10).json()
    print("模板消息接口返回：", response)

    if response.get("errcode") == 40037:
        exit_with_error("推送消息失败，请检查模板id是否正确")
    elif response.get("errcode") == 40036:
        exit_with_error("推送消息失败，请检查模板id是否为空")
    elif response.get("errcode") == 40003:
        exit_with_error("推送消息失败，请检查openid是否正确")
    elif response.get("errcode") == 0:
        print("推送消息成功")
    else:
        exit_with_error(f"推送消息失败：{response}")


if __name__ == "__main__":
    try:
        with open("config.txt", encoding="utf-8") as f:
            config = ast.literal_eval(f.read())
    except FileNotFoundError:
        exit_with_error("推送消息失败，请检查config.txt文件是否与main.py位于同一路径")
    except SyntaxError:
        exit_with_error("推送消息失败，请检查config.txt配置文件格式是否正确")
    except Exception as e:
        exit_with_error(f"读取配置文件失败：{e}")

    access_token = get_access_token()

    users = config["user"]
    region = config["region"]

    weather, temp, wind_dir = get_weather(region)

    note_ch = config["note_ch"]
    note_en = config["note_en"]

    if note_ch == "" and note_en == "":
        note_ch, note_en = get_ciba()

    for user in users:
        send_message(
            user,
            access_token,
            region,
            weather,
            temp,
            wind_dir,
            note_ch,
            note_en
        )
