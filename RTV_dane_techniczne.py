import glob
import os
import re
import csv
import json
from datetime import datetime
import time

from loguru import logger

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Konfiguracja folderu output
output_folder = "output"
os.makedirs(output_folder, exist_ok=True)

# Ustawienia nazwy sklepu oraz daty
SHOP_NAME = "rtv_euro_agd"
fieldnames = ["title", "date", "price", "product_link", "rating", "num_of_opinions", "tech_details"]
today_date = datetime.now().strftime("%Y-%m-%d")
csv_filename  = f"output/{SHOP_NAME}_{today_date}.csv"
log_filename = f"output/tech_details_log_{SHOP_NAME}_{today_date}.log"

# Konfiguracja logowania przy użyciu loguru:
logger.remove()
log_format = "{time:YYYY-MM-DD HH:mm:ss,SSS} - {level} - {message}"
logger.add(log_filename, level="INFO", format="{time} - {level} - {message}", encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)

# Konfiguracja Firefoksa i Geckodrivera
service = Service("geckodriver.exe")
options = webdriver.FirefoxOptions()
options.binary_location = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
options.add_argument("--headless")

logger.info("Rozpoczęcie skryptu pobierania szczegółów technicznych.")
logger.info("Plik CSV: {}", csv_filename)
logger.info("Plik logu: {}", log_filename)

try:
    driver = webdriver.Firefox(service=service, options=options)

    csv_pattern = os.path.join(output_folder, f"{SHOP_NAME}_*.csv")
    csv_files = glob.glob(csv_pattern)
    if not csv_files:
        logger.error("Nie znaleziono plików CSV pasujących do wzorca {}", csv_pattern)
        exit(1)


    def extract_date(filename):
        base = os.path.basename(filename)
        # Zakładamy, że nazwa pliku ma format: RTV-EURO-AGD_YYYY-MM-DD.csv
        date_str = base.replace(f"{SHOP_NAME}_", "").replace(".csv", "")
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            logger.error("Nie udało się przekształcić daty z formatu '{}' na '%Y-%m-%d'. Sprawdzony ciąg: {}", "%Y-%m-%d", date_str)
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
        driver.get(url)
        time.sleep(3)
        tech_details = {}
        try:
            #Zamknięcie banera z cookies który zasłania przycisk "Rozwiń pełne dane techniczne"
            try:
                cookie_button = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[contains(@id, "onetrust-accept-btn-handler")]'))
                )
                cookie_button.click()
                logger.info("Kliknięto przycisk akceptacji cookies.")
            except TimeoutException:
                logger.info("Brak banera cookies, kontynuujemy.")

            # Sprawdzenie, czy przycisk "Rozwiń pełne dane techniczne" jest obecny, a jeśli tak, kliknięcie w niego
            try:
                show_more_button = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[contains(@class, "cta") and .//span[contains(text(), "Rozwiń pełne dane techniczne")]]'))
                )
                driver.execute_script("arguments[0].scrollIntoView();", show_more_button)  # Przewinięcie do przycisku
                show_more_button.click()
            except TimeoutException:
                logger.warning("Nie znaleziono przycisku 'Rozwiń pełne dane techniczne', kontynuujemy bez klikania")
    
            time.sleep(2)  # krótkie oczekiwanie na załadowanie strony
            attributes_container = driver.find_element(By.XPATH, '//div[@class="technical-attributes"]')
            detail_elements = attributes_container.find_elements(By.XPATH, './/div[@class="technical-attributes__section"]')
            for element in detail_elements:
                try:
                    tr_elements = element.find_elements(By.TAG_NAME, 'tr')
                    if tr_elements:
                        for tr_element in tr_elements:
                            #Pomijamy elementy z linkami do pobrania plików (instrukcji, gwarancji itd.)
                            if tr_element.find_elements(By.TAG_NAME, 'a'):
                                logger.info(f"Pominięto element '{key}', ponieważ zawiera link.")
                                continue
                            try:
                                key_element = tr_element.find_elements(By.TAG_NAME, 'th')
                                value_element = tr_element.find_elements(By.TAG_NAME, 'span')

                                if key_element and value_element:
                                    key = key_element[0].text.replace(":", "").strip()
                                    value = value_element[0].text.strip()
                                    tech_details[key] = value
                                else:
                                    logger.warning("Pominięto wiersz, ponieważ brakuje 'th' lub 'span'.")
                            except Exception as inner_e:
                                logger.warning("Błąd przy przetwarzaniu detalu: {}", inner_e)
                except Exception as inner_e:
                    logger.warning("Błąd przy przetwarzaniu detalu: {}", inner_e)
        except Exception as e:
            logger.error("Błąd przy otwieraniu URL {}: {}", url, e)
        return tech_details        

    # Przygotowanie pliku wynikowego z danymi technicznymi w folderze output
    tech_csv_filename = os.path.join(output_folder, f"tech_details_{SHOP_NAME}_{today_date}.csv")
    fieldnames = ["product_link", "tech_details"]

    with open(tech_csv_filename, mode="a", newline="", encoding="utf-8") as tech_csvfile:
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
    
finally:
    #Zamknięcie przeglądarki
    driver.quit()
    logger.complete()
    logger.info("Zakończono pobieranie szczegółów technicznych. Dane zapisane w pliku: {}", tech_csv_filename)