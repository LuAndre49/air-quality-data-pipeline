import time
import requests
import pandas as pd
import dlt
from datetime import datetime, timedelta, timezone

START_DATE = "2024-08-01"
END_DATE = "2024-08-31"

NOMINATIM_HEADERS = {"User-Agent": "ph-weather-analytics/1.0"}
NCR = {"province": "Metro Manila (NCR)", "lat": 14.5086, "lon": 121.0197}

PHILIPPINE_PROVINCES = [
    "Abra", "Agusan del Norte", "Agusan del Sur", "Aklan", "Albay",
    "Antique", "Apayao", "Aurora", "Basilan", "Bataan",
    "Batanes", "Batangas", "Benguet", "Biliran", "Bohol",
    "Bukidnon", "Bulacan", "Cagayan", "Camarines Norte", "Camarines Sur",
    "Camiguin", "Capiz", "Catanduanes", "Cavite", "Cebu",
    "Cotabato", "Davao de Oro", "Davao del Norte", "Davao del Sur", "Davao Occidental",
    "Davao Oriental", "Dinagat Islands", "Eastern Samar", "Guimaras", "Ifugao",
    "Ilocos Norte", "Ilocos Sur", "Iloilo", "Isabela", "Kalinga",
    "La Union", "Laguna", "Lanao del Norte", "Lanao del Sur", "Leyte",
    "Maguindanao del Norte", "Maguindanao del Sur", "Marinduque", "Masbate",
    "Misamis Occidental", "Misamis Oriental", "Mountain Province", "Negros Occidental", "Negros Oriental",
    "Northern Samar", "Nueva Ecija", "Nueva Vizcaya", "Occidental Mindoro", "Oriental Mindoro",
    "Palawan", "Pampanga", "Pangasinan", "Quezon", "Quirino",
    "Rizal", "Romblon", "Samar", "Sarangani", "Siquijor",
    "Sorsogon", "South Cotabato", "Southern Leyte", "Sultan Kudarat", "Sulu",
    "Surigao del Norte", "Surigao del Sur", "Tarlac", "Tawi-Tawi", "Zambales",
    "Zamboanga del Norte", "Zamboanga del Sur", "Zamboanga Sibugay"
]

DAILY_VARIABLES = ",".join([
    "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
    "precipitation_sum", "rain_sum", "precipitation_hours",
    "wind_speed_10m_max", "wind_gusts_10m_max", "wind_direction_10m_dominant",
    "relative_humidity_2m_max", "relative_humidity_2m_min",
    "shortwave_radiation_sum", "sunshine_duration", "et0_fao_evapotranspiration"
])


def get_coordinates(province, retries=3):
    for attempt in range(retries):
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": f"{province}, Philippines", "format": "json", "limit": 1},
                headers=NOMINATIM_HEADERS,
                timeout=10
            )
            results = resp.json()
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
            return None, None
        except Exception as e:
            print(f"  [ERROR] get_coordinates {province} attempt {attempt + 1}: {e}")
            time.sleep(2)
    return None, None


def clean_float(val):
    try:
        f = float(val)
        return None if f != f else f
    except:
        return None


def fetch_province(loc, start_date, end_date, retries=3):
    for attempt in range(retries):
        try:
            resp = requests.get(
                "https://archive-api.open-meteo.com/v1/archive",
                params={
                    "latitude": loc["lat"],
                    "longitude": loc["lon"],
                    "start_date": start_date,
                    "end_date": end_date,
                    "daily": DAILY_VARIABLES,
                    "format": "json"
                },
                timeout=120
            )
            if resp.status_code == 200:
                return resp.json()
            print(f"  [ERROR] {loc['province']} attempt {attempt + 1}: status={resp.status_code} {resp.text[:100]}")
        except Exception as e:
            print(f"  [ERROR] {loc['province']} attempt {attempt + 1}: {e}")
        time.sleep(5 * (attempt + 1))
    return None


@dlt.resource(write_disposition="append", name="weather_daily")
def all_provinces_resource(locations):
    total = 0
    for loc in locations:
        print(f"  [backfill] Fetching {loc['province']}...")
        data = fetch_province(loc, START_DATE, END_DATE)
        if not data:
            print(f"  [WARN] Skipping {loc['province']} — no data returned")
            time.sleep(5)
            continue

        daily = data.get("daily", {})
        times = daily.get("time", [])

        for j, date in enumerate(times):
            yield {
                "province": loc["province"],
                "latitude": loc["lat"],
                "longitude": loc["lon"],
                "date": date,
                "temperature_max": clean_float(daily["temperature_2m_max"][j]),
                "temperature_min": clean_float(daily["temperature_2m_min"][j]),
                "temperature_mean": clean_float(daily["temperature_2m_mean"][j]),
                "precipitation_sum": clean_float(daily["precipitation_sum"][j]),
                "rain_sum": clean_float(daily["rain_sum"][j]),
                "precipitation_hours": clean_float(daily["precipitation_hours"][j]),
                "wind_speed_max": clean_float(daily["wind_speed_10m_max"][j]),
                "wind_gusts_max": clean_float(daily["wind_gusts_10m_max"][j]),
                "wind_direction_dominant": clean_float(daily["wind_direction_10m_dominant"][j]),
                "humidity_max": clean_float(daily["relative_humidity_2m_max"][j]),
                "humidity_min": clean_float(daily["relative_humidity_2m_min"][j]),
                "shortwave_radiation_sum": clean_float(daily["shortwave_radiation_sum"][j]),
                "sunshine_duration": clean_float(daily["sunshine_duration"][j]),
                "evapotranspiration": clean_float(daily["et0_fao_evapotranspiration"][j]),
            }
            total += 1

        print(f"  [backfill] {loc['province']} done — {total} total rows so far")
        time.sleep(15)

    print(f"  [backfill] All provinces done — {total} total rows")


if __name__ == "__main__":
    # resolve coordinates via nominatim
    print("  [backfill] Resolving coordinates...")
    locations = [NCR]
    for province in PHILIPPINE_PROVINCES:
        lat, lon = get_coordinates(province)
        if lat:
            locations.append({"province": province, "lat": lat, "lon": lon})
        else:
            print(f"  [WARN] Could not resolve coordinates for {province}")
        time.sleep(1)

    print(f"  [backfill] Resolved {len(locations)} locations")

    pipeline = dlt.pipeline(
        pipeline_name="ph_weather_full_backfill",
        destination="bigquery",
        dataset_name="raw_ph_weather"
    )

    try:
        load_info = pipeline.run(all_provinces_resource(locations))
        print(f"[DONE]: {load_info}")
    except Exception as e:
        print(f"[FAILED]: {e}")
        raise