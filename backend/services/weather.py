import requests
from ..config import Config

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"

def get_weather(lat, lon):
    params = {"lat": lat, "lon": lon, "appid": Config.OPENWEATHER_API_KEY}
    r = requests.get(OWM_URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()
