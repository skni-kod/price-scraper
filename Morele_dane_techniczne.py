# Biblioteki
import os
import glob
from loguru import logger
import json
import time
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service

# Konfiguracja Firefoksa i Geckodrivera
# Dla osób z windowsem https://github.com/mozilla/geckodriver/releases/download/v0.35.0/geckodriver-v0.35.0-win32.zip

# Utworzenie folderu output, jeśli nie istnieje
output_folder = "output"
os.makedirs(output_folder, exist_ok = True)

# Ustawienia nazwy sklepu oraz daty
shop_name = "morele"
today = datetime.now().strftime("%Y-%m-%d")
csv_filename = os.path.join(output_folder, f"{shop_name}_{today}.csv")
log_filename = os.path.join(output_folder, f"log_tech_details_{shop_name}_{today}.log")

logger.remove()  # usuwa domyślne ustawienia
log_format = "{time:YYYY-MM-DD HH:mm:ss,SSS} - {level} - {message}"
logger.add(log_filename, level="INFO", format="{time} - {level} - {message}", encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)

logger.info("Rozpoczęto scraping.")
logger.info("Plik CSV: {}", csv_filename)
logger.info("Plik logu: {}", log_filename)

csv_pattern = os.path.join(output_folder, f"{shop_name}_*.csv")
print(csv_pattern)
csv_files = glob.glob(csv_pattern)
if not csv_files:
    logger.error("Nie znaleziono plików CSV pasujących do wzorca {}", csv_pattern)
    exit(1)

def extract_date(filename):
    base = os.path.basename(filename)
    date_str = base.replace(f"{shop_name}_","").replace(".csv","")
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

product_data = []
with open(latest_csv_file, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get("product_link"):
            product_data.append({
                "product_link": row["product_link"],
                })
logger.info("Znaleziono {} produktów do przetworzenia.", len(product_data))

firefox_binary_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
service = Service("geckodriver.exe")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.binary_location = firefox_binary_path
driver = webdriver.Firefox(service=service, options=options)

def scrape_tech_details(url):
    tech_details = {}
    tech_details2 = {}
    try:
        driver.get(url)
        # time.sleep(2) może się przyda, może nie
        attributes_container = driver.find_element(By.CSS_SELECTOR, '#specification')
        expert_recom = attributes_container.find_element(By.CSS_SELECTOR, 'div > div.product-specification__wrapper > div.expert-table.c-label-description--orange > ul')
        data_phone = expert_recom.find_elements(By.XPATH, './/li')
        spec_table = attributes_container.find_element(By.CSS_SELECTOR, 'div > div.product-specification__wrapper > div.product-specification__table > div:nth-child(1) > div')

        tech_data = []
        for i in data_phone:
            tech_data.append(i.text.strip())
        tech_details = {item.split("\n", 1)[0]: item.split("\n", 1)[1] for item in tech_data}
        tech_data.clear()
        spec_table = attributes_container.find_element(By.CSS_SELECTOR,'div > div.product-specification__wrapper > div.product-specification__table')
        data_phone = spec_table.find_elements(By.XPATH,'.//div[@class="group__specification"]')

        for j in data_phone:
            tech_data.append(j.text.strip())
            
        for item in tech_data:  # Iterujemy po elementach listy
            text = item.split('\n')  # Rozdzielamy na klucze i wartości
            for j in range(0, len(text) - 1, 2):  # Przechodzimy co dwa elementy
                tech_details2[text[j]] = text[j + 1]  # Dodajemy do słownika
        tech_details.update(tech_details2)
    except Exception as e:
            logger.error("Błąd przy otwieraniu URL {}: {}", url, e)
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

driver.quit()
logger.complete()
logger.info("Zakończono pobieranie szczegółów technicznych. Dane zapisane w pliku: {}", tech_csv_filename)