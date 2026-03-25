import requests
import csv
import os
import json
import re
from datetime import datetime, timezone, timedelta

# Źródła danych z 2miners
URL_ALL_TIME = "https://hr.2miners.com/api/v1/hashrate/1d/grin"
URL_RECENT_HTML = "https://2miners.com/grin-network-hashrate"
CSV_FILE = "grin_data.csv"

# Strefa CET (UTC+1)
CET_TZ = timezone(timedelta(hours=1))

def fetch_data():
    daily_points = {}
    hourly_collections = {} # Do zbierania wielu próbek z jednego dnia
    current_time_ts = datetime.now(timezone.utc).timestamp()

    # 1. Pobieranie danych historycznych za cały czas (1 punkt na dzień API)
    try:
        response_all = requests.get(URL_ALL_TIME)
        response_all.raise_for_status()
        data_all = response_all.json()
        for point in data_all:
            ts = point.get("timestamp")
            if ts and ts <= current_time_ts:
                dt_cet = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(CET_TZ)
                day_str = dt_cet.strftime('%Y-%m-%d')

                # Używamy 12:00 jako godziny reprezentatywnej dla formatu wyjściowego
                dt_repr = dt_cet.replace(hour=12, minute=0, second=0)
                readable_time = dt_repr.strftime('%Y-%m-%d %H:%M:%S')

                daily_points[day_str] = {
                    "datetime": readable_time,
                    "y": point.get("hashrate", 0),
                    "netdiff": point.get("difficulty", 0)
                }
    except Exception as e:
        print(f"Error fetching all-time data: {e}")

    # 2. Pobieranie nowszych, godzinowych danych i zbieranie ich do średniej
    try:
        response_recent = requests.get(URL_RECENT_HTML)
        response_recent.raise_for_status()
        match = re.search(r'(\[{"timestamp".*?\}\])', response_recent.text)
        if match:
            data_recent = json.loads(match.group(1))
            for point in data_recent:
                ts = point.get("timestamp")
                if ts and ts <= current_time_ts:
                    dt_cet = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(CET_TZ)
                    day_str = dt_cet.strftime('%Y-%m-%d')

                    if day_str not in hourly_collections:
                        hourly_collections[day_str] = {"y": [], "netdiff": []}

                    hourly_collections[day_str]["y"].append(point.get("hashrate", 0))
                    hourly_collections[day_str]["netdiff"].append(point.get("difficulty", 0))

    except Exception as e:
        print(f"Error fetching recent HTML data: {e}")

    # Wyliczanie średniej dla dni z danymi godzinowymi i nadpisywanie
    for day_str, vals in hourly_collections.items():
        if vals["y"] and vals["netdiff"]:
            avg_y = sum(vals["y"]) / len(vals["y"])
            avg_diff = sum(vals["netdiff"]) / len(vals["netdiff"])

            # Reprezentacyjna godzina dla wiersza wyjściowego
            # Możemy sparsować date_str by dodać 12:00:00
            readable_time = f"{day_str} 12:00:00"

            # Nadpisujemy ew. punkt z API całodziennego, bardziej dokładną średnią
            daily_points[day_str] = {
                "datetime": readable_time,
                "y": round(avg_y, 2), # zaokrąglamy dla czystości CSV
                "netdiff": int(avg_diff) # difficulty jest ogromne, zazwyczaj integer
            }

    sorted_days = sorted(daily_points.keys())
    return [daily_points[day] for day in sorted_days]

def update_csv():
    new_data = fetch_data()
    if not new_data:
        print("No data fetched.")
        return

    # Słownik śledzący unikalne DNI z kolumny `datetime` (np. 2019-03-25)
    existing_days = set()
    file_exists = os.path.isfile(CSV_FILE)

    if file_exists:
        with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if row and len(row) >= 1:
                    date_val = row[0][:10]
                    existing_days.add(date_val)

    rows_to_append = []
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
