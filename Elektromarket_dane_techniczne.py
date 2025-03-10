# Biblioteki
from loguru import logger
import csv
import os
import glob
import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Utworzenie folderu output, jeśli nie istnieje
output_folder = "output"
os.makedirs(output_folder, exist_ok=True)

# Ustawienia nazwy sklepu oraz daty
shop_name = "elektromarket"
today_date = datetime.today().strftime("%Y-%m-%d")
csv_filename = f"output/{shop_name}_{today_date}.csv"
log_filename = f"output/log_tech_details_{shop_name}_{today_date}.log"

# Konfiguracja logowania przy użyciu loguru:
logger.remove()
log_format = "{time:YYYY-MM-DD HH:mm:ss,SSS} - {level} - {message}"
logger.add(log_filename, level="INFO", format="{time} - {level} - {message}", encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)

logger.info("Rozpoczęcie skryptu pobierania szczegółów technicznych.")
logger.info("Plik CSV: {}", csv_filename)
logger.info("Plik logu: {}", log_filename)

# Definiujemy pola CSV
fieldnames = ["date", "title", "price", "product_link"]

# Wyszukanie najnowszego pliku CSV wygenerowanego przez pierwszy skrypt
csv_pattern = os.path.join(output_folder, f"{shop_name}_*.csv")
csv_files = glob.glob(csv_pattern)
if not csv_files:
    logger.error("Nie znaleziono plików CSV pasujących do wzorca {}", csv_pattern)
    exit(1)

def extract_date(filename):
    base = os.path.basename(filename)
    # Zakładamy, że nazwa pliku ma format: komputronik_YYYY-MM-DD.csv
    date_str = base.replace(f"{shop_name}_", "").replace(".csv", "")
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

csv_files_with_date = [(file, extract_date(file)) for file in csv_files if extract_date(file) is not None]
if not csv_files_with_date:
    logger.error("Żaden z plików CSV nie ma poprawnego formatu daty.")
    exit(1)
csv_files_with_date.sort(key=lambda x: x[1], reverse=True)
latest_csv_file = csv_files_with_date[0][0]
logger.info("Wybrany plik CSV: {}", latest_csv_file)

# Wczytanie linków produktów z CSV
product_data = []
with open(latest_csv_file, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get("product_link"):
            product_data.append({
                "product_link": row["product_link"],
            })
logger.info("Znaleziono {} produktów do przetworzenia.", len(product_data))

def scrape_tech_details(url):
    """
    Funkcja otwiera stronę produktu i próbuje pobrać wszystkie detale techniczne.
    """
    tech_details = {}
    try:
        requested_page = requests.get(url)
        requested_page.raise_for_status()
        soup = BeautifulSoup(requested_page.text, 'html.parser')


        # Szukanie obiektu zawierającego między innymi dane techniczne
        product_details_table = soup.find(class_="tab-pane fade active in")
        if not product_details_table:
            logger.warning("Nie znaleziono tabeli dla URL: {}", url)
            return tech_details

        # Wyszukiwanie danych technicznych
        for table_title in product_details_table.find_all("h2"):
            if table_title.text.strip() == "Dane techniczne":
                table = table_title.find_next_sibling("table")
                if table:
                    for detail in table.find_all("tr"):
                        columns = detail.find_all("td")
                        if len(columns) == 2:
                            key = columns[0].get_text(strip=True)
                            value = columns[1].get_text(strip=True)
                            tech_details[key] = value
                        else:
                            logger.warning("Błąd podczas odczytywania parametrów, niepoprawna ilość kolumn: {}", url)

        if not product_details_table:
            logger.warning("Nie znaleziono tabel atrybutów dla URL: {}", url)
            return tech_details

    except Exception as e:
        logger.error("Błąd przy otwieraniu URL {}: {}", url, e)
    return tech_details


# Przygotowanie pliku wynikowego z danymi technicznymi w folderze output
tech_csv_filename = os.path.join(output_folder, f"tech_details_{shop_name}_{today_date}.csv")
fieldnames = ["product_link", "tech_details"]

with open(tech_csv_filename, mode="w", newline="", encoding="utf-8") as tech_csvfile:
    writer = csv.DictWriter(tech_csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for item in product_data:
        url = item["product_link"]
        logger.info("Przetwarzanie: {}", url)
        details = scrape_tech_details(url)
        writer.writerow({
            "product_link": url,
            "tech_details": json.dumps(details, ensure_ascii=False)
        })


# Zamknięcie przeglądarki
logger.complete()
logger.info("Zakończono pobieranie szczegółów technicznych. Dane zapisane w pliku: {}", tech_csv_filename)

