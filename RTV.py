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
log_filename = f"output/log_{SHOP_NAME}_{today_date}.log"

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


logger.info("Rozpoczęto scraping.")
logger.info("Plik CSV: {}", csv_filename)
logger.info("Plik logu: {}", log_filename)

try:
    driver = webdriver.Firefox(service=service, options=options)

    with open(csv_filename , mode="a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        page = 1
        while True: 
            if page == 1:
                url = "https://www.euro.com.pl/telefony-komorkowe.bhtml"
            else:
                url = f"https://www.euro.com.pl/telefony-komorkowe,strona-{page}.bhtml"
            logger.info(f"Scraping strony {page}: {url}")

            driver.get(url)

            #Czekamy na załadowanie produktów
            try:
                WebDriverWait(driver, 10).until(
                EC.visibility_of_all_elements_located((By.CLASS_NAME, "product-medium-box"))
            )
            except TimeoutException:
                logger.warning("Element 'product-medium-box' nie pojawił się")
            

            # Pobieramy wszystkie produkty na stronie
            products = driver.find_elements(By.XPATH,
                                            '//div[@class="product-medium-box"]')    
            if not products:
                logger.info("Brak produktów na stronie, kończę scraping.")
                break

            # Iteracja po produktach na stronie
            for product in products:

                try:
                    # Pobranie tytułu oraz linku
                    link_element = product.find_element(By.XPATH, './/a[@class="product-medium-box-intro__link"]')
                    title = link_element.text
                    product_link = link_element.get_attribute("href")

                    # Pobranie ceny
                    parted_price_total = product.find_element(By.XPATH, './/span[@class="parted-price-total"]')
                    parted_price_decimal = product.find_element(By.XPATH, './/span[@class="parted-price-decimal"]')

                    price_total_text = f"{parted_price_total.text.strip()},{parted_price_decimal.text.strip()}"

                    # Pobieranie oceny
                    try:
                        rating = "{}/5".format(product.find_element(By.XPATH, './/span[@class="client-rate__rate"]').text)
                        num_of_opinions = product.find_element(By.XPATH, './/span[@class="client-rate__opinions"]').text.split()[0]
                    except Exception as e:
                            logger.warning(f"Brak oceny lub opinii dla produktu: {title}")
                            rating = "Brak opinii"
                            num_of_opinions = "Brak opinii"

                    # Pobieranie danych technicznych
                    tech_details = {}
                    try:
                        technical_data_div = product.find_element(By.XPATH, './/div[@class="technical-data"]')
                        technical_data_items = technical_data_div.find_elements(By.XPATH, './/li[@class="technical-data__list-item"]')

                        for data_item in technical_data_items:
                            data_item_key = data_item.find_element(By.XPATH, './/span[@class="technical-data__list-item-name"]').text.strip().replace(":", "")
                            data_item_value = data_item.find_element(By.XPATH, './/span[@class="technical-data-item-text"]').text.strip()
                            tech_details[data_item_key] = data_item_value

                    except Exception as e:
                        logger.error(f"Błąd przy pobieraniu szczegółów technicznych dla {title}: {e}")
                    
                    # Zapis do pliku CSV
                    writer.writerow({
                        "title": title,
                        "date": today_date,
                        "price": price_total_text,
                        "product_link": product_link,
                        "rating": rating,
                        "num_of_opinions": num_of_opinions,
                        "tech_details": json.dumps(tech_details, ensure_ascii=False)
                    })
                    logger.info(f"Scraped: {title}")
                    
                except Exception as e:
                    logger.error(f"Błąd przy przetwarzaniu produktu: {e}")

            # Czekamy na przycisk 'Załaduj więcej'
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//a[@data-aut-id="show-more-products-button"]'))
                )
                logger.info("Przechodzę na następną stronę...")
                page += 1
            except Exception:
                logger.info("Brak przycisku 'Załaduj więcej' – zakończono scraping.")
                break
finally:
    #Zamknięcie przeglądarki
    driver.quit()
    logger.complete()
    logger.info(f"Zakończono scraping. Dane zapisane w pliku: {csv_filename }")