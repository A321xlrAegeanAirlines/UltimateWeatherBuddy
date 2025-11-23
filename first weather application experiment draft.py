"""
Ultimate Weather Buddy – 12-day Pro Marvel Update
(with Settings, Compare window, Live background, Autocomplete, Caching,
Precip Bars, Smart Header, Activity Hour Ranking)

Apple-ish weather desktop app using Open-Meteo (no API key).

Main features:
- Search any city/neighbourhood (e.g. "Barnes, London") with autocomplete dropdown
- Current conditions with feels-like, humidity, wind, pressure, rain
- Smart micro-summary under header (premium app feel)
- Live background: gradient sky that changes with weather + day/night, always readable text
- Light/Dark themes
- Metric/Imperial units (C/°F, km/h/mph, mm/in)
- Favourites (save, load, remove locations)
- Bigger, clearer favourites buttons
- Settings dialog:
    • Theme (light/dark)
    • Units (metric/imperial)
    • Show/hide advanced panels
- 12-day forecast (graph + detailed text)
    • High-temp line
    • NEW: daily precipitation bars
- 12-day overview & extremes
- Day selector for hourly view (up to 12 days)
- 24-hour graphs (per selected day):
    • Temperature
    • Feels like
    • Rain chance
    • UV
    • Wind speed
    • Humidity
    • Comfort index (0–100)
- Hourly mini-strip with emoji, temperature, rain %, “best outdoor hour” highlighted
- Sunrise/sunset timeline
- Wind compass
- Air quality (EU & US AQI)
- Moon phase
- Story card: today’s story + next days summary
- Activities: walking, sport, stargazing + best hour ranking
- Clothing & safety suggestions
- Compare favourites:
    • Opens in its own window ("page") with close button

Requires:
    pip install requests
"""

import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import requests
import math
import os
import json

# ===========================
# PATHS & SETTINGS FILE
# ===========================

if "__file__" in globals():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
else:
    BASE_DIR = os.getcwd()

SETTINGS_FILE = os.path.join(BASE_DIR, "weather_settings.json")

# ===========================
# API ENDPOINTS
# ===========================

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# ===========================
# FORECAST DAYS (NEW)
# ===========================

FORECAST_DAYS = 12

# ===========================
# THEMES
# ===========================

THEMES = {
    "light": {
        "bg": "#e5f0ff",
        "fg": "#111827",
        "card_bg": "#ffffff",
        "text_bg": "#ffffff",
        "text_fg": "#111827",
        "accent": "#2563eb",
    },
    "dark": {
        "bg": "#020617",
        "fg": "#e5e7eb",
        "card_bg": "#0f172a",
        "text_bg": "#020617",
        "text_fg": "#e5e7eb",
        "accent": "#38bdf8",
    },
}

theme_mode = "light"
units_mode = "metric"      # "metric" or "imperial"

# Advanced panel visibility
show_air_panel = True
show_comfort_graph = True
show_story_panel = True
show_activities_panel = True

weather_bg: Optional[str] = None

# Global state for data
last_forecast: Optional[Dict[str, Any]] = None
last_location: Optional[Dict[str, Any]] = None
last_air: Optional[Dict[str, Any]] = None
daily_dates: List[str] = []
selected_day_index: int = 0
favourites: List[Dict[str, Any]] = []
best_hour_time: Optional[str] = None  # ISO "YYYY-MM-DDTHH:MM"

# Forecast cache (NEW): 20 minute cache
forecast_cache: Dict[Tuple[float, float, str], Dict[str, Any]] = {}

# Widgets
root: tk.Tk
city_entry: tk.Entry
get_button: tk.Button
units_button: tk.Button
theme_button: tk.Button
settings_button: tk.Button
last_updated_label: tk.Label
top_frame: tk.Frame
autocomplete_listbox: tk.Listbox

favourites_listbox: tk.Listbox

content_canvas: tk.Canvas
scrollable_frame: tk.Frame

header_frame: tk.Frame
header_text_frame: tk.Frame
icon_label: tk.Label
big_temp_label: tk.Label
location_label: tk.Label
hi_lo_label: tk.Label
micro_summary_label: tk.Label  # NEW
alert_label: tk.Label

current_frame: tk.LabelFrame
current_text: tk.Text

forecast_frame: tk.LabelFrame
forecast_canvas: tk.Canvas
forecast_text: tk.Text

ten_day_overview_frame: tk.LabelFrame
ten_day_overview_text: tk.Text

hourly_frame: tk.LabelFrame
day_selector_frame: tk.Frame
day_label: tk.Label
day_buttons: List[tk.Button] = []

hourly_strip_canvas: tk.Canvas
hourly_strip_scrollbar: tk.Scrollbar

hourly_temp_canvas: tk.Canvas
hourly_feels_canvas: tk.Canvas
hourly_rain_canvas: tk.Canvas
hourly_uv_canvas: tk.Canvas
hourly_wind_canvas: tk.Canvas
hourly_humid_canvas: tk.Canvas
hourly_comfort_canvas: tk.Canvas

sun_frame: tk.LabelFrame
sun_text_label: tk.Label
sun_canvas: tk.Canvas

wind_frame: tk.LabelFrame
wind_text_label: tk.Label
wind_canvas: tk.Canvas

air_frame: tk.LabelFrame
air_text_label: tk.Label

moon_frame: tk.LabelFrame
moon_text_label: tk.Label

story_frame: tk.LabelFrame
story_text: tk.Text

activities_frame: tk.LabelFrame
activities_text: tk.Text

suggestions_frame: tk.LabelFrame
suggestions_text: tk.Text

compare_frame: tk.LabelFrame
compare_text: tk.Text

wallpaper_frame: tk.LabelFrame
wallpaper_canvas: tk.Canvas

footer_label: tk.Label


# ===========================
# UNIT CONVERSIONS
# ===========================

def c_to_f(c: Optional[float]) -> Optional[float]:
    if c is None:
        return None
    return c * 9.0 / 5.0 + 32.0


def f_to_c(f: Optional[float]) -> Optional[float]:
    if f is None:
        return None
    return (f - 32.0) * 5.0 / 9.0


def mm_to_in(mm: Optional[float]) -> Optional[float]:
    if mm is None:
        return None
    return mm / 25.4


def kmh_to_mph(kmh: Optional[float]) -> Optional[float]:
    if kmh is None:
        return None
    return kmh * 0.621371


def mph_to_kmh(mph: Optional[float]) -> Optional[float]:
    if mph is None:
        return None
    return mph / 0.621371


def fmt_temp_value(c: Optional[float]) -> str:
    if c is None:
        return "N/A"
    if units_mode == "metric":
        return f"{c:.1f} °C"
    else:
        f = c_to_f(c)
        return f"{f:.1f} °F"


def fmt_rain_value(mm: Optional[float]) -> str:
    if mm is None:
        return "N/A"
    if units_mode == "metric":
        return f"{mm:.1f} mm"
    else:
        inch = mm_to_in(mm)
        return f"{inch:.2f} in"


def fmt_wind_value(kmh: Optional[float]) -> str:
    if kmh is None:
        return "N/A"
    if units_mode == "metric":
        return f"{kmh:.1f} km/h"
    else:
        mph = kmh_to_mph(kmh)
        return f"{mph:.1f} mph"


def temp_axis_label(c: float) -> str:
    if units_mode == "metric":
        return f"{c:.0f}°C"
    else:
        f = c_to_f(c)
        return f"{f:.0f}°F"


def temp_point_label(c: float) -> str:
    if units_mode == "metric":
        return f"{c:.1f}°C"
    else:
        f = c_to_f(c)
        return f"{f:.1f}°F"


def wind_axis_label(kmh: float) -> str:
    if units_mode == "metric":
        return f"{kmh:.0f} km/h"
    else:
        mph = kmh_to_mph(kmh)
        return f"{mph:.0f} mph"


def wind_point_label(kmh: float) -> str:
    if units_mode == "metric":
        return f"{kmh:.1f} km/h"
    else:
        mph = kmh_to_mph(kmh)
        return f"{mph:.1f} mph"


# ===========================
# WEATHER CODE → TEXT + EMOJI
# ===========================

WEATHER_DESC = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def weather_text(code: Optional[int]) -> str:
    if code is None:
        return "Unknown"
    return WEATHER_DESC.get(code, f"Weather code {code}")


def weather_icon(code: Optional[int]) -> str:
    if code is None:
        return "🌡️"
    if code == 0:
        return "☀️"
    if code in (1, 2):
        return "⛅"
    if code == 3:
        return "☁️"
    if code in (45, 48):
        return "🌫️"
    if 51 <= code <= 57:
        return "🌦️"
    if 61 <= code <= 67:
        return "🌧️"
    if 71 <= code <= 77:
        return "❄️"
    if 80 <= code <= 82:
        return "🌧️"
    if 85 <= code <= 86:
        return "🌨️"
    if code >= 95:
        return "⛈️"
    return "🌡️"


# ===========================
# UV, AQI & SUGGESTIONS
# ===========================

def interpret_uv(uv: Optional[float]) -> str:
    if uv is None:
        return "N/A"
    if uv < 3:
        return "Low"
    if uv < 6:
        return "Moderate"
    if uv < 8:
        return "High"
    if uv < 11:
        return "Very high"
    return "Extreme"


def interpret_aqi_eu(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    if value <= 20:
        return "Good"
    if value <= 40:
        return "Fair"
    if value <= 60:
        return "Moderate"
    if value <= 80:
        return "Poor"
    if value <= 100:
        return "Very poor"
    return "Extremely poor"


def interpret_aqi_us(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    if value <= 50:
        return "Good"
    if value <= 100:
        return "Moderate"
    if value <= 150:
        return "Unhealthy for sensitive groups"
    if value <= 200:
        return "Unhealthy"
    if value <= 300:
        return "Very unhealthy"
    return "Hazardous"


def generate_suggestions(
    temp_c: Optional[float],
    feels_c: Optional[float],
    uv_max: Optional[float],
    rain_prob: Optional[float],
    wind_max: Optional[float],
    humidity_avg: Optional[float],
    aqi_desc: str,
    code: Optional[int],
) -> str:
    lines: List[str] = []
    base_temp = feels_c if feels_c is not None else temp_c

    lines.append("Clothing:")
    if base_temp is None:
        lines.append("• No temperature data – dress for how it feels outside.")
    else:
        if base_temp <= -5:
            lines.append("• 🧥 Very cold: heavy winter coat, scarf, gloves, hat and warm boots.")
        elif base_temp <= 3:
            lines.append("• 🧣 Freezing: thick coat, scarf and gloves strongly recommended.")
        elif base_temp <= 10:
            lines.append("• 🧥 Chilly: coat or thick hoodie and long trousers.")
        elif base_temp <= 18:
            lines.append("• 🧥 Cool: light jacket or jumper, layers you can take off.")
        elif base_temp <= 24:
            lines.append("• 👕 Comfortable: t-shirt with a light layer.")
        elif base_temp <= 30:
            lines.append("• 🩳 Warm: light, breathable clothes and drink water.")
        else:
            lines.append("• ☀️ Hot: very light clothing, stay hydrated and avoid long exposure in midday sun.")

    lines.append("")
    lines.append("Rain / snow:")
    if isinstance(rain_prob, (int, float)):
        if rain_prob >= 80:
            lines.append("• 🌧️ Rain very likely – waterproof jacket and a good umbrella are useful.")
        elif rain_prob >= 60:
            lines.append("• 🌦️ Showers likely – a compact umbrella or light raincoat is a good idea.")
        elif rain_prob >= 30:
            lines.append("• 🌥️ Some risk of showers – check the sky before going out.")
        else:
            lines.append("• 🌤️ Low chance of rain.")
    else:
        lines.append("• Rain probability not available.")

    if code is not None:
        if 71 <= code <= 77 or 85 <= code <= 86:
            lines.append("• ❄️ Snow possible – waterproof footwear and warm socks recommended.")
        if code >= 95:
            lines.append("• ⛈️ Thunderstorms: avoid open fields and tall isolated trees.")

    lines.append("")
    lines.append("Sun & UV:")
    if isinstance(uv_max, (int, float)):
        level = interpret_uv(uv_max)
        lines.append(f"• UV max: {uv_max:.1f} ({level}).")
        if uv_max >= 8:
            lines.append("• 🧢 Very strong UV – sunglasses, hat and high-SPF sunscreen are essential.")
        elif uv_max >= 5:
            lines.append("• 😎 Moderate UV – sunscreen and sunglasses recommended.")
        elif uv_max >= 3:
            lines.append("• Low–moderate UV – sunscreen helpful if outside for hours.")
        else:
            lines.append("• 🌙 Low UV – sunburn risk is small for most people.")
    else:
        lines.append("• UV data not available.")

    lines.append("")
    lines.append("Wind:")
    if isinstance(wind_max, (int, float)):
        if wind_max >= 60:
            lines.append("• 💨 Very windy/gusty – be careful cycling and with umbrellas, secure loose items.")
        elif wind_max >= 35:
            lines.append("• 🌬️ Windy – it will feel cooler than the temperature, windproof layer helps.")
        else:
            lines.append("• Light to moderate wind – nothing extreme.")
    else:
        lines.append("• Wind data not available.")

    lines.append("")
    lines.append("Humidity:")
    if isinstance(humidity_avg, (int, float)):
        if humidity_avg >= 80:
            lines.append("• 🥵 Very humid – can feel muggy, drink water and take breaks if exercising.")
        elif humidity_avg >= 60:
            lines.append("• A bit humid – can feel warmer than the air temperature.")
        elif humidity_avg <= 35:
            lines.append("• 💧 Dry air – lips and skin may dry out; lip balm or moisturiser can help.")
        else:
            lines.append("• Comfortable humidity for most people.")
    else:
        lines.append("• Humidity data not available.")

    lines.append("")
    lines.append("Air quality:")
    if aqi_desc and aqi_desc != "N/A":
        lines.append(f"• Overall: {aqi_desc}.")
        low = aqi_desc.lower()
        if any(w in low for w in ("unhealthy", "poor", "hazard")):
            lines.append("• People with asthma or heart/lung issues should avoid heavy outdoor exercise.")
        else:
            lines.append("• Air quality is fine for normal outdoor plans.")
    else:
        lines.append("• No air quality data available.")

    return "\n".join(lines)


# ===========================
# COMFORT INDEX (units-aware NEW)
# ===========================

def compute_comfort_index(
    temp_c_or_f: Optional[float],
    hum: Optional[float],
    wind_kmh_or_mph: Optional[float],
    uv: Optional[float],
    rain_prob: Optional[float],
) -> Optional[float]:
    """
    Return a 0–100 comfort score (higher = nicer).
    Units-aware: if imperial, convert to Celsius + km/h before scoring.
    """
    if temp_c_or_f is None:
        return None

    # Convert to metric for scoring if imperial
    if units_mode == "imperial":
        temp_c = f_to_c(float(temp_c_or_f))
        wind_kmh = mph_to_kmh(float(wind_kmh_or_mph)) if wind_kmh_or_mph is not None else None
    else:
        temp_c = float(temp_c_or_f)
        wind_kmh = float(wind_kmh_or_mph) if wind_kmh_or_mph is not None else None

    if temp_c is None:
        return None

    score = 100.0
    ideal = 19.0
    score -= min(60.0, abs(temp_c - ideal) * 2.5)

    if isinstance(hum, (int, float)):
        if hum >= 85:
            score -= 15
        elif hum >= 70:
            score -= 8
        elif hum <= 30:
            score -= 10

    if isinstance(wind_kmh, (int, float)):
        if wind_kmh >= 60:
            score -= 25
        elif wind_kmh >= 40:
            score -= 15
        elif wind_kmh >= 25:
            score -= 7

    if isinstance(uv, (int, float)):
        if uv >= 8:
            score -= 12
        elif uv >= 6:
            score -= 7
        elif uv >= 3:
            score -= 3

    if isinstance(rain_prob, (int, float)):
        if rain_prob >= 80:
            score -= 25
        elif rain_prob >= 60:
            score -= 15
        elif rain_prob >= 30:
            score -= 7

    return max(0.0, min(100.0, score))


# ===========================
# API HELPERS
# ===========================

def http_get_json(url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Network error", f"Could not reach the service:\n{e}")
        return None


def geocode_city(name: str) -> Optional[Dict[str, Any]]:
    params = {"name": name, "count": 5, "language": "en", "format": "json"}
    data = http_get_json(GEOCODE_URL, params)
    if not data:
        return None
    results = data.get("results") or []
    if not results:
        messagebox.showerror("Not found", f"Could not find any place called '{name}'.")
        return None

    if len(results) == 1:
        r = results[0]
    else:
        r = choose_location(results)
        if r is None:
            return None

    return {
        "name": r.get("name") or name,
        "country": r.get("country") or "",
        "admin1": r.get("admin1") or "",
        "latitude": r.get("latitude"),
        "longitude": r.get("longitude"),
        "timezone": r.get("timezone") or "auto",
    }


def choose_location(results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    dialog = tk.Toplevel(root)
    dialog.title("Choose a location")
    dialog.grab_set()

    tk.Label(dialog, text="Multiple matches found. Choose one:").pack(padx=10, pady=5)
    lb = tk.Listbox(dialog, width=60, height=min(8, len(results)))
    for r in results:
        name = r.get("name") or ""
        admin1 = r.get("admin1") or ""
        country = r.get("country") or ""
        parts = [name]
        if admin1:
            parts.append(admin1)
        if country:
            parts.append(country)
        lb.insert(tk.END, ", ".join(parts))
    lb.pack(padx=10, pady=5)

    chosen = {"i": None}

    def on_ok(event=None):
        sel = lb.curselection()
        if not sel:
            return
        chosen["i"] = sel[0]
        dialog.destroy()

    def on_cancel():
        dialog.destroy()

    lb.bind("<Double-Button-1>", on_ok)
    dialog.bind("<Return>", on_ok)
    dialog.bind("<Escape>", lambda e: on_cancel())

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="OK", command=on_ok).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side="left", padx=5)

    root.wait_window(dialog)
    i = chosen["i"]
    if i is None:
        return None
    return results[i]


def fetch_weather(lat: float, lon: float, timezone: str) -> Optional[Dict[str, Any]]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": timezone or "auto",
        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "rain",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "pressure_msl",
            "is_day",
        ]),
        "hourly": ",".join([
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "precipitation_probability",
            "uv_index",
            "wind_speed_10m",
            "weather_code",
        ]),
        "daily": ",".join([
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "apparent_temperature_max",
            "apparent_temperature_min",
            "uv_index_max",
            "precipitation_sum",
            "precipitation_probability_max",
            "wind_speed_10m_max",
            "sunrise",
            "sunset",
        ]),
        "forecast_days": FORECAST_DAYS,
    }
    return http_get_json(WEATHER_URL, params)


def fetch_weather_cached(lat: float, lon: float, timezone: str) -> Optional[Dict[str, Any]]:
    """NEW: 20-minute cache for forecasts."""
    key = (round(lat, 3), round(lon, 3), units_mode)
    item = forecast_cache.get(key)
    if item:
        age = datetime.now() - item["time"]
        if age < timedelta(minutes=20):
            return item["data"]

    data = fetch_weather(lat, lon, timezone)
    if data:
        forecast_cache[key] = {"time": datetime.now(), "data": data}
    return data


def fetch_air_quality(lat: float, lon: float, timezone: str) -> Optional[Dict[str, Any]]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": timezone or "auto",
        "current": "european_aqi,us_aqi,uv_index",
    }
    data = http_get_json(AIR_QUALITY_URL, params)
    if not data:
        return None
    return data.get("current")


# ===========================
# BACKGROUND & THEME
# ===========================

def choose_weather_background(code: Optional[int], is_day: Optional[int]) -> str:
    if is_day == 0:
        return "#020617"
    else:
        if code in (0, 1):
            return "#dbeafe"
        if code in (2, 3, 45, 48):
            return "#e5e7eb"
        if code and (51 <= code <= 67 or 80 <= code <= 82):
            return "#e0f2fe"
        if code and (71 <= code <= 77 or 85 <= code <= 86):
            return "#f1f5f9"
        if code and code >= 95:
            return "#e5e7eb"
        return "#e5f0ff"


def load_wallpapers() -> None:
    pass


def style_day_buttons() -> None:
    theme = THEMES[theme_mode]
    for i, btn in enumerate(day_buttons):
        if i == selected_day_index:
            btn.config(relief="sunken", font=("Arial", 11, "bold"),
                       bg=theme["card_bg"])
        else:
            btn.config(relief="raised", font=("Arial", 11),
                       bg=theme["card_bg"])


def update_wallpaper(code: Optional[int], is_day: Optional[int]) -> None:
    wallpaper_canvas.delete("all")

    width = wallpaper_canvas.winfo_width()
    height = wallpaper_canvas.winfo_height()
    if width < 300:
        width = 900
    if height < 120:
        height = 220

    def hex_to_rgb(h: str):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def interpolate(c1: str, c2: str, t: float) -> str:
        r1, g1, b1 = hex_to_rgb(c1)
        r2, g2, b2 = hex_to_rgb(c2)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def luminance(c: str) -> float:
        r, g, b = hex_to_rgb(c)
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0

    top_col = "#60a5fa"
    bottom_col = "#bfdbfe"

    if is_day == 0:
        if code in (0, 1):
            top_col = "#020617"
            bottom_col = "#111827"
        elif code in (2, 3, 45, 48):
            top_col = "#111827"
            bottom_col = "#4b5563"
        elif code and (51 <= code <= 67 or 80 <= code <= 82):
            top_col = "#020617"
            bottom_col = "#1f2937"
        elif code and (71 <= code <= 77 or 85 <= code <= 86):
            top_col = "#0b1120"
            bottom_col = "#e5e7eb"
        elif code and code >= 95:
            top_col = "#020617"
            bottom_col = "#111827"
        else:
            top_col = "#020617"
            bottom_col = "#111827"
    else:
        if code in (0, 1):
            top_col = "#38bdf8"
            bottom_col = "#e0f2fe"
        elif code in (2, 3, 45, 48):
            top_col = "#d1d5db"
            bottom_col = "#e5e7eb"
        elif code and (51 <= code <= 67 or 80 <= code <= 82):
            top_col = "#1d4ed8"
            bottom_col = "#93c5fd"
        elif code and (71 <= code <= 77 or 85 <= code <= 86):
            top_col = "#e5f0ff"
            bottom_col = "#f9fafb"
        elif code and code >= 95:
            top_col = "#111827"
            bottom_col = "#4b5563"
        else:
            top_col = "#60a5fa"
            bottom_col = "#bfdbfe"

    stripes = 40
    for i in range(stripes):
        t = i / max(1, stripes - 1)
        colour = interpolate(top_col, bottom_col, t)
        y0 = int(t * height)
        y1 = int((i + 1) / max(1, stripes) * height)
        wallpaper_canvas.create_rectangle(0, y0, width, y1, fill=colour, outline="")

    mid_color = interpolate(top_col, bottom_col, 0.5)
    if luminance(mid_color) < 0.5:
        fg = "#f9fafb"
    else:
        fg = "#111827"

    global last_forecast, last_location
    desc = weather_text(code)
    emoji = weather_icon(code)
    temp_text = ""
    loc_text = ""

    if last_forecast and isinstance(last_forecast, dict):
        current = last_forecast.get("current") or {}
        temp_c = current.get("temperature_2m")
        if isinstance(temp_c, (int, float)):
            temp_text = fmt_temp_value(temp_c)

    if last_location and isinstance(last_location, dict):
        loc_text = format_location(last_location)

    wallpaper_canvas.create_text(
        width / 2,
        height * 0.32,
        text=f"{emoji}  {desc}",
        fill=fg,
        font=("Arial", 20, "bold")
    )

    if temp_text:
        wallpaper_canvas.create_text(
            width / 2,
            height * 0.52,
            text=temp_text,
            fill=fg,
            font=("Arial", 16)
        )

    if loc_text:
        wallpaper_canvas.create_text(
            width / 2,
            height * 0.7,
            text=loc_text,
            fill=fg,
            font=("Arial", 11)
        )


def apply_theme() -> None:
    theme = THEMES[theme_mode]
    bg = weather_bg or theme["bg"]

    root.configure(bg=bg)
    content_canvas.configure(bg=bg, highlightbackground=bg)

    top_frame.configure(bg=theme["card_bg"])
    for w in top_frame.winfo_children():
        if isinstance(w, tk.Label):
            w.configure(bg=theme["card_bg"], fg=theme["fg"])
        elif isinstance(w, tk.Button):
            text = w.cget("text")
            if "Get Weather" in text or "Loading" in text:
                w.configure(bg=theme["accent"], fg="#ffffff", activebackground=theme["accent"])
            else:
                w.configure(bg=theme["card_bg"], fg=theme["fg"], activebackground=theme["card_bg"])

    city_entry.configure(bg=theme["text_bg"], fg=theme["text_fg"], insertbackground=theme["text_fg"])
    last_updated_label.configure(bg=bg, fg=theme["fg"])

    favourites_frame.configure(bg=theme["card_bg"])
    for w in favourites_frame.winfo_children():
        if isinstance(w, tk.Label):
            w.configure(bg=theme["card_bg"], fg=theme["fg"])
        elif isinstance(w, tk.Button):
            w.configure(bg=theme["card_bg"], fg=theme["fg"], activebackground=theme["card_bg"])

    favourites_listbox.configure(bg=theme["text_bg"], fg=theme["text_fg"],
                                 selectbackground=theme["accent"], selectforeground="#ffffff")

    header_frame.configure(bg=theme["card_bg"])
    header_text_frame.configure(bg=theme["card_bg"])
    for w in (icon_label, big_temp_label, location_label, hi_lo_label, micro_summary_label, alert_label):
        w.configure(bg=theme["card_bg"], fg=theme["fg"])

    for frame in (
        current_frame, forecast_frame, ten_day_overview_frame, hourly_frame,
        sun_frame, wind_frame, air_frame,
        moon_frame, story_frame, activities_frame,
        suggestions_frame, wallpaper_frame,
        compare_frame
    ):
        frame.configure(bg=theme["card_bg"], fg=theme["fg"])

    for txt in (current_text, forecast_text, ten_day_overview_text,
                activities_text, suggestions_text,
                story_text, compare_text):
        txt.configure(bg=theme["text_bg"], fg=theme["text_fg"], insertbackground=theme["text_fg"])

    for cv in (
        forecast_canvas, hourly_strip_canvas,
        hourly_temp_canvas, hourly_feels_canvas, hourly_rain_canvas,
        hourly_uv_canvas, hourly_wind_canvas, hourly_humid_canvas, hourly_comfort_canvas,
        sun_canvas, wind_canvas, wallpaper_canvas
    ):
        cv.configure(bg=theme["card_bg"], highlightbackground=theme["card_bg"])

    day_selector_frame.configure(bg=theme["card_bg"])
    day_label.configure(bg=theme["card_bg"], fg=theme["fg"])
    for btn in day_buttons:
        btn.configure(bg=theme["card_bg"], fg=theme["fg"], activebackground=theme["card_bg"])

    sun_text_label.configure(bg=theme["card_bg"], fg=theme["fg"])
    wind_text_label.configure(bg=theme["card_bg"], fg=theme["fg"])
    air_text_label.configure(bg=theme["card_bg"], fg=theme["fg"])
    moon_text_label.configure(bg=theme["card_bg"], fg=theme["fg"])

    footer_label.configure(bg=bg, fg=theme["fg"])
    style_day_buttons()


def toggle_theme() -> None:
    global theme_mode
    theme_mode = "dark" if theme_mode == "light" else "light"
    save_settings()
    apply_theme()
    if last_forecast is not None:
        draw_12day_chart(last_forecast.get("daily") or {})
        redraw_hourly_graphs(last_forecast)
        draw_hourly_strip(last_forecast)
        draw_sunrise_card(last_forecast)
        draw_wind_card(last_forecast)
        draw_air_card(last_air)
        draw_moon_card(last_forecast)
        set_text(story_text, generate_story_text(last_forecast))
        set_text(ten_day_overview_text, generate_12day_overview(last_forecast))
        current = last_forecast.get("current") or {}
        update_wallpaper(current.get("weather_code"), current.get("is_day"))


def toggle_units() -> None:
    global units_mode
    units_mode = "imperial" if units_mode == "metric" else "metric"
    units_button.config(text=f"Units: {'Metric' if units_mode == 'metric' else 'Imperial'}")
    save_settings()
    if last_forecast is not None and last_location is not None:
        render_weather(last_location, last_forecast, last_air)


# ===========================
# SMALL HELPERS
# ===========================

def set_text(widget: tk.Text, text: str) -> None:
    widget.config(state="normal")
    widget.delete("1.0", tk.END)
    widget.insert("1.0", text)
    widget.config(state="disabled")


def format_location(loc: Dict[str, Any]) -> str:
    name = loc.get("name") or ""
    admin1 = loc.get("admin1") or ""
    country = loc.get("country") or ""
    parts = [name]
    if admin1:
        parts.append(admin1)
    if country:
        parts.append(country)
    return ", ".join(parts)


# ===========================
# SETTINGS SAVE/LOAD
# ===========================

def save_settings() -> None:
    data = {
        "theme_mode": theme_mode,
        "units_mode": units_mode,
        "favourites": favourites,
        "last_location": last_location,
        "show_air_panel": show_air_panel,
        "show_comfort_graph": show_comfort_graph,
        "show_story_panel": show_story_panel,
        "show_activities_panel": show_activities_panel,
    }
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


def load_settings() -> None:
    global theme_mode, units_mode, favourites, last_location
    global show_air_panel, show_comfort_graph, show_story_panel, show_activities_panel

    if not os.path.exists(SETTINGS_FILE):
        return
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return

    tm = data.get("theme_mode")
    um = data.get("units_mode")
    fav = data.get("favourites")
    last = data.get("last_location")

    if tm in ("light", "dark"):
        theme_mode = tm
    if um in ("metric", "imperial"):
        units_mode = um

    if isinstance(fav, list):
        favourites.clear()
        for item in fav:
            if isinstance(item, dict) and "latitude" in item and "longitude" in item:
                favourites.append(item)

    if isinstance(last, dict) and "latitude" in last and "longitude" in last:
        last_location = last
    else:
        last_location = None

    s_air = data.get("show_air_panel")
    if isinstance(s_air, bool):
        show_air_panel = s_air
    s_comf = data.get("show_comfort_graph")
    if isinstance(s_comf, bool):
        show_comfort_graph = s_comf
    s_story = data.get("show_story_panel")
    if isinstance(s_story, bool):
        show_story_panel = s_story
    s_act = data.get("show_activities_panel")
    if isinstance(s_act, bool):
        show_activities_panel = s_act


def auto_load_last_location() -> None:
    if last_location is None:
        return
    loc = last_location
    forecast = fetch_weather_cached(loc["latitude"], loc["longitude"], loc["timezone"])
    if not forecast:
        return
    air = fetch_air_quality(loc["latitude"], loc["longitude"], loc["timezone"])
    city_entry.delete(0, tk.END)
    city_entry.insert(0, format_location(loc))
    render_weather(loc, forecast, air)


# ===========================
# SETTINGS DIALOG & PANEL VISIBILITY
# ===========================

def update_panel_visibility() -> None:
    global show_air_panel, show_comfort_graph, show_story_panel, show_activities_panel

    if show_air_panel:
        if not air_frame.winfo_ismapped():
            air_frame.pack(fill="x", padx=10, pady=5)
    else:
        if air_frame.winfo_ismapped():
            air_frame.pack_forget()

    if show_story_panel:
        if not story_frame.winfo_ismapped():
            story_frame.pack(fill="both", padx=10, pady=5)
    else:
        if story_frame.winfo_ismapped():
            story_frame.pack_forget()

    if show_activities_panel:
        if not activities_frame.winfo_ismapped():
            activities_frame.pack(fill="both", padx=10, pady=5)
    else:
        if activities_frame.winfo_ismapped():
            activities_frame.pack_forget()

    if show_comfort_graph:
        if not hourly_comfort_canvas.winfo_ismapped():
            hourly_comfort_canvas.pack(fill="x", pady=3)
    else:
        if hourly_comfort_canvas.winfo_ismapped():
            hourly_comfort_canvas.pack_forget()


def open_settings() -> None:
    global theme_mode, units_mode, show_air_panel, show_comfort_graph, show_story_panel, show_activities_panel

    dialog = tk.Toplevel(root)
    dialog.title("Settings")
    dialog.transient(root)
    dialog.grab_set()

    theme_var = tk.StringVar(value=theme_mode)
    units_var = tk.StringVar(value=units_mode)
    air_var = tk.BooleanVar(value=show_air_panel)
    comfort_var = tk.BooleanVar(value=show_comfort_graph)
    story_var = tk.BooleanVar(value=show_story_panel)
    act_var = tk.BooleanVar(value=show_activities_panel)

    tk.Label(dialog, text="Theme:", font=("Arial", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
    theme_frame = tk.Frame(dialog)
    theme_frame.pack(anchor="w", padx=20)
    tk.Radiobutton(theme_frame, text="Light", variable=theme_var, value="light").pack(side="left", padx=5)
    tk.Radiobutton(theme_frame, text="Dark", variable=theme_var, value="dark").pack(side="left", padx=5)

    tk.Label(dialog, text="Units:", font=("Arial", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
    units_frame = tk.Frame(dialog)
    units_frame.pack(anchor="w", padx=20)
    tk.Radiobutton(units_frame, text="Metric (°C, km/h, mm)", variable=units_var, value="metric").pack(anchor="w")
    tk.Radiobutton(units_frame, text="Imperial (°F, mph, in)", variable=units_var, value="imperial").pack(anchor="w")

    tk.Label(dialog, text="Advanced panels:", font=("Arial", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
    adv_frame = tk.Frame(dialog)
    adv_frame.pack(anchor="w", padx=20, pady=(0, 10))
    tk.Checkbutton(adv_frame, text="Show air quality", variable=air_var).pack(anchor="w")
    tk.Checkbutton(adv_frame, text="Show comfort index graph", variable=comfort_var).pack(anchor="w")
    tk.Checkbutton(adv_frame, text="Show weather story card", variable=story_var).pack(anchor="w")
    tk.Checkbutton(adv_frame, text="Show activities card", variable=act_var).pack(anchor="w")

    def on_ok():
        nonlocal theme_var, units_var, air_var, comfort_var, story_var, act_var

        new_theme = theme_var.get()
        new_units = units_var.get()
        new_air = air_var.get()
        new_comfort = comfort_var.get()
        new_story = story_var.get()
        new_act = act_var.get()

        if new_theme in ("light", "dark") and new_theme != theme_mode:
            globals()["theme_mode"] = new_theme

        if new_units in ("metric", "imperial") and new_units != units_mode:
            globals()["units_mode"] = new_units
            units_button.config(text=f"Units: {'Metric' if new_units == 'metric' else 'Imperial'}")

        globals()["show_air_panel"] = bool(new_air)
        globals()["show_comfort_graph"] = bool(new_comfort)
        globals()["show_story_panel"] = bool(new_story)
        globals()["show_activities_panel"] = bool(new_act)

        save_settings()
        apply_theme()
        update_panel_visibility()
        if last_forecast is not None and last_location is not None:
            render_weather(last_location, last_forecast, last_air)

        dialog.destroy()

    def on_cancel():
        dialog.destroy()

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="OK", width=10, command=on_ok).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Cancel", width=10, command=on_cancel).pack(side="left", padx=5)


# ===========================
# FAVOURITES
# ===========================

def add_favourite() -> None:
    if last_location is None:
        messagebox.showinfo("No location", "Get the weather first, then add to favourites.")
        return
    display = format_location(last_location)
    for f in favourites:
        if format_location(f) == display:
            messagebox.showinfo("Already added", "This place is already in favourites.")
            return
    favourites.append(last_location.copy())
    favourites_listbox.insert(tk.END, display)
    save_settings()


def remove_favourite() -> None:
    sel = favourites_listbox.curselection()
    if not sel:
        return
    idx = sel[0]
    favourites_listbox.delete(idx)
    del favourites[idx]
    save_settings()


def load_selected_favourite(event=None) -> None:
    sel = favourites_listbox.curselection()
    if not sel:
        return
    idx = sel[0]
    loc = favourites[idx]
    forecast = fetch_weather_cached(loc["latitude"], loc["longitude"], loc["timezone"])
    if not forecast:
        return
    air = fetch_air_quality(loc["latitude"], loc["longitude"], loc["timezone"])
    city_entry.delete(0, tk.END)
    city_entry.insert(0, format_location(loc))
    render_weather(loc, forecast, air)


def compare_favourites() -> None:
    if len(favourites) < 2:
        messagebox.showinfo("Compare favourites", "Add at least two favourites first.")
        return

    sel = favourites_listbox.curselection()
    chosen_indices: List[int] = []

    if len(sel) >= 2:
        chosen_indices = list(sel)[:3]
    elif len(sel) == 1:
        messagebox.showinfo("Compare favourites", "Select at least two favourites in the list.")
        return
    else:
        chosen_indices = list(range(min(3, len(favourites))))

    rows = []
    for idx in chosen_indices:
        loc = favourites[idx]
        fc = fetch_weather_cached(loc["latitude"], loc["longitude"], loc["timezone"])
        if not fc:
            continue
        daily = fc.get("daily") or {}
        tmax = (daily.get("temperature_2m_max") or [None])[0]
        tmin = (daily.get("temperature_2m_min") or [None])[0]
        rain_prob = (daily.get("precipitation_probability_max") or [None])[0]
        wind_max = (daily.get("wind_speed_10m_max") or [None])[0]
        uv_max = (daily.get("uv_index_max") or [None])[0]

        rows.append({
            "name": format_location(loc),
            "tmax": tmax,
            "tmin": tmin,
            "rain_prob": rain_prob,
            "wind_max": wind_max,
            "uv_max": uv_max,
        })

    if not rows:
        set_text(compare_text, "No data could be fetched for the selected favourites.")
        return

    lines = []
    lines.append("Comparing today's forecast (uses current units):\n")
    header = f"{'Place':<28} {'High':>10} {'Low':>10} {'Rain%':>7} {'Wind':>11} {'UV':>5}"
    lines.append(header)
    lines.append("-" * len(header))

    for row in rows:
        name = row["name"][:27] + "…" if len(row["name"]) > 28 else row["name"]
        hi = fmt_temp_value(row["tmax"])
        lo = fmt_temp_value(row["tmin"])
        rp = f"{row['rain_prob']:.0f}%" if isinstance(row["rain_prob"], (int, float)) else "N/A"
        wd = fmt_wind_value(row["wind_max"])
        uv = f"{row['uv_max']:.1f}" if isinstance(row["uv_max"], (int, float)) else "N/A"
        line = f"{name:<28} {hi:>10} {lo:>10} {rp:>7} {wd:>11} {uv:>5}"
        lines.append(line)

    result_text = "\n".join(lines)
    set_text(compare_text, result_text)

    theme = THEMES[theme_mode]

    win = tk.Toplevel(root)
    win.title("Compare favourites (today)")
    win.minsize(650, 300)
    win.configure(bg=theme["bg"])

    title_label = tk.Label(
        win,
        text="Compare favourites – today",
        bg=theme["bg"],
        fg=theme["fg"],
        font=("Arial", 12, "bold")
    )
    title_label.pack(anchor="w", padx=12, pady=(10, 4))

    text_frame = tk.Frame(win, bg=theme["bg"])
    text_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    scroll_y = tk.Scrollbar(text_frame, orient="vertical")
    scroll_y.pack(side="right", fill="y")

    txt = tk.Text(
        text_frame,
        wrap="none",
        yscrollcommand=scroll_y.set,
        bg=theme["text_bg"],
        fg=theme["text_fg"],
        font=("Consolas", 11)
    )
    txt.pack(side="left", fill="both", expand=True)
    scroll_y.config(command=txt.yview)

    txt.insert("1.0", result_text)
    txt.config(state="disabled")

    btn_frame = tk.Frame(win, bg=theme["bg"])
    btn_frame.pack(fill="x", pady=(0, 10), padx=12)

    close_btn = tk.Button(
        btn_frame,
        text="✕ Close",
        command=win.destroy,
        bg=theme["card_bg"],
        fg=theme["fg"],
        relief="raised"
    )
    close_btn.pack(side="right")


# ===========================
# 12-DAY CHART (NEW bars)
# ===========================

def draw_12day_chart(daily: Dict[str, Any]) -> None:
    dates = daily.get("time") or []
    tmax = daily.get("temperature_2m_max") or []
    rain_sum = daily.get("precipitation_sum") or []

    forecast_canvas.delete("all")
    n = min(FORECAST_DAYS, len(dates), len(tmax))
    if n < 2:
        return

    temps = [tmax[i] for i in range(n)]
    t_min = min(temps)
    t_max = max(temps)
    if t_max == t_min:
        t_max += 1

    rains = [rain_sum[i] if i < len(rain_sum) and isinstance(rain_sum[i], (int, float)) else 0.0 for i in range(n)]
    r_max = max(rains) if rains else 1.0
    if r_max == 0:
        r_max = 1.0

    width = max(int(forecast_canvas.winfo_width()), 400)
    height = max(int(forecast_canvas.winfo_height()), 180)
    x_pad = 40
    y_pad = 30
    usable_w = width - 2 * x_pad
    usable_h = height - 2 * y_pad

    theme = THEMES[theme_mode]
    axis = theme["fg"]
    line_color = theme["accent"]

    forecast_canvas.create_line(x_pad, y_pad, x_pad, height-y_pad, fill=axis)
    forecast_canvas.create_line(x_pad, height-y_pad, width-x_pad, height-y_pad, fill=axis)

    unit_label = "°C" if units_mode == "metric" else "°F"
    legend_text = f"Line = daily high ({unit_label})"
    forecast_canvas.create_text(width-8, 8, text=legend_text, anchor="ne",
                                fill=axis, font=("Arial", 8, "italic"))

    points = []
    for i in range(n):
        tc = temps[i]
        x = x_pad + usable_w * i / (n-1)
        y = height - y_pad - usable_h * (tc - t_min) / (t_max - t_min)
        points.append((x, y))

    # NEW: precipitation bars
    bar_base_y = height - y_pad
    bar_max_h = usable_h * 0.35
    bar_w = max(6, int(usable_w / n * 0.35))

    for i in range(n):
        x, _ = points[i]
        r = rains[i]
        h_bar = bar_max_h * (r / r_max)
        forecast_canvas.create_rectangle(
            x - bar_w/2, bar_base_y - h_bar,
            x + bar_w/2, bar_base_y,
            fill=line_color, outline=""
        )

    for i in range(n-1):
        x1, y1 = points[i]
        x2, y2 = points[i+1]
        forecast_canvas.create_line(x1, y1, x2, y2, fill=line_color, width=2)

    for i, (x, y) in enumerate(points):
        tc = temps[i]
        date_str = dates[i]
        try:
            dt = datetime.fromisoformat(date_str)
            day_label = dt.strftime("%a")
        except Exception:
            day_label = date_str

        forecast_canvas.create_oval(x-3, y-3, x+3, y+3, fill=line_color, outline=line_color)
        forecast_canvas.create_text(x, y-16, text=temp_point_label(tc), fill=axis,
                                   font=("Arial", 8), anchor="s")
        forecast_canvas.create_text(x, height-y_pad+6, text=day_label, fill=axis,
                                   font=("Arial", 9), anchor="n")


# ===========================
# HOURLY GRAPHS
# ===========================

def draw_hourly_graph(
    canvas: tk.Canvas,
    times: List[str],
    values: List[Optional[float]],
    day_date: Optional[str],
    title: str,
    axis_fmt,
    point_fmt,
    legend: str = "",
) -> None:
    canvas.delete("all")
    if not times or not values:
        return

    if not isinstance(day_date, str):
        return

    xs: List[str] = []
    ys: List[float] = []
    for t, v in zip(times, values):
        if isinstance(t, str) and t.startswith(day_date) and isinstance(v, (int, float)):
            xs.append(t)
            ys.append(float(v))

    if len(xs) < 2:
        return

    vmin = min(ys)
    vmax = max(ys)
    if vmax == vmin:
        vmax += 1

    width = max(int(canvas.winfo_width()), 400)
    height = max(int(canvas.winfo_height()), 110)
    left = 55
    right = 10
    top = 30
    bottom = 24
    usable_w = width - left - right
    usable_h = height - top - bottom

    theme = THEMES[theme_mode]
    fg = theme["fg"]
    line_color = theme["accent"]

    canvas.create_text(left, 10, text=title, anchor="w", fill=fg, font=("Arial", 10, "bold"))
    if legend:
        canvas.create_text(width-10, 10, text=legend, anchor="ne", fill=fg,
                           font=("Arial", 8, "italic"))

    canvas.create_line(left, top, left, top+usable_h, fill=fg)
    canvas.create_line(left, top+usable_h, left+usable_w, top+usable_h, fill=fg)

    canvas.create_text(left-5, top, text=axis_fmt(vmax), anchor="e", fill=fg, font=("Arial", 8))
    canvas.create_text(left-5, top+usable_h, text=axis_fmt(vmin), anchor="e", fill=fg, font=("Arial", 8))

    n = len(xs)
    x_step = usable_w / (n-1)
    points = []
    for i, v in enumerate(ys):
        x = left + i * x_step
        norm = (v - vmin) / (vmax - vmin)
        y = top + (1-norm)*usable_h
        points.append((x, y))

    flat = []
    for x, y in points:
        flat.extend([x, y])
    canvas.create_line(*flat, fill=line_color, width=2, smooth=True)

    for i, (x, y) in enumerate(points):
        v = ys[i]
        canvas.create_oval(x-2, y-2, x+2, y+2, fill=line_color, outline=line_color)
        if i % 3 == 0 or i == n-1:
            canvas.create_text(x, y-8, text=point_fmt(v), fill=fg, font=("Arial", 7), anchor="s")
            t_str = xs[i]
            hhmm = t_str.split("T")[1][:5] if "T" in t_str else t_str
            canvas.create_text(x, height-bottom+3, text=hhmm, fill=fg, font=("Arial", 7), anchor="n")


def redraw_hourly_graphs(forecast: Dict[str, Any]) -> None:
    hourly = forecast.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    feels = hourly.get("apparent_temperature") or []
    rain_probs = hourly.get("precipitation_probability") or []
    uv_vals = hourly.get("uv_index") or []
    wind_vals = hourly.get("wind_speed_10m") or []
    hum_vals = hourly.get("relative_humidity_2m") or []

    day = daily_dates[selected_day_index] if daily_dates and 0 <= selected_day_index < len(daily_dates) else None

    comfort_vals: List[Optional[float]] = []
    for t, temp, hum, wind, uv, rain_p in zip(times, temps, hum_vals, wind_vals, uv_vals, rain_probs):
        if isinstance(temp, (int, float)):
            comfort_vals.append(compute_comfort_index(
                float(temp),
                float(hum) if isinstance(hum, (int, float)) else None,
                float(wind) if isinstance(wind, (int, float)) else None,
                float(uv) if isinstance(uv, (int, float)) else None,
                float(rain_p) if isinstance(rain_p, (int, float)) else None,
            ))
        else:
            comfort_vals.append(None)

    temp_unit = "°C" if units_mode == "metric" else "°F"
    wind_unit = "km/h" if units_mode == "metric" else "mph"

    draw_hourly_graph(
        hourly_temp_canvas, times, temps, day,
        "24 hours – temperature",
        axis_fmt=temp_axis_label,
        point_fmt=temp_point_label,
        legend=f"Line = temperature ({temp_unit})",
    )
    draw_hourly_graph(
        hourly_feels_canvas, times, feels, day,
        "24 hours – feels like",
        axis_fmt=temp_axis_label,
        point_fmt=temp_point_label,
        legend=f"Line = feels-like ({temp_unit})",
    )
    draw_hourly_graph(
        hourly_rain_canvas, times, rain_probs, day,
        "24 hours – rain chance",
        axis_fmt=lambda v: f"{v:.0f}%",
        point_fmt=lambda v: f"{v:.0f}%",
        legend="Line = rain probability (%)",
    )
    draw_hourly_graph(
        hourly_uv_canvas, times, uv_vals, day,
        "24 hours – UV index",
        axis_fmt=lambda v: f"{v:.1f}",
        point_fmt=lambda v: f"{v:.1f}",
        legend="Line = UV index",
    )
    draw_hourly_graph(
        hourly_wind_canvas, times, wind_vals, day,
        "24 hours – wind speed",
        axis_fmt=wind_axis_label,
        point_fmt=wind_point_label,
        legend=f"Line = wind speed ({wind_unit})",
    )
    draw_hourly_graph(
        hourly_humid_canvas, times, hum_vals, day,
        "24 hours – humidity",
        axis_fmt=lambda v: f"{v:.0f}%",
        point_fmt=lambda v: f"{v:.0f}%",
        legend="Line = relative humidity (%)",
    )

    if show_comfort_graph:
        draw_hourly_graph(
            hourly_comfort_canvas, times, comfort_vals, day,
            "24 hours – comfort index",
            axis_fmt=lambda v: f"{v:.0f}/100",
            point_fmt=lambda v: f"{v:.0f}/100",
            legend="Line = comfort (0 awful – 100 perfect)",
        )
    else:
        hourly_comfort_canvas.delete("all")


# ===========================
# HOURLY MINI-STRIP + BEST HOUR
# ===========================

def find_best_hour_for_outdoor(forecast: Dict[str, Any]) -> Optional[str]:
    hourly = forecast.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    rain_probs = hourly.get("precipitation_probability") or []
    wind_vals = hourly.get("wind_speed_10m") or []
    codes = hourly.get("weather_code") or []

    current = forecast.get("current") or {}
    now_time = current.get("time")
    if not isinstance(now_time, str):
        return None
    today = now_time.split("T")[0]

    best_score = -1.0
    best_t = None

    for t, temp, rain, wind, code in zip(times, temps, rain_probs, wind_vals, codes):
        if not isinstance(t, str) or not t.startswith(today):
            continue
        if not isinstance(temp, (int, float)):
            continue

        temp_c = float(temp)
        rain_p = float(rain) if isinstance(rain, (int, float)) else 0.0
        wind_kmh = float(wind) if isinstance(wind, (int, float)) else 0.0
        code_i = int(code) if isinstance(code, (int, float)) else 0

        score = 100.0

        if rain_p >= 70 or code_i >= 95:
            score -= 70
        elif rain_p >= 40:
            score -= 40
        elif rain_p >= 20:
            score -= 15

        ideal = 19.0
        score -= min(50, abs(temp_c - ideal) * 2.5)

        if wind_kmh > 50:
            score -= 30
        elif wind_kmh > 35:
            score -= 15
        elif wind_kmh > 25:
            score -= 5

        if code_i in (3, 45, 48):
            score -= 5

        if score > best_score:
            best_score = score
            best_t = t

    if best_score < 40:
        return None
    return best_t


def draw_hourly_strip(forecast: Dict[str, Any]) -> None:
    hourly = forecast.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    rain_probs = hourly.get("precipitation_probability") or []
    codes = hourly.get("weather_code") or []

    hourly_strip_canvas.delete("all")
    day = daily_dates[selected_day_index] if daily_dates and 0 <= selected_day_index < len(daily_dates) else None
    if not isinstance(day, str) or not times:
        return

    xs: List[str] = []
    temp_vals: List[float] = []
    rain_vals: List[float] = []
    code_vals: List[int] = []

    for t, temp, rain_p, code in zip(times, temps, rain_probs, codes):
        if isinstance(t, str) and t.startswith(day) and isinstance(temp, (int, float)):
            xs.append(t)
            temp_vals.append(float(temp))
            rain_vals.append(float(rain_p) if isinstance(rain_p, (int, float)) else 0.0)
            code_vals.append(int(code) if isinstance(code, (int, float)) else 0)

    if not xs:
        return

    col_width = 70
    height = 90
    margin = 10
    total_width = margin + len(xs)*col_width

    hourly_strip_canvas.config(scrollregion=(0, 0, total_width, height))

    theme = THEMES[theme_mode]
    fg = theme["fg"]
    accent = theme["accent"]

    best_day_prefix = None
    if best_hour_time and "T" in best_hour_time:
        best_day_prefix = best_hour_time.split("T")[0]

    for i, t in enumerate(xs):
        x0 = margin + i*col_width
        x1 = x0 + col_width
        x_center = x0 + col_width/2
        hhmm = t.split("T")[1][:5] if "T" in t else t

        temp_c = temp_vals[i]
        temp_label = temp_point_label(temp_c)
        rain_p = rain_vals[i]
        code = code_vals[i]

        if best_hour_time and t == best_hour_time and day == best_day_prefix:
            hourly_strip_canvas.create_rectangle(
                x0+2, 5, x1-2, height-5,
                outline=accent, width=2
            )

        hourly_strip_canvas.create_text(x_center, 10, text=hhmm, anchor="n", fill=fg, font=("Arial", 8))
        hourly_strip_canvas.create_text(x_center, 26, text=weather_icon(code), anchor="n",
                                        font=("Segoe UI Emoji", 14))
        hourly_strip_canvas.create_text(x_center, 48, text=temp_label, anchor="n", fill=fg, font=("Arial", 8))
        hourly_strip_canvas.create_text(x_center, 68, text=f"{rain_p:.0f}%", anchor="n", fill=fg, font=("Arial", 7))


# ===========================
# DAILY TEXT
# ===========================

def build_daily_text(forecast: Dict[str, Any]) -> str:
    daily = forecast.get("daily") or {}
    hourly = forecast.get("hourly") or {}

    dates = daily.get("time") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    app_max = daily.get("apparent_temperature_max") or []
    app_min = daily.get("apparent_temperature_min") or []
    uvmax = daily.get("uv_index_max") or []
    rain_sum = daily.get("precipitation_sum") or []
    rain_prob = daily.get("precipitation_probability_max") or []
    wind_max = daily.get("wind_speed_10m_max") or []
    codes = daily.get("weather_code") or []
    sunrise = daily.get("sunrise") or []
    sunset = daily.get("sunset") or []

    h_times = hourly.get("time") or []
    h_hum = hourly.get("relative_humidity_2m") or []

    lines: List[str] = []
    n = min(FORECAST_DAYS, len(dates))

    for i in range(n):
        date_str = dates[i]
        try:
            dt = datetime.fromisoformat(date_str)
            day_label = dt.strftime("%a %d %b")
        except Exception:
            day_label = date_str

        code = codes[i] if i < len(codes) else None
        tmax_i = tmax[i] if i < len(tmax) else None
        tmin_i = tmin[i] if i < len(tmin) else None
        app_max_i = app_max[i] if i < len(app_max) else None
        app_min_i = app_min[i] if i < len(app_min) else None
        uv_i = uvmax[i] if i < len(uvmax) else None
        rain_i = rain_sum[i] if i < len(rain_sum) else None
        prob_i = rain_prob[i] if i < len(rain_prob) else None
        wind_i = wind_max[i] if i < len(wind_max) else None

        hum_vals = [
            h for t, h in zip(h_times, h_hum)
            if isinstance(t, str) and t.startswith(date_str) and isinstance(h, (int, float))
        ]
        hum_avg = sum(hum_vals)/len(hum_vals) if hum_vals else None

        sr = sunrise[i].split("T")[1] if i < len(sunrise) and isinstance(sunrise[i], str) else "N/A"
        ss = sunset[i].split("T")[1] if i < len(sunset) and isinstance(sunset[i], str) else "N/A"

        lines.append(f"{day_label}: {weather_icon(code)} {weather_text(code)}")
        lines.append(f"  Max temp:    {fmt_temp_value(tmax_i)}")
        lines.append(f"  Min temp:    {fmt_temp_value(tmin_i)}")
        lines.append(f"  Feels max:   {fmt_temp_value(app_max_i)}")
        lines.append(f"  Feels min:   {fmt_temp_value(app_min_i)}")
        if hum_avg is not None:
            lines.append(f"  Avg humidity:{hum_avg:.0f} %")
        if uv_i is not None:
            lines.append(f"  UV max:      {uv_i:.1f} ({interpret_uv(uv_i)})")
        if rain_i is not None:
            extra = f" (chance {prob_i:.0f}%)" if isinstance(prob_i, (int, float)) else ""
            lines.append(f"  Rain:        {fmt_rain_value(rain_i)}{extra}")
        if wind_i is not None:
            lines.append(f"  Max wind:    {fmt_wind_value(wind_i)}")
        lines.append(f"  Sunrise:     {sr}   |   Sunset: {ss}")
        lines.append("")

    return "\n".join(lines) if lines else "No forecast data."


# ===========================
# 12-DAY OVERVIEW & EXTREMES
# ===========================

def generate_12day_overview(forecast: Dict[str, Any]) -> str:
    daily = forecast.get("daily") or {}
    dates = daily.get("time") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    rain_sum = daily.get("precipitation_sum") or []
    wind_max = daily.get("wind_speed_10m_max") or []
    codes = daily.get("weather_code") or []

    n = min(FORECAST_DAYS, len(dates))
    if n == 0:
        return "No forecast available."

    days: List[Dict[str, Any]] = []
    for i in range(n):
        date_str = dates[i]
        try:
            dt = datetime.fromisoformat(date_str)
            label = dt.strftime("%a %d %b")
        except Exception:
            dt = None
            label = date_str
        days.append({
            "index": i,
            "date": date_str,
            "label": label,
            "dt": dt,
            "tmax": tmax[i] if i < len(tmax) else None,
            "tmin": tmin[i] if i < len(tmin) else None,
            "rain": rain_sum[i] if i < len(rain_sum) else None,
            "wind": wind_max[i] if i < len(wind_max) else None,
            "code": codes[i] if i < len(codes) else None,
        })

    high_vals = [d["tmax"] for d in days if isinstance(d["tmax"], (int, float))]
    low_vals = [d["tmin"] for d in days if isinstance(d["tmin"], (int, float))]
    rain_vals = [d["rain"] for d in days if isinstance(d["rain"], (int, float))]
    wind_vals = [d["wind"] for d in days if isinstance(d["wind"], (int, float))]

    lines: List[str] = []
    lines.append(f"{FORECAST_DAYS}-day overview:")

    if high_vals and low_vals:
        overall_high = max(high_vals)
        overall_low = min(low_vals)
        lines.append(f"• Temperatures range roughly from {fmt_temp_value(overall_low)} to {fmt_temp_value(overall_high)}.")
    elif high_vals:
        overall_high = max(high_vals)
        lines.append(f"• Highs up to about {fmt_temp_value(overall_high)}.")
    elif low_vals:
        overall_low = min(low_vals)
        lines.append(f"• Lows down to about {fmt_temp_value(overall_low)}.")
    else:
        lines.append("• Temperature range: N/A.")

    if len(high_vals) >= 2:
        early = high_vals[: min(3, len(high_vals))]
        late = high_vals[-min(3, len(high_vals)):]
        early_avg = sum(early)/len(early)
        late_avg = sum(late)/len(late)
        diff = late_avg - early_avg

        if abs(diff) < 1.0:
            trend = "stays fairly similar from the start to the end of the period."
        elif diff > 0:
            trend = "slowly turns milder towards the end of the period."
        else:
            trend = "gradually cools down towards the end of the period."
        lines.append(f"• Trend: it {trend}")
    else:
        lines.append("• Trend: not enough data to judge.")

    if rain_vals:
        total_rain = sum(rain_vals)
        if total_rain < 2:
            rain_line = "mostly dry, only small amounts of rain expected."
        elif total_rain < 10:
            rain_line = "a few showery days, but also dry spells."
        else:
            rain_line = "several wetter days mixed into the period."
        lines.append(f"• Rain character: {rain_line}")
    else:
        lines.append("• Rain character: no rain totals available.")

    lines.append("")
    lines.append("Notable days:")

    warmest_day = max(days, key=lambda d: d["tmax"] if isinstance(d["tmax"], (int, float)) else -999)
    coldest_day = min(days, key=lambda d: d["tmin"] if isinstance(d["tmin"], (int, float)) else 999)
    wettest_day = max(days, key=lambda d: d["rain"] if isinstance(d["rain"], (int, float)) else -1)
    windiest_day = max(days, key=lambda d: d["wind"] if isinstance(d["wind"], (int, float)) else -1)

    if isinstance(warmest_day["tmax"], (int, float)):
        lines.append(f"• Warmest: {warmest_day['label']} – {fmt_temp_value(warmest_day['tmax'])}.")
    if isinstance(coldest_day["tmin"], (int, float)):
        lines.append(f"• Coldest: {coldest_day['label']} – {fmt_temp_value(coldest_day['tmin'])}.")
    if isinstance(wettest_day["rain"], (int, float)):
        lines.append(f"• Wettest: {wettest_day['label']} – {fmt_rain_value(wettest_day['rain'])}.")
    if isinstance(windiest_day["wind"], (int, float)):
        lines.append(f"• Windiest: {windiest_day['label']} – gusts up to {fmt_wind_value(windiest_day['wind'])}.")

    lines.append("")
    avg_high = sum(high_vals)/len(high_vals) if high_vals else None
    if avg_high is not None:
        if avg_high <= 5:
            temp_word = "mostly cold"
        elif avg_high <= 12:
            temp_word = "rather cool"
        elif avg_high <= 20:
            temp_word = "mild"
        elif avg_high <= 27:
            temp_word = "warm"
        else:
            temp_word = "quite hot"
    else:
        temp_word = "mixed"

    rain_word = "with several wet days." if rain_vals and sum(rain_vals) > 8 else \
                "with occasional showers." if rain_vals and sum(rain_vals) > 2 else \
                "and often dry."

    lines.append(f"Headline: The next {FORECAST_DAYS} days look {temp_word} {rain_word}")

    return "\n".join(lines)


# ===========================
# WEATHER STORY CARD (unchanged)
# ===========================

def generate_story_text(forecast: Dict[str, Any]) -> str:
    daily = forecast.get("daily") or {}
    hourly = forecast.get("hourly") or {}
    current = forecast.get("current") or {}

    dates = daily.get("time") or []
    codes = daily.get("weather_code") or []
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    uvmax = daily.get("uv_index_max") or []
    rain_prob_max = daily.get("precipitation_probability_max") or []

    h_times = hourly.get("time") or []
    h_temps = hourly.get("temperature_2m") or []
    h_rain = hourly.get("precipitation_probability") or []
    h_codes = hourly.get("weather_code") or []

    now_str = current.get("time")
    today = None
    if isinstance(now_str, str) and "T" in now_str:
        today = now_str.split("T")[0]
    elif dates:
        today = dates[0]

    lines: List[str] = []

    def slice_hours(start_h: int, end_h: int):
        temps, rains, codes_ = [], [], []
        for t, temp, r, c in zip(h_times, h_temps, h_rain, h_codes):
            if not isinstance(t, str) or not isinstance(temp, (int, float)):
                continue
            if not today or not t.startswith(today):
                continue
            hh = int(t.split("T")[1][:2])
            if start_h <= hh < end_h:
                temps.append(float(temp))
                rains.append(float(r) if isinstance(r, (int, float)) else 0.0)
                codes_.append(int(c) if isinstance(c, (int, float)) else 0)
        return temps, rains, codes_

    def describe_period(name: str, start_h: int, end_h: int):
        temps, rains, codes_ = slice_hours(start_h, end_h)
        if not temps:
            return f"{name}: No data.\n"

        avg_temp = sum(temps) / len(temps)
        max_rain = max(rains) if rains else 0.0
        common_code = codes_[0] if codes_ else None

        desc_parts = []
        if avg_temp <= 5:
            desc_parts.append("very cold")
        elif avg_temp <= 12:
            desc_parts.append("chilly")
        elif avg_temp <= 20:
            desc_parts.append("cool to mild")
        elif avg_temp <= 27:
            desc_parts.append("warm")
        else:
            desc_parts.append("hot")

        if max_rain >= 70:
            desc_parts.append("with frequent showers")
        elif max_rain >= 40:
            desc_parts.append("with some showers around")
        elif max_rain >= 20:
            desc_parts.append("with a small chance of showers")
        else:
            desc_parts.append("mostly dry")

        if common_code is not None:
            desc_parts.append(f"({weather_text(common_code).lower()})")

        return f"{name}: {' '.join(desc_parts)}, around {temp_point_label(avg_temp)}.\n"

    lines.append("Today’s story:")
    if today:
        lines.append(describe_period("Morning", 6, 12).strip())
        lines.append(describe_period("Afternoon", 12, 18).strip())
        lines.append(describe_period("Evening", 18, 24).strip())
    else:
        lines.append("No hourly data to build today’s story.")

    lines.append("")
    lines.append("Next few days:")
    n = min(4, len(dates))
    if n >= 2:
        for i in range(n):
            date_str = dates[i]
            try:
                dt = datetime.fromisoformat(date_str)
                day_label = dt.strftime("%a")
            except Exception:
                day_label = date_str
            code = codes[i] if i < len(codes) else None
            tmax_i = tmax[i] if i < len(tmax) else None
            tmin_i = tmin[i] if i < len(tmin) else None
            rain_p = rain_prob_max[i] if i < len(rain_prob_max) else None
            if isinstance(rain_p, (int, float)):
                lines.append(
                    f"{day_label}: {weather_icon(code)} {weather_text(code)}, "
                    f"{fmt_temp_value(tmin_i)} – {fmt_temp_value(tmax_i)}, "
                    f"rain chance {rain_p:.0f}%"
                )
            else:
                lines.append(
                    f"{day_label}: {weather_icon(code)} {weather_text(code)}, "
                    f"{fmt_temp_value(tmin_i)} – {fmt_temp_value(tmax_i)}"
                )
    else:
        lines.append("Not enough forecast data for a multi-day summary.")

    if uvmax:
        uv = uvmax[0]
        if isinstance(uv, (int, float)):
            lines.append("")
            lines.append(f"UV today: {uv:.1f} ({interpret_uv(uv)}).")
            if uv >= 7:
                lines.append("Afternoons are quite bright – sunscreen and sunglasses strongly recommended.")
            elif uv >= 4:
                lines.append("Some sun protection is a good idea if you’re outside for longer periods.")

    return "\n".join(lines)


# ===========================
# SUNRISE / SUNSET CARD
# ===========================

def draw_sunrise_card(forecast: Dict[str, Any]) -> None:
    sun_canvas.delete("all")
    daily = forecast.get("daily") or {}
    current = forecast.get("current") or {}

    sunrise_list = daily.get("sunrise") or []
    sunset_list = daily.get("sunset") or []
    if not sunrise_list or not sunset_list:
        sun_text_label.config(text="No sunrise/sunset data.")
        return

    sunrise_str = sunrise_list[0]
    sunset_str = sunset_list[0]
    try:
        sunrise_dt = datetime.fromisoformat(sunrise_str)
        sunset_dt = datetime.fromisoformat(sunset_str)
    except Exception:
        sun_text_label.config(text="Sunrise/sunset time format error.")
        return

    daylight = sunset_dt - sunrise_dt
    hours = daylight.seconds // 3600
    mins = (daylight.seconds // 60) % 60

    text = f"Sunrise: {sunrise_str.split('T')[1]}   |   Sunset: {sunset_str.split('T')[1]}   |   Daylight: {hours} h {mins} min"
    sun_text_label.config(text=text)

    now_str = current.get("time")
    width = max(int(sun_canvas.winfo_width()), 400)
    height = max(int(sun_canvas.winfo_height()), 40)
    margin = 30
    theme = THEMES[theme_mode]
    fg = theme["fg"]
    accent = theme["accent"]

    sun_canvas.create_line(margin, height/2, width-margin, height/2, fill=fg, width=4)
    sun_canvas.create_oval(margin-4, height/2-4, margin+4, height/2+4, fill=fg, outline=fg)
    sun_canvas.create_oval(width-margin-4, height/2-4, width-margin+4, height/2+4, fill=fg, outline=fg)

    if isinstance(now_str, str):
        try:
            now_dt = datetime.fromisoformat(now_str)
            if sunrise_dt <= now_dt <= sunset_dt:
                frac = (now_dt - sunrise_dt).total_seconds() / daylight.total_seconds()
                frac = max(0.0, min(1.0, frac))
                x_now = margin + frac*(width-2*margin)
                sun_canvas.create_line(margin, height/2, x_now, height/2, fill=accent, width=4)
                sun_canvas.create_oval(x_now-5, height/2-5, x_now+5, height/2+5, fill=accent, outline=accent)
            elif now_dt > sunset_dt:
                sun_canvas.create_line(margin, height/2, width-margin, height/2, fill=accent, width=4)
        except Exception:
            pass


# ===========================
# WIND CARD
# ===========================

def draw_wind_card(forecast: Dict[str, Any]) -> None:
    wind_canvas.delete("all")
    current = forecast.get("current") or {}
    daily = forecast.get("daily") or {}

    wind_spd = current.get("wind_speed_10m")
    wind_dir = current.get("wind_direction_10m")
    wind_max_list = daily.get("wind_speed_10m_max") or []
    wind_max = wind_max_list[0] if wind_max_list else None

    dir_text = "N/A"
    if isinstance(wind_dir, (int, float)):
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = int((wind_dir % 360) / 45) % 8
        dir_text = f"{dirs[idx]} ({wind_dir:.0f}°)"

    lines = []
    lines.append(f"Current wind: {fmt_wind_value(wind_spd)} from {dir_text}")
    if isinstance(wind_max, (int, float)):
        lines.append(f"Max wind today: {fmt_wind_value(wind_max)}")
    else:
        lines.append("Max wind today: N/A")

    if isinstance(wind_spd, (int, float)):
        if wind_spd >= 60:
            lines.append("Feels: very windy / gusty – take care cycling and with loose objects.")
        elif wind_spd >= 35:
            lines.append("Feels: breezy to windy – will feel cooler than the thermometer.")
        else:
            lines.append("Feels: light to moderate breeze.")
    wind_text_label.config(text="\n".join(lines))

    width = max(int(wind_canvas.winfo_width()), 140)
    height = max(int(wind_canvas.winfo_height()), 140)
    cx, cy = width//2, height//2
    r = min(width, height)//2 - 20

    theme = THEMES[theme_mode]
    fg = theme["fg"]
    accent = theme["accent"]

    wind_canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=fg)
    wind_canvas.create_text(cx, cy-r-8, text="N", fill=fg, font=("Arial", 9))
    wind_canvas.create_text(cx+r+8, cy, text="E", fill=fg, font=("Arial", 9))
    wind_canvas.create_text(cx, cy+r+8, text="S", fill=fg, font=("Arial", 9))
    wind_canvas.create_text(cx-r-8, cy, text="W", fill=fg, font=("Arial", 9))

    if isinstance(wind_dir, (int, float)):
        angle_deg = wind_dir - 90
        angle_rad = math.radians(angle_deg)
        x_end = cx + r * math.cos(angle_rad)
        y_end = cy + r * math.sin(angle_rad)
        wind_canvas.create_line(cx, cy, x_end, y_end, fill=accent, width=3, arrow=tk.LAST)


# ===========================
# AIR QUALITY CARD
# ===========================

def draw_air_card(air: Optional[Dict[str, Any]]) -> None:
    if not air:
        air_text_label.config(text="No air quality data available.")
        return
    eu_aqi = air.get("european_aqi")
    us_aqi = air.get("us_aqi")

    eu_desc = interpret_aqi_eu(eu_aqi) if eu_aqi is not None else "N/A"
    us_desc = interpret_aqi_us(us_aqi) if us_aqi is not None else "N/A"

    lines = []
    if eu_aqi is not None:
        lines.append(f"European AQI: {eu_aqi:.0f} ({eu_desc})")
    else:
        lines.append("European AQI: N/A")
    if us_aqi is not None:
        lines.append(f"US AQI:       {us_aqi:.0f} ({us_desc})")
    else:
        lines.append("US AQI:       N/A")

    low = (us_desc if us_aqi is not None else eu_desc).lower()
    if any(w in low for w in ("unhealthy", "poor", "hazard")):
        lines.append("Tip: limit heavy outdoor exercise if you have heart or lung conditions.")
    else:
        lines.append("Tip: air quality is okay for normal outdoor plans.")

    air_text_label.config(text="\n".join(lines))


# ===========================
# MOON PHASE CARD
# ===========================

def moon_phase_info(date: datetime) -> (str, str):
    known_new = datetime(2000, 1, 6)
    days = (date - known_new).total_seconds() / 86400.0
    synodic = 29.53058867
    phase = days % synodic
    frac = phase / synodic

    if frac < 0.03 or frac > 0.97:
        return "🌑", "New moon"
    elif frac < 0.22:
        return "🌒", "Waxing crescent"
    elif frac < 0.28:
        return "🌓", "First quarter"
    elif frac < 0.47:
        return "🌔", "Waxing gibbous"
    elif frac < 0.53:
        return "🌕", "Full moon"
    elif frac < 0.72:
        return "🌖", "Waning gibbous"
    elif frac < 0.78:
        return "🌗", "Last quarter"
    else:
        return "🌘", "Waning crescent"


def draw_moon_card(forecast: Dict[str, Any]) -> None:
    current = forecast.get("current") or {}
    now_str = current.get("time")
    if isinstance(now_str, str):
        try:
            now_dt = datetime.fromisoformat(now_str)
        except Exception:
            now_dt = datetime.now()
    else:
        now_dt = datetime.now()

    emoji, desc = moon_phase_info(now_dt)
    moon_text_label.config(
        text=f"Today: {emoji} {desc}\n"
             f"Date: {now_dt.strftime('%Y-%m-%d')}"
    )


# ===========================
# ACTIVITIES CARD (NEW best hours)
# ===========================

def rank_activity_hours(forecast: Dict[str, Any]) -> str:
    hourly = forecast.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    rain_probs = hourly.get("precipitation_probability") or []
    uv_vals = hourly.get("uv_index") or []
    wind_vals = hourly.get("wind_speed_10m") or []
    codes = hourly.get("weather_code") or []

    current = forecast.get("current") or {}
    now_time = current.get("time")
    if not isinstance(now_time, str):
        return "No hourly ranking available."
    today = now_time.split("T")[0]

    scored = []
    for t, temp, rain, uv, wind, code in zip(times, temps, rain_probs, uv_vals, wind_vals, codes):
        if not isinstance(t, str) or not t.startswith(today):
            continue
        if not isinstance(temp, (int, float)):
            continue

        comfort = compute_comfort_index(
            float(temp),
            None,
            float(wind) if isinstance(wind, (int, float)) else None,
            float(uv) if isinstance(uv, (int, float)) else None,
            float(rain) if isinstance(rain, (int, float)) else None
        ) or 0.0

        rain_p = float(rain) if isinstance(rain, (int, float)) else 0.0
        uv_v = float(uv) if isinstance(uv, (int, float)) else 0.0
        wind_k = float(wind) if isinstance(wind, (int, float)) else 0.0
        code_i = int(code) if isinstance(code, (int, float)) else 0

        # Walk score: comfort heavy, rain heavy, wind moderate
        walk_score = comfort - rain_p*0.6 - max(0, wind_k-25)*0.4

        # Sport/running score: comfort + cooler bias, penalize high UV/rain
        sport_score = comfort - rain_p*0.7 - max(0, uv_v-5)*4

        # Stargazing: prefer clear/mostly clear, low rain, evening/night hours
        hh = int(t.split("T")[1][:2])
        sky_bonus = 20 if code_i in (0, 1) else 5 if code_i in (2,) else -10
        night_bonus = 15 if (hh >= 19 or hh <= 5) else 0
        star_score = sky_bonus + night_bonus - rain_p*0.8

        scored.append((t, walk_score, sport_score, star_score))

    if not scored:
        return "No hourly ranking available."

    def top3(idx):
        best = sorted(scored, key=lambda x: x[idx], reverse=True)[:3]
        return [b[0].split("T")[1][:5] for b in best]

    walk_best = top3(1)
    sport_best = top3(2)
    star_best = top3(3)

    return (
        "Best hours today (local time):\n"
        f"• Walking / park: {', '.join(walk_best)}\n"
        f"• Sport / running: {', '.join(sport_best)}\n"
        f"• Stargazing: {', '.join(star_best)}"
    )


def generate_activities_text(forecast: Dict[str, Any], best_hour: Optional[str]) -> str:
    daily = forecast.get("daily") or {}
    current = forecast.get("current") or {}

    temp_c = current.get("temperature_2m")
    feels_c = current.get("apparent_temperature")

    uvmax = daily.get("uv_index_max") or []
    uv_today = uvmax[0] if uvmax else None

    rain_prob_daily = daily.get("precipitation_probability_max") or []
    rain_prob_today = rain_prob_daily[0] if rain_prob_daily else None

    wind_daily = daily.get("wind_speed_10m_max") or []
    wind_today = wind_daily[0] if wind_daily else None

    codes_daily = daily.get("weather_code") or []
    code_today = codes_daily[0] if codes_daily else current.get("weather_code")

    lines: List[str] = []
    lines.append("General outdoor comfort:")

    base_temp = feels_c if feels_c is not None else temp_c
    if base_temp is None:
        lines.append("• Temperature data missing – judge by how it feels.")
    else:
        if base_temp <= 3:
            lines.append("• Feels very cold – short outdoor trips are fine, but wrap up well.")
        elif base_temp <= 10:
            lines.append("• Cool – good for walks and light activity with a coat.")
        elif base_temp <= 24:
            lines.append("• Comfortable – great for most outdoor activities.")
        elif base_temp <= 30:
            lines.append("• Warm – good, but drink water and avoid pushing too hard.")
        else:
            lines.append("• Hot – avoid intense activity in the middle of the day, seek shade.")

    if best_hour and "T" in best_hour:
        hhmm = best_hour.split("T")[1][:5]
        lines.append(f"\n⭐ Nice outdoor hour today: around {hhmm} (local time).")
    else:
        lines.append("\n⭐ No single perfect hour found today – pick your favourite calmer period.")

    lines.append("\nWalking / park:")
    if isinstance(rain_prob_today, (int, float)) and rain_prob_today < 40 and base_temp and 5 <= base_temp <= 25:
        lines.append("• Rating: 👍 Great – comfortable temps and not too wet.")
    elif isinstance(rain_prob_today, (int, float)) and rain_prob_today >= 70:
        lines.append("• Rating: ⚠️ Tricky – walks may be wet, check the radar and bring waterproofs.")
    else:
        lines.append("• Rating: 🙂 Okay – mixed conditions, choose your time.")

    lines.append("\nSports / running:")
    if isinstance(wind_today, (int, float)) and wind_today > 60:
        lines.append("• Rating: ⚠️ Windy – running or cycling will feel hard, consider shorter sessions.")
    elif isinstance(uv_today, (int, float)) and uv_today >= 7:
        lines.append("• Rating: 🙂 Good but bright – great for sport with sun protection and plenty of water.")
    else:
        lines.append("• Rating: 👍 Generally good for outdoor exercise for most people.")

    lines.append("\nStargazing tonight:")
    current_code = code_today
    if isinstance(current_code, int):
        if current_code in (0, 1):
            lines.append("• Rating: 🌟 Great – clear or mainly clear skies if light pollution is low.")
        elif current_code in (2, 3):
            lines.append("• Rating: 😐 Limited – cloud cover may block stars.")
        elif current_code in (45, 48):
            lines.append("• Rating: 👎 Poor – fog or mist will reduce visibility.")
        else:
            lines.append("• Rating: 👎 Not ideal – precipitation or unsettled weather.")
    else:
        lines.append("• Rating: ? – sky condition unknown, check visually tonight.")

    # NEW ranking block
    lines.append("\n" + rank_activity_hours(forecast))

    return "\n".join(lines)


# ===========================
# DAY SELECTOR
# ===========================

def update_day_selector(daily: Dict[str, Any]) -> None:
    global daily_dates, day_buttons, selected_day_index
    daily_dates = daily.get("time") or []

    for b in day_buttons:
        b.destroy()
    day_buttons = []

    if not daily_dates:
        return

    selected_day_index = 0
    max_days = min(FORECAST_DAYS, len(daily_dates))
    for idx in range(max_days):
        date_str = daily_dates[idx]
        try:
            dt = datetime.fromisoformat(date_str)
            label = dt.strftime("%a")
        except Exception:
            label = f"D{idx+1}"
        btn = tk.Button(
            day_selector_frame,
            text=label,
            command=lambda i=idx: on_day_button_click(i),
            width=6,
            height=2,
            font=("Arial", 11, "bold")
        )
        btn.pack(side="left", padx=2)
        day_buttons.append(btn)

    apply_theme()
    style_day_buttons()


def on_day_button_click(idx: int) -> None:
    global selected_day_index
    selected_day_index = idx
    style_day_buttons()
    if last_forecast is not None:
        redraw_hourly_graphs(last_forecast)
        draw_hourly_strip(last_forecast)


# ===========================
# SMART HEADER MICRO-SUMMARY (NEW)
# ===========================

def build_micro_summary(temp_c, feels_c, rain_prob, wind_kmh, code, best_hour) -> str:
    parts = []
    base = feels_c if feels_c is not None else temp_c

    if isinstance(base, (int, float)):
        if base <= 5: parts.append("Very cold")
        elif base <= 12: parts.append("Chilly")
        elif base <= 20: parts.append("Cool")
        elif base <= 27: parts.append("Mild")
        else: parts.append("Warm")

    if isinstance(wind_kmh, (int, float)) and wind_kmh >= 25:
        parts.append("breezy")

    if isinstance(rain_prob, (int, float)) and rain_prob >= 40:
        parts.append("rain possible")

    if isinstance(code, int) and code >= 95:
        parts.append("storm risk")

    line = ", ".join(parts) if parts else "Mixed conditions"
    if best_hour and "T" in best_hour:
        line += f". Best outdoors ~{best_hour.split('T')[1][:5]}"
    return line


# ===========================
# RENDERING
# ===========================

def render_weather(loc: Dict[str, Any],
                   forecast: Dict[str, Any],
                   air: Optional[Dict[str, Any]]) -> None:
    global last_forecast, last_location, last_air, weather_bg, best_hour_time
    last_forecast = forecast
    last_location = loc
    last_air = air

    current = forecast.get("current") or {}
    daily = forecast.get("daily") or {}
    hourly = forecast.get("hourly") or {}

    location_label.config(text="Location: " + format_location(loc))

    temp_c = current.get("temperature_2m")
    feels_c = current.get("apparent_temperature")
    hum = current.get("relative_humidity_2m")
    press = current.get("pressure_msl")
    wind_spd = current.get("wind_speed_10m")
    wind_dir = current.get("wind_direction_10m")
    precip = current.get("precipitation")
    rain = current.get("rain")
    code = current.get("weather_code")
    is_day = current.get("is_day")
    now_time = current.get("time")

    icon_label.config(text=weather_icon(code))
    big_temp_label.config(text=fmt_temp_value(temp_c))

    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    hi = fmt_temp_value(tmax[0]) if tmax else "N/A"
    lo = fmt_temp_value(tmin[0]) if tmin else "N/A"
    hi_lo_label.config(text=f"Today: High {hi}   •   Low {lo}")

    h_times = hourly.get("time") or []
    h_hum = hourly.get("relative_humidity_2m") or []
    day_str = now_time.split("T")[0] if isinstance(now_time, str) else None
    hum_values = [
        h for t, h in zip(h_times, h_hum)
        if isinstance(t, str) and day_str and t.startswith(day_str) and isinstance(h, (int, float))
    ]
    hum_avg_today = sum(hum_values) / len(hum_values) if hum_values else hum

    lines: List[str] = []
    if now_time:
        lines.append(f"Local time: {now_time}")
    lines.append(f"Condition: {weather_text(code)}")
    lines.append("")
    lines.append(f"Temperature: {fmt_temp_value(temp_c)}")
    lines.append(f"Feels like:  {fmt_temp_value(feels_c)}")
    lines.append(f"Humidity:    {hum:.0f} %" if isinstance(hum, (int, float)) else "Humidity:    N/A")
    if isinstance(press, (int, float)):
        lines.append(f"Pressure:    {press:.0f} hPa")
    else:
        lines.append("Pressure:    N/A")
    if isinstance(wind_spd, (int, float)):
        wd = f"{wind_dir:.0f}°" if isinstance(wind_dir, (int, float)) else "?"
        lines.append(f"Wind:        {fmt_wind_value(wind_spd)} (dir {wd})")
    else:
        lines.append("Wind:        N/A")
    if isinstance(precip, (int, float)):
        lines.append(f"Precip now:  {fmt_rain_value(precip)}")
    if isinstance(rain, (int, float)):
        lines.append(f"Rain now:    {fmt_rain_value(rain)}")

    set_text(current_text, "\n".join(lines))

    set_text(forecast_text, build_daily_text(forecast))
    draw_12day_chart(daily)

    overview = generate_12day_overview(forecast)
    set_text(ten_day_overview_text, overview)

    update_day_selector(daily)
    redraw_hourly_graphs(forecast)

    best = find_best_hour_for_outdoor(forecast)
    best_hour_time = best
    draw_hourly_strip(forecast)

    draw_air_card(air)

    uv_daily = daily.get("uv_index_max") or []
    uv_today = uv_daily[0] if uv_daily else None
    rain_prob_daily = daily.get("precipitation_probability_max") or []
    rain_prob_today = rain_prob_daily[0] if rain_prob_daily else None
    wind_daily = daily.get("wind_speed_10m_max") or []
    wind_today = wind_daily[0] if wind_daily else None

    if air:
        eu_aqi = air.get("european_aqi")
        us_aqi = air.get("us_aqi")
        eu_desc = interpret_aqi_eu(eu_aqi) if eu_aqi is not None else "N/A"
        us_desc = interpret_aqi_us(us_aqi) if us_aqi is not None else "N/A"
        aqi_desc = us_desc if us_aqi is not None else eu_desc
    else:
        aqi_desc = "N/A"

    suggestions = generate_suggestions(
        temp_c=temp_c,
        feels_c=feels_c,
        uv_max=uv_today,
        rain_prob=rain_prob_today,
        wind_max=wind_today,
        humidity_avg=hum_avg_today,
        aqi_desc=aqi_desc,
        code=code,
    )
    set_text(suggestions_text, suggestions)

    activities_str = generate_activities_text(forecast, best_hour_time)
    set_text(activities_text, activities_str)

    story_str = generate_story_text(forecast)
    set_text(story_text, story_str)

    draw_sunrise_card(forecast)
    draw_wind_card(forecast)
    draw_moon_card(forecast)

    global weather_bg
    weather_bg = choose_weather_background(code, is_day)
    update_wallpaper(code, is_day)
    apply_theme()
    update_panel_visibility()

    # NEW micro-summary line
    micro_summary_label.config(
        text=build_micro_summary(temp_c, feels_c, rain_prob_today, wind_today, code, best_hour_time)
    )

    # Alerts + NEW banner styling
    alert_messages: List[str] = []
    if isinstance(rain_prob_today, (int, float)) and rain_prob_today >= 80:
        alert_messages.append("Heavy rain likely today.")
    if isinstance(wind_today, (int, float)) and wind_today >= 60:
        alert_messages.append("Very windy/gusty later today.")
    if isinstance(code, int) and code >= 95:
        alert_messages.append("Thunderstorms possible.")
    if isinstance(uv_today, (int, float)) and uv_today >= 8:
        alert_messages.append("Very strong UV around midday.")

    if alert_messages:
        alert_label.config(text=" ⚠️ " + " ".join(alert_messages))
        # soft coloured pill
        if theme_mode == "light":
            alert_label.config(bg="#fee2e2", fg="#991b1b")
        else:
            alert_label.config(bg="#7f1d1d", fg="#fee2e2")
    else:
        alert_label.config(text="")
        # reset bg to card
        theme = THEMES[theme_mode]
        alert_label.config(bg=theme["card_bg"], fg=theme["fg"])

    now_local = datetime.now().strftime("%H:%M")
    last_updated_label.config(text=f"Last updated: {now_local}")

    save_settings()


# ===========================
# BUTTON HANDLER
# ===========================

def on_get_weather(event=None) -> None:
    city = city_entry.get().strip()
    if not city:
        messagebox.showwarning("City name", "Please type a city or area, e.g. 'Barnes, London'.")
        return

    get_button.config(text="Loading...", state="disabled")
    root.update_idletasks()
    try:
        loc = geocode_city(city)
        if not loc:
            return
        forecast = fetch_weather_cached(loc["latitude"], loc["longitude"], loc["timezone"])
        if not forecast:
            return
        air = fetch_air_quality(loc["latitude"], loc["longitude"], loc["timezone"])
        render_weather(loc, forecast, air)
    finally:
        get_button.config(text="Get Weather", state="normal")


# ===========================
# AUTOCOMPLETE (NEW)
# ===========================

_autocomplete_results: List[Dict[str, Any]] = []
_autocomplete_after_id = None

def show_autocomplete(results: List[Dict[str, Any]]) -> None:
    global _autocomplete_results
    _autocomplete_results = results

    autocomplete_listbox.delete(0, tk.END)
    for r in results:
        name = r.get("name") or ""
        admin1 = r.get("admin1") or ""
        country = r.get("country") or ""
        parts = [name]
        if admin1:
            parts.append(admin1)
        if country:
            parts.append(country)
        autocomplete_listbox.insert(tk.END, ", ".join(parts))

    if results:
        autocomplete_listbox.place(x=8, y=35, width=360, height=min(120, 20*len(results)))
        autocomplete_listbox.lift()
    else:
        autocomplete_listbox.place_forget()


def hide_autocomplete(event=None) -> None:
    autocomplete_listbox.place_forget()


def on_autocomplete_pick(event=None) -> None:
    sel = autocomplete_listbox.curselection()
    if not sel:
        return
    idx = sel[0]
    r = _autocomplete_results[idx]
    city_entry.delete(0, tk.END)
    parts = [r.get("name") or ""]
    if r.get("admin1"):
        parts.append(r["admin1"])
    if r.get("country"):
        parts.append(r["country"])
    city_entry.insert(0, ", ".join(parts))
    hide_autocomplete()
    on_get_weather()


def schedule_autocomplete(event=None):
    global _autocomplete_after_id
    if _autocomplete_after_id:
        root.after_cancel(_autocomplete_after_id)
    _autocomplete_after_id = root.after(350, run_autocomplete)


def run_autocomplete():
    text = city_entry.get().strip()
    if len(text) < 2:
        show_autocomplete([])
        return
    data = http_get_json(GEOCODE_URL, {"name": text, "count": 5, "language": "en", "format": "json"})
    results = (data or {}).get("results") or []
    show_autocomplete(results)


# ===========================
# GUI SETUP
# ===========================

root = tk.Tk()
root.title("Ultimate Weather Buddy – Open-Meteo (12-day Marvel)")
root.minsize(1250, 800)
root.option_add("*Font", "Arial 11")

# Top bar
top_frame = tk.Frame(root, padx=10, pady=8)
top_frame.pack(fill="x")

tk.Label(top_frame, text="City / area:").pack(side="left")
city_entry = tk.Entry(top_frame, width=32)
city_entry.pack(side="left", padx=5)
city_entry.bind("<Return>", on_get_weather)
city_entry.bind("<KeyRelease>", schedule_autocomplete)
city_entry.bind("<FocusOut>", hide_autocomplete)

get_button = tk.Button(top_frame, text="Get Weather", command=on_get_weather)
get_button.pack(side="left", padx=5)

units_button = tk.Button(top_frame, text="Units: Metric", command=toggle_units)
units_button.pack(side="left", padx=5)

theme_button = tk.Button(top_frame, text="Light / Dark", command=toggle_theme)
theme_button.pack(side="right")

settings_button = tk.Button(top_frame, text="⚙ Settings", command=open_settings)
settings_button.pack(side="right", padx=5)

# Autocomplete listbox (NEW)
autocomplete_listbox = tk.Listbox(top_frame)
autocomplete_listbox.bind("<Double-Button-1>", on_autocomplete_pick)
autocomplete_listbox.bind("<Return>", on_autocomplete_pick)

last_updated_label = tk.Label(root, text="Last updated: --:--", font=("Arial", 9))
last_updated_label.pack(anchor="e", padx=12)

# Middle layout
middle_frame = tk.Frame(root)
middle_frame.pack(fill="both", expand=True)

# Favourites sidebar
favourites_frame = tk.Frame(middle_frame, padx=8, pady=8, width=230)
favourites_frame.pack(side="left", fill="y")
favourites_frame.pack_propagate(False)

tk.Label(favourites_frame, text="Favourites", font=("Arial", 12, "bold")).pack(anchor="w")

favourites_listbox = tk.Listbox(favourites_frame, height=18, selectmode=tk.EXTENDED)
favourites_listbox.pack(side="left", fill="both", expand=True, pady=5)
favourites_listbox.bind("<Double-Button-1>", load_selected_favourite)

fav_scroll = tk.Scrollbar(favourites_frame, orient="vertical", command=favourites_listbox.yview)
fav_scroll.pack(side="right", fill="y")
favourites_listbox.configure(yscrollcommand=fav_scroll.set)

fav_buttons_frame = tk.Frame(favourites_frame)
fav_buttons_frame.pack(fill="x", pady=6)

button_font = ("Arial", 10, "bold")

tk.Button(
    fav_buttons_frame,
    text="Add current location",
    command=add_favourite,
    font=button_font,
    height=2
).pack(fill="x", pady=3)

tk.Button(
    fav_buttons_frame,
    text="Load selected",
    command=load_selected_favourite,
    font=button_font,
    height=2
).pack(fill="x", pady=3)

tk.Button(
    fav_buttons_frame,
    text="Remove selected",
    command=remove_favourite,
    font=button_font,
    height=2
).pack(fill="x", pady=3)

tk.Button(
    fav_buttons_frame,
    text="Compare favourites…",
    command=compare_favourites,
    font=button_font,
    height=2
).pack(fill="x", pady=3)

# Scrollable content on right
content_container = tk.Frame(middle_frame)
content_container.pack(side="left", fill="both", expand=True)

content_canvas = tk.Canvas(content_container, borderwidth=0)
content_canvas.pack(side="left", fill="both", expand=True)

scrollbar = tk.Scrollbar(content_container, orient="vertical", command=content_canvas.yview)
scrollbar.pack(side="right", fill="y")
content_canvas.configure(yscrollcommand=scrollbar.set)

scrollable_frame = tk.Frame(content_canvas)
window_id = content_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

def on_frame_configure(event):
    content_canvas.configure(scrollregion=content_canvas.bbox("all"))

def on_canvas_configure(event):
    content_canvas.itemconfig(window_id, width=event.width)

scrollable_frame.bind("<Configure>", on_frame_configure)
content_canvas.bind("<Configure>", on_canvas_configure)

# HEADER
header_frame = tk.Frame(scrollable_frame, padx=10, pady=8)
header_frame.pack(fill="x")

icon_label = tk.Label(header_frame, text="⛅", font=("Segoe UI Emoji", 36))
icon_label.pack(side="left", padx=5)

big_temp_label = tk.Label(header_frame, text="--", font=("Arial", 26, "bold"))
big_temp_label.pack(side="left", padx=5)

header_text_frame = tk.Frame(header_frame)
header_text_frame.pack(side="left", padx=10)

location_label = tk.Label(header_text_frame, text="Location: (none yet)", font=("Arial", 13, "bold"))
location_label.pack(anchor="w")

hi_lo_label = tk.Label(header_text_frame, text="Today: High --   •   Low --", font=("Arial", 11))
hi_lo_label.pack(anchor="w", pady=(2, 0))

micro_summary_label = tk.Label(header_text_frame, text="", font=("Arial", 10, "italic"))
micro_summary_label.pack(anchor="w", pady=(2, 0))

alert_label = tk.Label(header_frame, text="", font=("Arial", 11, "bold"))
alert_label.pack(side="bottom", anchor="w", pady=(5, 0))

# LIVE BACKGROUND
wallpaper_frame = tk.LabelFrame(scrollable_frame, text="Live background", padx=10, pady=5)
wallpaper_frame.pack(fill="x", padx=10, pady=5)

wallpaper_canvas = tk.Canvas(wallpaper_frame, height=220)
wallpaper_canvas.pack(fill="x", expand=True)

# CURRENT CONDITIONS
current_frame = tk.LabelFrame(scrollable_frame, text="Current conditions", padx=10, pady=5)
current_frame.pack(fill="x", padx=10, pady=5)

current_text = tk.Text(current_frame, height=8, wrap="word")
current_text.pack(fill="x")
current_text.config(state="disabled")

# FORECAST
forecast_frame = tk.LabelFrame(scrollable_frame, text="12-day forecast (graph + detail)", padx=10, pady=5)
forecast_frame.pack(fill="both", padx=10, pady=5)

forecast_inner = tk.Frame(forecast_frame)
forecast_inner.pack(fill="both", expand=True)

forecast_canvas = tk.Canvas(forecast_inner, height=180)
forecast_canvas.pack(side="left", fill="both", expand=True, padx=(0, 5))

forecast_text = tk.Text(forecast_inner, wrap="word")
forecast_text.pack(side="left", fill="both", expand=True)
forecast_text.config(state="disabled", height=12)

# OVERVIEW
ten_day_overview_frame = tk.LabelFrame(scrollable_frame, text="12-day overview & extremes", padx=10, pady=5)
ten_day_overview_frame.pack(fill="both", padx=10, pady=5)

ten_day_overview_text = tk.Text(ten_day_overview_frame, height=7, wrap="word")
ten_day_overview_text.pack(fill="both", expand=True)
ten_day_overview_text.config(state="disabled")

# HOURLY
hourly_frame = tk.LabelFrame(scrollable_frame, text="Next 24 hours (per selected day)", padx=10, pady=5)
hourly_frame.pack(fill="both", padx=10, pady=5)

day_selector_frame = tk.Frame(hourly_frame)
day_selector_frame.pack(fill="x", pady=(0, 5))

day_label = tk.Label(day_selector_frame, text="Choose day:")
day_label.pack(side="left", padx=(0, 5))

hourly_strip_container = tk.Frame(hourly_frame)
hourly_strip_container.pack(fill="x", pady=(0, 5))

hourly_strip_canvas = tk.Canvas(hourly_strip_container, height=90)
hourly_strip_canvas.pack(side="left", fill="x", expand=True)

hourly_strip_scrollbar = tk.Scrollbar(hourly_strip_container, orient="horizontal",
                                      command=hourly_strip_canvas.xview)
hourly_strip_scrollbar.pack(side="bottom", fill="x")
hourly_strip_canvas.configure(xscrollcommand=hourly_strip_scrollbar.set)

hourly_temp_canvas = tk.Canvas(hourly_frame, height=110)
hourly_temp_canvas.pack(fill="x", pady=3)

hourly_feels_canvas = tk.Canvas(hourly_frame, height=110)
hourly_feels_canvas.pack(fill="x", pady=3)

hourly_rain_canvas = tk.Canvas(hourly_frame, height=110)
hourly_rain_canvas.pack(fill="x", pady=3)

hourly_uv_canvas = tk.Canvas(hourly_frame, height=110)
hourly_uv_canvas.pack(fill="x", pady=3)

hourly_wind_canvas = tk.Canvas(hourly_frame, height=110)
hourly_wind_canvas.pack(fill="x", pady=3)

hourly_humid_canvas = tk.Canvas(hourly_frame, height=110)
hourly_humid_canvas.pack(fill="x", pady=3)

hourly_comfort_canvas = tk.Canvas(hourly_frame, height=110)
hourly_comfort_canvas.pack(fill="x", pady=3)

# SUN
sun_frame = tk.LabelFrame(scrollable_frame, text="Sunrise & sunset", padx=10, pady=5)
sun_frame.pack(fill="x", padx=10, pady=5)

sun_text_label = tk.Label(sun_frame, text="", anchor="w", justify="left")
sun_text_label.pack(fill="x", pady=(0, 5))

sun_canvas = tk.Canvas(sun_frame, height=40)
sun_canvas.pack(fill="x")

# WIND
wind_frame = tk.LabelFrame(scrollable_frame, text="Wind", padx=10, pady=5)
wind_frame.pack(fill="x", padx=10, pady=5)

wind_text_label = tk.Label(wind_frame, text="", justify="left", anchor="w")
wind_text_label.pack(side="left", fill="both", expand=True)

wind_canvas = tk.Canvas(wind_frame, width=150, height=150)
wind_canvas.pack(side="right", padx=10)

# AIR
air_frame = tk.LabelFrame(scrollable_frame, text="Air quality", padx=10, pady=5)
air_frame.pack(fill="x", padx=10, pady=5)

air_text_label = tk.Label(air_frame, text="", justify="left", anchor="w")
air_text_label.pack(fill="x")

# MOON
moon_frame = tk.LabelFrame(scrollable_frame, text="Moon phase", padx=10, pady=5)
moon_frame.pack(fill="x", padx=10, pady=5)

moon_text_label = tk.Label(moon_frame, text="", justify="left", anchor="w")
moon_text_label.pack(fill="x")

# STORY
story_frame = tk.LabelFrame(scrollable_frame, text="Weather story & summary", padx=10, pady=5)
story_frame.pack(fill="both", padx=10, pady=5)

story_text = tk.Text(story_frame, height=9, wrap="word")
story_text.pack(fill="both", expand=True)
story_text.config(state="disabled")

# ACTIVITIES
activities_frame = tk.LabelFrame(scrollable_frame, text="Activities & best times", padx=10, pady=5)
activities_frame.pack(fill="both", padx=10, pady=5)

activities_text = tk.Text(activities_frame, height=7, wrap="word")
activities_text.pack(fill="both", expand=True)
activities_text.config(state="disabled")

# SUGGESTIONS
suggestions_frame = tk.LabelFrame(scrollable_frame, text="What to wear / suggestions", padx=10, pady=5)
suggestions_frame.pack(fill="both", padx=10, pady=5)

suggestions_text = tk.Text(suggestions_frame, height=9, wrap="word")
suggestions_text.pack(fill="both", expand=True)
suggestions_text.config(state="disabled")

# COMPARE
compare_frame = tk.LabelFrame(scrollable_frame, text="Compare favourites (today)", padx=10, pady=5)
compare_frame.pack(fill="both", padx=10, pady=5)

compare_text = tk.Text(compare_frame, height=6, wrap="none", font=("Consolas", 11))
compare_text.pack(fill="both", expand=True)
compare_text.config(state="disabled")

# FOOTER
footer_label = tk.Label(
    scrollable_frame,
    text="Ultimate Weather Buddy (12-day Marvel) • Data from Open-Meteo.com • Settings • Compare favourites • Comfort index, story & activity ranking",
    font=("Arial", 9),
)
footer_label.pack(side="bottom", pady=5)

# Load settings & start
load_settings()
units_button.config(text=f"Units: {'Metric' if units_mode == 'metric' else 'Imperial'}")

for loc in favourites:
    favourites_listbox.insert(tk.END, format_location(loc))

load_wallpapers()
apply_theme()
update_panel_visibility()
update_wallpaper(None, None)
auto_load_last_location()

if __name__ == "__main__":
    root.mainloop()
