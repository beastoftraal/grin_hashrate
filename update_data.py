import requests
import csv
import os
import json
import re
from datetime import datetime, timezone

# Źródło 1: Główne historyczne statystyki codzienne (od początku istnienia sieci)
URL_ALL_TIME = "https://hr.2miners.com/api/v1/hashrate/1d/grin"
# Źródło 2: Bardziej szczegółowe statystyki z ostatnich dni zagnieżdżone w HTML
URL_RECENT_HTML = "https://2miners.com/grin-network-hashrate"
CSV_FILE = "grin_data.csv"

def fetch_data():
    all_points = {}

    # 1. Pobieranie danych historycznych za cały czas (dzienne próbki)
    try:
        response_all = requests.get(URL_ALL_TIME)
        response_all.raise_for_status()
        data_all = response_all.json()
        for point in data_all:
            ts = point.get("timestamp")
            if ts:
                all_points[ts] = {
                    "x": ts,
                    "y": point.get("hashrate", 0),
                    "netdiff": point.get("difficulty", 0)
                }
    except Exception as e:
        print(f"Error fetching all-time data: {e}")

    # 2. Pobieranie nowszych, bardziej szczegółowych danych z tagu skryptu HTML (godzinowe próbki z ostatnich miesięcy)
    try:
        response_recent = requests.get(URL_RECENT_HTML)
        response_recent.raise_for_status()
        match = re.search(r'(\[{"timestamp".*?\}\])', response_recent.text)
        if match:
            data_recent = json.loads(match.group(1))
            for point in data_recent:
                ts = point.get("timestamp")
                if ts:
                    # To nadpisze codzienne (jeśli timestamp idealnie się pokrywa, choć zwykle godzinowe są unikalne)
                    all_points[ts] = {
                        "x": ts,
                        "y": point.get("hashrate", 0),
                        "netdiff": point.get("difficulty", 0)
                    }
    except Exception as e:
        print(f"Error fetching recent HTML data: {e}")

    # Zwróć jako listę, posortowaną po timestampie
    return [all_points[ts] for ts in sorted(all_points.keys())]

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
