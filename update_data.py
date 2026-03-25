import requests
import csv
import os
import json
import re
from datetime import datetime, timezone

TARGET_URL = "https://2miners.com/grin-network-hashrate"
CSV_FILE = "grin_data.csv"

def fetch_data():
    try:
        response = requests.get(TARGET_URL)
        response.raise_for_status()
        html = response.text

        # Wyszukujemy tablice obiektów zawierających {"timestamp": ...}
        # w kodzie JS osadzonym w dokumencie
        match = re.search(r'(\[{"timestamp".*?\}\])', html)
        if match:
            json_str = match.group(1)
            try:
                data = json.loads(json_str)
                formatted_data = []
                for point in data:
                    ts = point.get("timestamp")
                    if ts:
                        formatted_data.append({
                            "x": ts,
                            "y": point.get("hashrate", 0),
                            "netdiff": point.get("difficulty", 0)
                        })
                return formatted_data
            except json.JSONDecodeError as e:
                print(f"Błąd podczas parsowania JSON: {e}")
                return []
        else:
            print("Nie znaleziono danych na stronie.")
            return []
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

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
