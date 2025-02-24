import re
from loguru import logger
import csv
import json
import time
import glob
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Konfiguracja Firefoksa i Geckodrivera

firefox_binary_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
service = Service("geckodriver.exe")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.binary_location = firefox_binary_path
driver = webdriver.Firefox(service=service, options=options)

# Definiujemy pola CSV
fieldnames = ["product_link", "tech_info"]
today_date = datetime.today().strftime("%d-%m-%Y")

shop_name = "mediaExpert"
log_filename = f"{shop_name}Tech_{today_date}.log"

logger.remove()
log_format = "{time:YYYY-MM-DD HH:mm:ss,SSS} - {level} - {message}"
logger.add(log_filename, level="INFO", format="{time} - {level} - {message}", encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)


pliki = glob.glob("mediaExpert_*.csv")

if not pliki:
    logger.error("Nie znaleziono plików CSV pasujących do wzorca")
    exit(1)

def newfile(file):
    data = file.split("_")[-1].replace(".csv", "")
    return datetime.strptime(data, "%d-%m-%Y")

input_file = max(pliki, key=newfile)
output_file = f"medExpDaneTech_{today_date}.csv"

logger.info("Rozpoczęcie skryptu pobierania szczegółów technicznych.")
logger.info("Plik CSV: {}", input_file)
logger.info("Plik logu: {}", log_filename)

def scrape_tech_details(url):
    tech_details = {}
    try:
        driver.get(url)
        time.sleep(2)

        attributes_container = driver.find_element(By.CSS_SELECTOR,"table.list.attributes")
        detail_elements = attributes_container.find_elements(By.CSS_SELECTOR, 'tbody tr.item')

        for element in detail_elements:
            try:
                key = element.find_element(By.CSS_SELECTOR, 'th.name.attribute span').text.strip().replace(":", "")
                value = element.find_element(By.CSS_SELECTOR, 'td.values.attribute span').text.strip()
                tech_details[key] = value
            except Exception as inner_e:
                logger.info("Błąd przy przetwarzaniu detalu: {}", inner_e)
    except Exception as e:
        logger.error("Błąd przy otwieraniu URL {}: {}", url, e)
    return tech_details


product_data = []
with open(input_file, mode="r", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        if row.get("product_link"):
            product_data.append({
                "product_link": row["product_link"],
            })
logger.info("Znaleziono {} produktów do przetworzenia.", len(product_data))
timer = 0
with open(output_file, mode="w", newline="\n", encoding="utf-8") as output:
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for item in product_data:
        timer += 1
        if(timer % 20 == 0): time.sleep(10)
        url = item["product_link"]
        logger.info("Przetwarzanie: {}", url)
        details = scrape_tech_details(url)

        writer.writerow({
            "product_link": url,
            "tech_info": json.dumps(details, ensure_ascii=False)
        })

# Zamknięcie przeglądarki
driver.quit()
logger.complete()
# print("Zakończono scraping. Dane zapisane w pliku:", output_file)
logger.info(f"Zakończono scraping. Dane zapisane w pliku: {output_file}")