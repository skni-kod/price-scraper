import os
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from loguru import logger
import json

# Tworzenie folderu output
os.makedirs("output", exist_ok=True)

# Ustawienia nazwy sklepu oraz daty
shop_name = "mediamarkt"
today = datetime.now().strftime("%Y-%m-%d")
csv_filename = f"output/{shop_name}_{today}.csv"
log_filename = f"output/log_{shop_name}_{today}.log"

# Konfiguracja loggera
logger.remove()  # Usuwa domyślne ustawienia
logger.add(log_filename, level="INFO", format="{time} - {level} - {message}", encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format="{time} - {level} - {message}")

logger.info("Rozpoczęto scraping.")
logger.info("Plik CSV: {}", csv_filename)
logger.info("Plik logu: {}", log_filename)

# Konfiguracja przeglądarki Firefox
firefox_binary_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
service = Service("geckodriver.exe")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.binary_location = firefox_binary_path

# Nagłówki kolumn w pliku CSV
fieldnames = ["title", "product_link", "price", "num_of_opinions", "rating"]

# Otwarcie pliku CSV do zapisu
with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    page = 1
    while True:
        # Inicjalizacja nowego webdrivera za każdym razem, bo driver.get(url) nie działa bo mediamarkt ma captche
        driver = webdriver.Firefox(service=service, options=options)

        url = f"https://mediamarkt.pl/pl/category/smartfony-25983.html?page={page}"
        logger.info(f"Przetwarzanie strony: {url}")

        # Otwórz stronę
        driver.get(url)
        driver.execute_script("document.body.style.transform = 'scale(0.3)'")
        try:
            # Czekaj na załadowanie produktów
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.XPATH, '//div[@data-test="mms-product-card"]'))
            )

            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            json_scripts = soup.find_all('script', type='application/ld+json')

            for script in json_scripts:
                try:
                    json_data = json.loads(script.string)
                    
                    if json_data.get('@type') == 'ItemList':
                        for item in json_data.get('itemListElement', []):
                            product = item.get('item', {})
                            
                            # Odczytanie danych
                            name = product.get('name').replace("Smartfon ", "")
                            price = product.get('offers', {}).get('price')
                            rating_value = product.get('aggregateRating', {}).get('ratingValue')
                            review_count = product.get('aggregateRating', {}).get('reviewCount')
                            url = product.get('url')
                            
                            writer.writerow({
                                "title": name,
                                "product_link": url,
                                "price": price,
                                "num_of_opinions": review_count,
                                "rating": rating_value,
                            })
                            logger.info(f"Zapisano produkt: {name}")
                except json.JSONDecodeError as e:
                    logger.error(f"Błąd podczas parsowania JSON: {e}")
                    continue
            driver.quit()
            page += 1

        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania strony {page}: {e}")
            driver.quit()
            break

# Zamknij przeglądarkę po zakończeniu
logger.info("Zakończono scraping.")