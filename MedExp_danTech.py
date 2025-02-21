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

# from Komputronik import output_file

# Konfiguracja Firefoksa i Geckodrivera

firefox_binary_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
service = Service("geckodriver.exe")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.binary_location = firefox_binary_path
driver = webdriver.Firefox(service=service, options=options)

# Definiujemy pola CSV
fieldnames = ["title", "tech_info"]
today_date = datetime.today().strftime("%d-%m-%Y")

logger.remove()
logger.add(f'medExpDaneTech_{today_date}.log',
           format="{time: MMMM D, YYYY - HH:mm:ss} {level} --- <red>{message}</red>",
           serialize=True,
           level='WARNING',)


pliki = glob.glob("mediaExpert_*.csv")

def newfile(file):
    data = file.split("_")[-1].replace(".csv", "")
    return datetime.strptime(data, "%d-%m-%Y")

input_file = max(pliki, key=newfile)
output_file = f"medExpDaneTech_{today_date}.csv"
# print(output_file)

with open(input_file, mode="r", encoding="utf-8") as csvfile, open(output_file, mode="w", newline="\n", encoding="utf-8") as output:
    reader = csv.DictReader(csvfile)
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    test = 0
    for row in reader:
        url = row["product_link"]
        # print(url)
        driver.get(url)

        # try:
        #     # Czekamy aż produkty się załadują
        #     wait = WebDriverWait(driver, 10)
        #     wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,"table.list")))
        # except Exception as e:
        #     print("Błąd oczekiwania na produkty:", e)
        #     logger.error(f"Błąd oczekiwania na produkty: {e}")
        #     break

        time.sleep(2)
        if test%20==0:
            time.sleep(10)

        # Pobranie tytułu

        # try:
        #     title = driver.find_element(By.CSS_SELECTOR,"h1.is-title").text
        #     title = title.replace("Smartfon", "").strip()
        #
        #     # print(title)
        #
        # except Exception as e:
        #     print("Błąd przy przetwarzaniu produktu: ", e)
        #     logger.error(f"Błąd przy przetwarzaniu produktu: {e}")
        title = row["title"]


        # Pobieranie danych technicznych
        tech_details = {}

        # Część 2: Szczegóły techniczne z accordionu
        try:
            accordion = driver.find_element(By.XPATH,
                                            './/table[contains(@class, "list") and contains(@class, "attributes")]')
            details_container = accordion.find_elements(By.XPATH, './/tr[@class="item"]')
            for detail in details_container:
                # key = detail.find_element(By.XPATH,'.//th//span[@class="attribute-name"]').text.strip().replace(":", "")
                key = detail.find_element(By.XPATH,'.//th//span[contains(@class, "attribute-name")]').text.strip().replace(":","")
                value = detail.find_element(By.XPATH, './/td//span[contains(@class, "attribute-value")]').text.strip()
                tech_details[key] = value
        except Exception as e:
            print("Błąd przy pobieraniu szczegółów technicznych:", e)

        writer.writerow({
            "title": title,
            "tech_info": json.dumps(tech_details, ensure_ascii=False)
        })
        test+=1
        print(f"  Scraped: {title}")
        # time.sleep(1)


# Zamknięcie przeglądarki
driver.quit()
print("Zakończono scraping. Dane zapisane w pliku:", output_file)
logger.info(f"Zakończono scraping. Dane zapisane w pliku: {output_file}")