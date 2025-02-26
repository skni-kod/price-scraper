# Biblioteki
import os
import glob
from loguru import logger
import re
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Konfiguracja Firefoksa i Geckodrivera
# Dla osób z windowsem https://github.com/mozilla/geckodriver/releases/download/v0.35.0/geckodriver-v0.35.0-win32.zip

# Utworzenie folderu output, jeśli nie istnieje
os.makedirs("output", exist_ok = True)

# Ustawienia nazwy sklepu oraz daty
shop_name = "morele"
today = datetime.now().strftime("%Y-%m-%d")
csv_filename = f"output/{shop_name}_{today}.csv"
log_filename = f"output/log_{shop_name}_{today}.log"

log_folder = "output"
logger.remove()  # usuwa domyślne ustawienia

log_format = "{time:YYYY-MM-DD HH:mm:ss,SSS} - {level} - {message}"

logger.add(log_filename, level="INFO", format="{time} - {level} - {message}", encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)

logger.info("Rozpoczęto scraping.")
logger.info("Plik CSV: {}", csv_filename)
logger.info("Plik logu: {}", log_filename)


firefox_binary_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
service = Service("geckodriver.exe")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.binary_location = firefox_binary_path
driver = webdriver.Firefox(service=service, options=options)



# Definiujemy pola CSV
fieldnames = ["title", "product_link", "price", "num_of_opinions", "rating", "additional_info"] 


with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    page = 1
    while True:
        # Ustalanie URL: dla pierwszej strony używamy podstawowego adresu, a kolejne strony mają parametr ?p=
        if page == 1:
            url = "https://www.morele.net/kategoria/smartfony-280/"
        else:
            url = f"https://www.morele.net/kategoria/smartfony-280/,,,,,,,,0,,,,/{page}/"
        print(f"Scraping strony {page}: {url}")

        driver.get(url)
        products = driver.find_elements(By.XPATH,
                                        '//div[@class="cat-product card"]')

        if not products:
            logger.info("Brak produktów na stronie, kończę scraping.")
            break

        # Iteracja po produktach na stronie
        for product in products:
            try:
                # Pobranie tytułu oraz linku produktu
                link_element = product.find_element(By.XPATH, './/a[@class="productLink"]')
                title = link_element.get_attribute("title")
                product_link = link_element.get_attribute("href")
                title = title.replace("Smartfon", "").strip()  # Obcięcie słowa "smartfon" z nazwy
                przed_gb, po_gb = (re.split(r'GB\s*', title, maxsplit=1) + [""])[:2]
                lista_po_gb = po_gb.split()
                lista_po_gb = [x for x in lista_po_gb if x!= "-"]

                # Pobranie ceny
                try:
                    price_element = WebDriverWait(product, 1).until(
                        EC.presence_of_element_located((By.XPATH, './/div[@class="price-new"]'))
                    )
                    price = price_element.text.strip()
                    price = re.sub(r'[^\d,]', '', price)
                    price = price.replace(',', '.')
                    price = float(price)
                except:
                    price = 0
                    logger.info(f"Nie wykryto ceny dla: {title}")

                try:
                    num_of_opinions = product.find_element(By.XPATH, './/span[@class="rating-count"]').text
                    match = re.search(r"\d+", num_of_opinions)
                    num_of_opinions = int(match.group()) if match else 0
                except:
                    num_of_opinions = 0
                    logger.info(f"Nie wykryto liczby opinii dla: {title}")

                try:
                    rating = product.find_element(By.XPATH,'.//input[@type="radio" and @checked="checked"]').get_attribute("value")
                except:
                    rating = 0
                    logger.info(f"Nie wykryto oceny dla: {title}")

                # Zapis do pliku CSV
                writer.writerow({
                    "title": przed_gb,
                    "product_link": product_link,
                    "price": price,
                    "num_of_opinions": num_of_opinions,
                    "rating": rating,
                    "additional_info": lista_po_gb,
                })
                logger.info("Scraped: {}", title)
            
            except Exception as e:
                logger.error(f"Błąd podczas przetwarzania produktu: {str(e)}")
    
        # Sprawdzenie, czy przycisk „nawiguj do następnej strony” jest dostępny
        try:
            next_arrow = driver.find_elements(By.XPATH, '//a[@class="pagination-btn" and i[@class="icon-arrow-right"]]')

            if not next_arrow:
                logger.info("Brak przycisku 'następna strona' – zakończono scraping.")
                break
        except Exception as e:
            logger.error("Błąd przy sprawdzaniu następnej strony: {}", e)
            break

        page += 1

driver.quit()
logger.complete()
logger.info("Zakończono scraping. Dane zapisane w pliku: {}",csv_filename)