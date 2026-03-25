import requests
import csv
import os
from datetime import datetime, timezone

API_URL = "https://grin.2miners.com/api/stats"
CSV_FILE = "grin_data.csv"

def fetch_data():
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()
        # W algorytmie GRIN 2miners używa klucza '32'
        charts_data = data.get("charts", {}).get("32", [])
        return charts_data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def update_csv():
    new_data = fetch_data()
    if not new_data:
        print("No data fetched.")
        return

    # Słownik do przechowywania już istniejących punktów po timestamp
    existing_timestamps = set()

    # Sprawdzanie i ładowanie istniejących danych
    file_exists = os.path.isfile(CSV_FILE)
    if file_exists:
        with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if row:
                    try:
                        # Przechowujemy oryginalny unix timestamp, by uniknąć duplikatów
                        ts = int(row[0])
                        existing_timestamps.add(ts)
                    except ValueError:
                        pass

    # Przygotowanie nowych wierszy
    rows_to_append = []
    for point in new_data:
        ts = point.get("x")
        if ts is not None and ts not in existing_timestamps:
            # Formatowanie timestampa do czytelnego formatu
            readable_time = datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            hashrate = point.get("y", 0) # y to hashrate w Gps (lub odpowiedniej jednostce)
            difficulty = point.get("netdiff", 0)
            rows_to_append.append([ts, readable_time, hashrate, difficulty])
            existing_timestamps.add(ts)

    # Sortowanie danych po timestampie, by upewnić się, że idą chronologicznie
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
