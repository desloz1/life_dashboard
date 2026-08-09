import requests

LATITUDE = -26.9194
LONGITUDE = -49.0661
API_URL = "https://api.open-meteo.com/v1/forecast"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}

WMO_CODES = {
    0: ("Céu limpo", "fa5s.sun", "#f9c74f"),
    1: ("Parcialmente nublado", "fa5s.cloud-sun", "#f9c74f"),
    2: ("Parcialmente nublado", "fa5s.cloud-sun", "#9db4d0"),
    3: ("Nublado", "fa5s.cloud", "#9db4d0"),
    45: ("Nevoeiro", "fa5s.smog", "#9db4d0"),
    48: ("Nevoeiro com geada", "fa5s.smog", "#9db4d0"),
    51: ("Garoa leve", "fa5s.cloud-rain", "#7ec8e3"),
    53: ("Garoa", "fa5s.cloud-rain", "#7ec8e3"),
    55: ("Garoa forte", "fa5s.cloud-rain", "#7ec8e3"),
    56: ("Garoa congelante", "fa5s.cloud-rain", "#7ec8e3"),
    57: ("Garoa congelante forte", "fa5s.cloud-rain", "#7ec8e3"),
    61: ("Chuva fraca", "fa5s.cloud-showers-heavy", "#5aa9e6"),
    63: ("Chuva", "fa5s.cloud-showers-heavy", "#5aa9e6"),
    65: ("Chuva forte", "fa5s.cloud-showers-heavy", "#5aa9e6"),
    66: ("Chuva congelante", "fa5s.cloud-showers-heavy", "#5aa9e6"),
    67: ("Chuva congelante forte", "fa5s.cloud-showers-heavy", "#5aa9e6"),
    71: ("Neve fraca", "fa5s.snowflake", "#bfe3ff"),
    73: ("Neve", "fa5s.snowflake", "#bfe3ff"),
    75: ("Neve forte", "fa5s.snowflake", "#bfe3ff"),
    77: ("Grãos de neve", "fa5s.snowflake", "#bfe3ff"),
    80: ("Pancadas de chuva", "fa5s.cloud-showers-heavy", "#5aa9e6"),
    81: ("Pancadas de chuva", "fa5s.cloud-showers-heavy", "#5aa9e6"),
    82: ("Pancadas de chuva forte", "fa5s.cloud-showers-heavy", "#5aa9e6"),
    85: ("Pancadas de neve", "fa5s.snowflake", "#bfe3ff"),
    86: ("Pancadas de neve", "fa5s.snowflake", "#bfe3ff"),
    95: ("Trovoada", "fa5s.bolt", "#f9c74f"),
    96: ("Trovoada com granizo", "fa5s.bolt", "#f9c74f"),
    99: ("Trovoada forte com granizo", "fa5s.bolt", "#f9c74f"),
}


def _info(code):
    return WMO_CODES.get(code, ("Desconhecido", "fa5s.cloud", "#9db4d0"))


def get_weather():
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": (
            "temperature_2m,relative_humidity_2m,"
            "apparent_temperature,weather_code,wind_speed_10m"
        ),
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "America/Sao_Paulo",
        "forecast_days": 7,
    }
    response = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
    response.raise_for_status()
    data = response.json()

    current = data["current"]
    current_code = current["weather_code"]
    description, icon_name, icon_color = _info(current_code)

    days = []
    daily = data["daily"]
    for index, day in enumerate(daily["time"]):
        code = daily["weather_code"][index]
        desc, icon, color = _info(code)
        days.append(
            {
                "date": day,
                "code": code,
                "description": desc,
                "icon": icon,
                "color": color,
                "max": round(daily["temperature_2m_max"][index]),
                "min": round(daily["temperature_2m_min"][index]),
                "precip": daily["precipitation_probability_max"][index],
            }
        )

    return {
        "temperature": round(current["temperature_2m"]),
        "feels_like": round(current["apparent_temperature"]),
        "humidity": current["relative_humidity_2m"],
        "wind": round(current["wind_speed_10m"]),
        "description": description,
        "icon": icon_name,
        "color": icon_color,
        "days": days,
    }
