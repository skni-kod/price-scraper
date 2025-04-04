import os
import re
from loguru import logger
import csv
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

# Konfiguracja Firefoksa i Geckodrivera
service = Service("/usr/local/bin/geckodriver")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
driver = webdriver.Firefox(service=service, options=options)

# Konfiguracja folderu output
output_folder = "output"
os.makedirs(output_folder, exist_ok=True)

# Ustawienia sklepu oraz bieżącej daty
shop_name = "MediaExpert"
today_date = datetime.now().strftime("%Y-%m-%d")
csv_filename = os.path.join(output_folder, f"{shop_name}_{today_date}.csv")
log_filename = os.path.join(output_folder, f"{shop_name}_{today_date}.log")


# Definiujemy pola CSV
fieldnames = ["date", "title", "price",  "rating", "num_of_opinions", "product_link"] #Fajnie by było znać datę kiedy jaka cena występowała
shop_name = "MediaExpert"

logger.remove()
log_format = "{time:YYYY-MM-DD HH:mm:ss,SSS} - {level} - {message}"
logger.add(log_filename, level="INFO", format="{time} - {level} - {message}", encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)

logger.info("Rozpoczęto scraping.")
logger.info("Plik CSV: {}", csv_filename)
logger.info("Plik logu: {}", log_filename)


with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    page = 1
    while True:
        # Ustalanie URL: dla pierwszej strony używamy podstawowego adresu, a kolejne strony mają parametr ?p=
        if page == 1:
            url = "https://www.mediaexpert.pl/smartfony-i-zegarki/smartfony"
        else:
            url = f"https://www.mediaexpert.pl/smartfony-i-zegarki/smartfony?page={page}"
        logger.info("Scraping strony {}: {}", page, url)

        driver.get(url)

        try:
            # Czekamy aż produkty się załadują
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.offer-box")))
        except Exception as e:
            logger.error("Błąd oczekiwania na produkty: {}",e)
            break
        # time.sleep(1)

        products = driver.find_elements(By.CSS_SELECTOR, "div.offer-box")
        products_count = len(products)
        logger.info("Znaleziono {} produktów.", products_count)

        if not products:
            logger.info("Brak produktów na stronie, kończę scraping.")
            break

        def process_product(index, retries=3):
            for attempt in range(retries):
                try:
                    # Pobierz aktualną listę produktów, aby nie operować na "starych" referencjach
                    products = driver.find_elements(By.CSS_SELECTOR, "div.offer-box")
                    product = products[index]

                    # Przewiń produkt do widoku – wymusza załadowanie lazy-loaded elementów
                    driver.execute_script("arguments[0].scrollIntoView(true);", product)
                    time.sleep(1)

                    # Pobierz nazwę produktu (jeśli brak – prawdopodobnie to nie jest właściwy produkt)
                    product_name_elements = product.find_elements(By.CSS_SELECTOR, "h2.name a")
                    if not product_name_elements:
                        return None
                    product_name = product_name_elements[0].text.strip()

                    # Pobierz ocenę, uwzględniając pełne oraz połowkowe gwiazdki
                    try:
                        rating_element = product.find_element(By.CSS_SELECTOR, "div.product-rating")
                        # Pełne gwiazdki (np. <i class="icon-star01 is-filled">)
                        full_stars = rating_element.find_elements(By.CSS_SELECTOR, "i.icon-star01.is-filled")
                        # Połowkowe gwiazdki (np. <svg class="is-half-filled">)
                        half_stars = rating_element.find_elements(By.CSS_SELECTOR, "svg.is-half-filled")
                        rating = len(full_stars) + 0.5 * len(half_stars)
                        # Pobierz liczbę opinii
                        reviews_elements = rating_element.find_elements(By.CSS_SELECTOR, "span.count-number")
                        reviews = reviews_elements[0].text.strip() if reviews_elements else "0"
                    except Exception:
                        rating = None
                        reviews = None
                        logger.info("Brak opinii dla produktu '{}'.", product_name)

                    try:
                        # Pobranie tytułu oraz linku produktu
                        link_element = product.find_element(By.CSS_SELECTOR, 'h2.name a.ui-link')
                        product_link = link_element.get_attribute("href")

                        # Pobranie ceny produktu
                        try:
                            cala = product.find_element(By.XPATH, './/span[@class="whole"]').text.strip()
                            grosze = product.find_element(By.XPATH, './/span[@class="cents"]').text.strip()
                            waluta = product.find_element(By.XPATH, './/span[@class="currency"]').text.strip()
                            price_text = f"{cala}.{grosze}{waluta}"
                        except:
                            price_text = None
                            logger.info("Nie wykryto ceny: {}",product_name)

                        return product_name, rating, reviews, price_text, product_link
                    except:
                        logger.error("Problem z pobraniem")

                except StaleElementReferenceException:
                    if attempt < retries - 1:
                        # time.sleep(1)
                        continue  # ponów próbę
                    else:
                        raise

        seen_products = set()

        for i in range(products_count):
            try:
                result = process_product(i)
                if result is None:
                    continue  # pomijamy elementy, które nie zawierają danych produktu
                product_name, rating, reviews, price_text, product_link = result

                # Sprawdzanie duplikatów
                if product_name in seen_products:
                    logger.info("Produkt '{}' został już przetworzony, pomijam duplikat.", product_name)
                    continue
                seen_products.add(product_name)

                # Usuwanie NNBSP (Unicode U+202F) z ceny
                price_text = price_text.replace("\u202F", "")

                # Zapis do pliku CSV
                writer.writerow({
                    "date": today_date,
                    "title": product_name,
                    "price": price_text,
                    "rating": rating,
                    "num_of_opinions": reviews,
                    "product_link": product_link
                })
                logger.info("Scraped: {}", product_name)

            except Exception as e:
                logger.error("Błąd przy przetwarzaniu produktu: {}", e)

        # Sprawdzenie, czy przycisk kolejnej strony jest dostępny
        try:
            number = driver.find_element(By.XPATH, '//div[@class="lastpage-button"]').text
            # print(number)
            if int(number) <= page:
                logger.info("Ostatnia strona – zakończono scraping.")
                break
        except Exception as e:
            logger.error("Błąd przy sprawdzaniu następnej strony: {}",e)
            break

        page += 1

driver.quit()
logger.complete()
logger.info(f"Zakończono scraping. Dane zapisane w pliku: {csv_filename}")