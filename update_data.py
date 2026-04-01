import requests
import csv
import os
import json
import re
from datetime import datetime, timezone, timedelta

URL_ALL_TIME = "https://hr.2miners.com/api/v1/hashrate/1d/grin"
URL_RECENT_HTML = "https://2miners.com/grin-network-hashrate"
CSV_FILE = "grin_data.csv"

CET_TZ = timezone(timedelta(hours=1))
CUTOFF_DATE_STR = "2021-01-16"

def fetch_data():
    daily_points = {}
    hourly_collections = {}
    # Odpalamy z luznym filtrem 2 tygodni, zeby nie odcinalo spoznionych kropek lub offsetow API
    current_time_ts = (datetime.now(timezone.utc) + timedelta(days=5)).timestamp()

    try:
        response_all = requests.get(URL_ALL_TIME, timeout=10)
        response_all.raise_for_status()
        data_all = response_all.json()
        for point in data_all:
            ts = point.get("timestamp")
            if ts and ts <= current_time_ts:
                dt_cet = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(CET_TZ)
                day_str = dt_cet.strftime('%Y-%m-%d')

                if day_str < CUTOFF_DATE_STR:
                    continue

                dt_repr = dt_cet.replace(hour=12, minute=0, second=0)
                readable_time = dt_repr.strftime('%Y-%m-%d %H:%M:%S')

                daily_points[day_str] = {
                    "datetime": readable_time,
                    "y": point.get("hashrate", 0),
                    "netdiff": point.get("difficulty", 0)
                }
    except Exception as e:
        print(f"Error fetching all-time data: {e}")

    try:
        response_recent = requests.get(URL_RECENT_HTML, timeout=10)
        response_recent.raise_for_status()
        match = re.search(r'(\[{"timestamp".*?\}\])', response_recent.text)
        if match:
            data_recent = json.loads(match.group(1))
            for point in data_recent:
                ts = point.get("timestamp")
                if ts and ts <= current_time_ts:
                    dt_cet = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(CET_TZ)
                    day_str = dt_cet.strftime('%Y-%m-%d')

                    if day_str < CUTOFF_DATE_STR:
                        continue

                    if day_str not in hourly_collections:
                        hourly_collections[day_str] = {"y": [], "netdiff": []}

                    hourly_collections[day_str]["y"].append(point.get("hashrate", 0))
                    hourly_collections[day_str]["netdiff"].append(point.get("difficulty", 0))
    except Exception as e:
        print(f"Error fetching recent HTML data: {e}")

    for day_str, vals in hourly_collections.items():
        if vals["y"] and vals["netdiff"]:
            avg_y = sum(vals["y"]) / len(vals["y"])
            avg_diff = sum(vals["netdiff"]) / len(vals["netdiff"])
            readable_time = f"{day_str} 12:00:00"

            daily_points[day_str] = {
                "datetime": readable_time,
                "y": round(avg_y, 2),
                "netdiff": int(avg_diff)
            }

    sorted_days = sorted(daily_points.keys())
    return [daily_points[day] for day in sorted_days]

def update_csv():
    new_data = fetch_data()
    if not new_data:
        print("No data fetched.")
        return

    existing_days = set()
    file_exists = os.path.isfile(CSV_FILE)

    # Skoro uzytkownik widzi ostatni z 25 marca, to update_data.py NIE potrafil dopisac nowych,
    # ALBO w ogole sie nie odpalal, ALBO zapisal sie stary current_time_ts ktory ucina?
    # Wczytajmy to co mamy:
    if file_exists:
        with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if row and len(row) >= 1:
                    date_val = row[0][:10]
                    existing_days.add(date_val)

    rows_to_append = []
    # Dopiszemy wszystko to, czego brakuje w pliku
    for point in new_data:
        day_str = point["datetime"][:10]
        if day_str not in existing_days:
            hashrate = point.get("y", 0)
            difficulty = point.get("netdiff", 0)
            rows_to_append.append([point["datetime"], hashrate, difficulty])
            existing_days.add(day_str)

    rows_to_append.sort(key=lambda x: x[0])

    if rows_to_append:
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["datetime", "hashrate", "difficulty"])
            writer.writerows(rows_to_append)
        print(f"Added {len(rows_to_append)} new records to {CSV_FILE}.")
    else:
        print("No new records to add.")

if __name__ == "__main__":
    update_csv()
