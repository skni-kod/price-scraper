import csv
import json
import glob
import os
import time
import gc
from datetime import datetime
from loguru import logger
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service

# Konfiguracja folderu output
output_folder = "output"
os.makedirs(output_folder, exist_ok=True)

# Ustawienia sklepu oraz bieżącej daty
shop_name = "MediaExpert"
today = datetime.now().strftime("%Y-%m-%d")
csv_filename = os.path.join(output_folder, f"{shop_name}_{today}.csv")
log_filename = os.path.join(output_folder, f"log_tech_details_{shop_name}_{today}.log")

# Konfiguracja logowania za pomocą loguru
logger.remove()  # usunięcie domyślnego handlera
log_format = "{time:YYYY-MM-DD HH:mm:ss,SSS} - {level} - {message}"
logger.add(log_filename, level="INFO", format="{time} - {level} - {message}", encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)

logger.info("Rozpoczęcie skryptu pobierania szczegółów technicznych.")
logger.info("Plik CSV: {}", csv_filename)
logger.info("Plik logu: {}", log_filename)

# Wyszukanie najnowszego pliku CSV wygenerowanego przez pierwszy skrypt
csv_pattern = os.path.join(output_folder, f"{shop_name}_*.csv")
csv_files = glob.glob(csv_pattern)
if not csv_files:
    logger.error("Nie znaleziono plików CSV pasujących do wzorca {}", csv_pattern)
    exit(1)

# Ponieważ format nazwy pliku to mediaExpert_YYYY-MM-DD.csv, wystarczy wybrać najnowszy plik
latest_csv_file = max(csv_files)
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

# Konfiguracja Firefoksa i Geckodrivera
service = Service("/usr/local/bin/geckodriver")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
driver = webdriver.Firefox(service=service, options=options)

def scrape_tech_details_mediaexpert(url):
    """
    Funkcja otwiera stronę produktu MediaExpert i pobiera dane techniczne z tabeli.
    """
    tech_details = {}
    try:
        driver.get(url)
        time.sleep(2)  # oczekiwanie na załadowanie strony

        # Szukanie tabeli z atrybutami
        table = driver.find_element(By.CSS_SELECTOR, 'table.list.attributes')
        rows = table.find_elements(By.TAG_NAME, 'tr')
        for row in rows:
            try:
                th_elements = row.find_elements(By.TAG_NAME, 'th')
                td_elements = row.find_elements(By.TAG_NAME, 'td')
                if not th_elements or not td_elements:
                    continue
                # Pobieramy nazwę atrybutu i usuwamy zbędne znaki
                key = th_elements[0].text.replace(":", "").strip()
                # Pobieramy wartość atrybutu
                value = td_elements[0].text.strip()
                tech_details[key] = value
            except Exception as inner_e:
                logger.info("Błąd przy przetwarzaniu detalu: {}", inner_e)
    except Exception as e:
        logger.error("Błąd przy otwieraniu URL {}: {}", url, e)
    return tech_details

# Przygotowanie pliku wynikowego z danymi technicznymi w folderze output
tech_csv_filename = os.path.join(output_folder, f"tech_details_{shop_name}_{today}.csv")
fieldnames = ["product_link", "tech_details"]

# Liczba stron po których restartujemy driver
restart_interval = 10

with open(tech_csv_filename, mode="w", newline="", encoding="utf-8") as tech_csvfile:
    writer = csv.DictWriter(tech_csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for i, item in enumerate(product_data, start=1):
        url = item["product_link"]
        logger.info("Przetwarzanie: {}", url)
        details = scrape_tech_details_mediaexpert(url)
        writer.writerow({
            "product_link": url,
            "tech_details": json.dumps(details, ensure_ascii=False)
        })

        # Czyszczenie ciasteczek i wywołanie garbage collectora
        driver.delete_all_cookies()
        gc.collect()

        # Restart driver co restart_interval stron
        if i % restart_interval == 0:
            logger.info("Restartowanie przeglądarki po {} stronach", i)
            driver.quit()
            driver = webdriver.Firefox(service=service, options=options)

# Zamknięcie przeglądarki
driver.quit()
logger.complete()
logger.info("Zakończono pobieranie szczegółów technicznych. Dane zapisane w pliku: {}", tech_csv_filename)
