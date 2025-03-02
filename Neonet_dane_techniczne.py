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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Konfiguracja folderu output
output_folder = "output"
os.makedirs(output_folder, exist_ok=True)

# Ustawienia sklepu oraz bieżącej daty
shop_name = "neonet"
today = datetime.now().strftime("%Y-%m-%d")

# Wyszukujemy pliki CSV wygenerowane przez pierwszy skrypt – zakładamy, że mają w nazwie "neonet"
csv_pattern = os.path.join(output_folder, f"{shop_name}_*.csv")
log_filename = os.path.join(output_folder, f"log_tech_details_{shop_name}_{today}.log")

# Konfiguracja logowania za pomocą loguru (format zgodny z przykładowymi logami)
logger.remove()
log_format = "{time:YYYY-MM-DDTHH:mm:ss.SSSSSSZZ} - {level} - {message}"
logger.add(log_filename, level="INFO", format=log_format, encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)

logger.info("Rozpoczęcie skryptu pobierania szczegółów technicznych.")
logger.info("Plik logu: {}", log_filename)

# Wyszukanie najnowszego pliku CSV wygenerowanego przez pierwszy skrypt
csv_files = glob.glob(csv_pattern)
if not csv_files:
    logger.error("Nie znaleziono plików CSV pasujących do wzorca {}", csv_pattern)
    exit(1)


def extract_date(filename):
    base = os.path.basename(filename)
    parts = base.replace(".csv", "").split("_")
    for part in parts:
        try:
            return datetime.strptime(part, "%Y-%m-%d")
        except ValueError:
            continue
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
            product_data.append({"product_link": row["product_link"]})
logger.info("Znaleziono {} produktów do przetworzenia.", len(product_data))

# Konfiguracja Selenium (Firefox, Geckodriver)
firefox_binary_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
service = Service("geckodriver.exe")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.binary_location = firefox_binary_path
driver = webdriver.Firefox(service=service, options=options)


def scrape_tech_details(url):
    global driver
    tech_details = {}
    max_attempts = 3
    attempts = 0
    while attempts < max_attempts:
        try:
            driver.get(url)
            # Czekamy maksymalnie 5 sekund na pojawienie się kontenera z danymi technicznymi
            container = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH,
                     '//section[@class="FeaturedTechnicalSpecificationsScss-root-oUb" and @role="presentation"]')
                )
            )
            table = container.find_element(By.XPATH, './/table[@data-id="tableFeaturedTechnicalSpecifications"]')
            rows = table.find_elements(By.XPATH, './/tr')
            for row in rows:
                try:
                    key = row.find_element(By.XPATH, './td[1]').text.strip().replace(":", "")
                    value = row.find_element(By.XPATH, './td[2]').text.strip()
                    tech_details[key] = value
                except Exception as inner_e:
                    logger.info("Błąd przy przetwarzaniu detalu: {}", inner_e)
            return tech_details
        except Exception as e:
            if "Browsing context has been discarded" in str(e):
                logger.error(
                    "Błąd 'Browsing context has been discarded' dla URL {}: {}. Próba ponownego uruchomienia drivera.",
                    url, e)
                try:
                    driver.quit()
                except Exception:
                    pass
                driver = webdriver.Firefox(service=service, options=options)
                time.sleep(1)
            else:
                logger.error("Błąd przy otwieraniu URL {}: {}", url, e)
            attempts += 1
    return tech_details


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
        logger.info("Zakończono przetwarzanie: {}", url)

driver.quit()
logger.info("Zakończono pobieranie szczegółów technicznych. Dane zapisane w pliku: {}", tech_csv_filename)
logger.complete()
