import requests
import csv
import os
import json
import re
from datetime import datetime, timezone, timedelta

# Źródło 1: Główne historyczne statystyki codzienne (od początku istnienia sieci)
URL_ALL_TIME = "https://hr.2miners.com/api/v1/hashrate/1d/grin"
# Źródło 2: Bardziej szczegółowe statystyki z ostatnich dni zagnieżdżone w HTML
URL_RECENT_HTML = "https://2miners.com/grin-network-hashrate"
CSV_FILE = "grin_data.csv"

# Definicja strefy czasowej CET (UTC+1, bez uwzględniania czasu letniego dla prostoty,
# jako wytyczna dla filtru - godzina 12:00 CET odpowiada 11:00 UTC w zimie)
# Dokładniej: Użyjemy twardego offsetu UTC+1
CET_TZ = timezone(timedelta(hours=1))

def fetch_data():
    daily_points = {}
    current_time_ts = datetime.now(timezone.utc).timestamp()

    # 1. Pobieranie danych historycznych za cały czas (dzienne próbki z API)
    try:
        response_all = requests.get(URL_ALL_TIME)
        response_all.raise_for_status()
        data_all = response_all.json()
        for point in data_all:
            ts = point.get("timestamp")
            if ts and ts <= current_time_ts:
                # Zamiana timestampu na datę CET w celu uzyskania "dnia"
                dt_cet = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(CET_TZ)
                day_str = dt_cet.strftime('%Y-%m-%d')

                # API "1d" zazwyczaj daje jeden punkt dziennie, często o 00:00.
                # Zapisujemy go w słowniku pod danym dniem.
                daily_points[day_str] = {
                    "x": ts,
                    "y": point.get("hashrate", 0),
                    "netdiff": point.get("difficulty", 0)
                }
    except Exception as e:
        print(f"Error fetching all-time data: {e}")

    # 2. Pobieranie nowszych, godzinowych danych i wyłuskiwanie tylko godz. 12:00 CET
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

                    # Jeśli to jest próbka z godziny 12:00 CET, preferujemy ją jako punkt dnia
                    if dt_cet.hour == 12:
                        daily_points[day_str] = {
                            "x": ts,
                            "y": point.get("hashrate", 0),
                            "netdiff": point.get("difficulty", 0)
                        }
                    # Jeśli nie mamy ŻADNEGO punktu w ogóle na ten dzień, możemy zapisać
                    # go ratunkowo (np. jeśli 12 jeszcze nie wybiła, by mieć cokolwiek na dziś).
                    elif day_str not in daily_points:
                        daily_points[day_str] = {
                            "x": ts,
                            "y": point.get("hashrate", 0),
                            "netdiff": point.get("difficulty", 0)
                        }
    except Exception as e:
        print(f"Error fetching recent HTML data: {e}")

    # Sortuj rosnąco po kluczu, czyli dacie (str)
    sorted_days = sorted(daily_points.keys())
    return [daily_points[day] for day in sorted_days]

def update_csv():
    new_data = fetch_data()
    if not new_data:
        print("No data fetched.")
        return

    existing_timestamps = set()
    file_exists = os.path.isfile(CSV_FILE)
    if file_exists:
        with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if row:
                    try:
                        ts = int(row[0])
                        existing_timestamps.add(ts)
                    except ValueError:
                        pass

    rows_to_append = []
    for point in new_data:
        ts = point.get("x")
        if ts is not None and ts not in existing_timestamps:
            readable_time = datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            hashrate = point.get("y", 0)
            difficulty = point.get("netdiff", 0)
            rows_to_append.append([ts, readable_time, hashrate, difficulty])
            existing_timestamps.add(ts)

    rows_to_append.sort(key=lambda x: x[0])

    if rows_to_append:
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "datetime", "hashrate", "difficulty"])
            writer.writerows(rows_to_append)
        print(f"Added {len(rows_to_append)} new records to {CSV_FILE}.")
    else:
        print("No new records to add.")

if __name__ == "__main__":
    update_csv()
