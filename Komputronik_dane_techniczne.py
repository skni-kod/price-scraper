import csv
import json
import glob
import os
import time
from datetime import datetime
from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service

# Konfiguracja folderu output
output_folder = "output"
os.makedirs(output_folder, exist_ok=True)

# Ustawienia sklepu oraz bieżącej daty
shop_name = "komputronik"
today = datetime.now().strftime("%Y-%m-%d")
csv_filename = os.path.join(output_folder, f"{shop_name}_{today}.csv")
log_filename = os.path.join(output_folder, f"log_tech_details_{shop_name}_{today}.log")

# Konfiguracja logowania za pomocą loguru
# Usuwamy domyślnego handlera i dodajemy nowe z określonym formatem
logger.remove()  # Usuwa domyślny handler logowania
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

# Konfiguracja Selenium (Firefox, Geckodriver)
service = Service("/usr/local/bin/geckodriver")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
driver = webdriver.Firefox(service=service, options=options)

def scrape_tech_details(url):
    """
    Funkcja otwiera stronę produktu i próbuje pobrać wszystkie detale techniczne.
    """
    tech_details = {}
    try:
        driver.get(url)
        time.sleep(2)  # krótkie oczekiwanie na załadowanie strony

        attributes_container = driver.find_element(By.XPATH, '//div[@data-name="productAttributes"]')
        detail_elements = attributes_container.find_elements(
            By.XPATH, './/div[contains(@class, "mt-4") or contains(@class, "space-y-2")]'
        )
        for element in detail_elements:
            try:
                p_elements = element.find_elements(By.TAG_NAME, 'p')
                label_elements = element.find_elements(By.TAG_NAME, 'label')
                if p_elements and label_elements:
                    key = p_elements[0].text.replace(":", "").strip()
                    checked_label = None
                    for label in label_elements:
                        try:
                            input_el = label.find_element(By.TAG_NAME, 'input')
                            if input_el.get_attribute("checked") is not None:
                                checked_label = label
                                break
                        except Exception:
                            continue
                    if checked_label:
                        value = checked_label.find_element(By.TAG_NAME, 'span').text.strip()
                    else:
                        value = label_elements[0].find_element(By.TAG_NAME, 'span').text.strip()
                    tech_details[key] = value
                else:
                    span_elements = element.find_elements(By.TAG_NAME, 'span')
                    if len(span_elements) >= 2:
                        key = span_elements[0].text.replace(":", "").strip()
                        value = span_elements[1].text.strip()
                        tech_details[key] = value
            except Exception as inner_e:
                logger.info("Błąd przy przetwarzaniu detalu: {}", inner_e)
    except Exception as e:
        logger.error("Błąd przy otwieraniu URL {}: {}", url, e)
    return tech_details

# Przygotowanie pliku wynikowego z danymi technicznymi w folderze output
tech_csv_filename = os.path.join(output_folder, f"tech_details_{shop_name}_{today}.csv")
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
driver.quit()
logger.complete()
logger.info("Zakończono pobieranie szczegółów technicznych. Dane zapisane w pliku: {}", tech_csv_filename)
