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

# Strefa CET (UTC+1) używana do wyłuskiwania punktów z godziny 12:00
CET_TZ = timezone(timedelta(hours=1))

def fetch_data():
    daily_points = {}
    current_time_ts = datetime.now(timezone.utc).timestamp()

    # 1. Pobieranie danych historycznych za cały czas
    try:
        response_all = requests.get(URL_ALL_TIME)
        response_all.raise_for_status()
        data_all = response_all.json()
        for point in data_all:
            ts = point.get("timestamp")
            if ts and ts <= current_time_ts:
                dt_cet = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(CET_TZ)
                day_str = dt_cet.strftime('%Y-%m-%d')
                # Format czytelnej daty
                readable_time = dt_cet.strftime('%Y-%m-%d %H:%M:%S')

                daily_points[day_str] = {
                    "datetime": readable_time,
                    "y": point.get("hashrate", 0),
                    "netdiff": point.get("difficulty", 0)
                }
    except Exception as e:
        print(f"Error fetching all-time data: {e}")

    # 2. Pobieranie nowszych, godzinowych danych i wyłuskiwanie 12:00 CET
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
                    readable_time = dt_cet.strftime('%Y-%m-%d %H:%M:%S')

                    if dt_cet.hour == 12:
                        daily_points[day_str] = {
                            "datetime": readable_time,
                            "y": point.get("hashrate", 0),
                            "netdiff": point.get("difficulty", 0)
                        }
                    elif day_str not in daily_points:
                        daily_points[day_str] = {
                            "datetime": readable_time,
                            "y": point.get("hashrate", 0),
                            "netdiff": point.get("difficulty", 0)
                        }
    except Exception as e:
        print(f"Error fetching recent HTML data: {e}")

    sorted_days = sorted(daily_points.keys())
    return [daily_points[day] for day in sorted_days]

def update_csv():
    new_data = fetch_data()
    if not new_data:
        print("No data fetched.")
        return

    # Słownik śledzący unikalne DNI z kolumny `datetime` (np. 2019-03-25),
    # ponieważ usuwamy surowy `timestamp`.
    existing_days = set()
    file_exists = os.path.isfile(CSV_FILE)

    if file_exists:
        with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if row and len(row) >= 1:
                    # Szukamy YYYY-MM-DD z daty w pierwszej kolumnie
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
