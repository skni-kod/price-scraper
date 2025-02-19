import csv
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from loguru import logger

# Utworzenie folderu output, jeśli nie istnieje
os.makedirs("output", exist_ok=True)

# Ustawienia nazwy sklepu oraz daty
shop_name = "komputronik"
today = datetime.now().strftime("%Y-%m-%d")
csv_filename = f"output/{shop_name}_{today}.csv"
log_filename = f"output/log_{shop_name}_{today}.log"

# Konfiguracja logowania przy użyciu loguru:
# Usuwamy domyślnego handlera i dodajemy nowe z określonym formatem
logger.remove()  # usuwa domyślne ustawienia
log_format = "{time:YYYY-MM-DD HH:mm:ss,SSS} - {level} - {message}"
logger.add(log_filename, level="INFO", format="{time} - {level} - {message}", encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)

logger.info("Rozpoczęto scraping.")
logger.info("Plik CSV: {}", csv_filename)
logger.info("Plik logu: {}", log_filename)

# Konfiguracja Firefoksa i Geckodrivera
service = Service("/usr/local/bin/geckodriver")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
driver = webdriver.Firefox(service=service, options=options)

# Definiujemy pola CSV
fieldnames = ["title", "product_link", "price", "image_url", "reviews"]

with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    page = 1
    while True:
        # Ustalanie URL: dla pierwszej strony używamy podstawowego adresu, a kolejne strony mają parametr ?p=
        if page == 1:
            url = "https://www.komputronik.pl/category/1596/telefony.html"
        else:
            url = f"https://www.komputronik.pl/category/1596/telefony.html?p={page}"
        logger.info("Scraping strony {}: {}", page, url)

        driver.get(url)
        products = driver.find_elements(By.XPATH, '//div[@data-name="listingTile"]')
        if not products:
            logger.info("Brak produktów na stronie, kończę scraping.")
            break

        # Iteracja po produktach na stronie
        for product in products:
            try:
                # Pobranie tytułu oraz linku produktu
                link_element = product.find_element(By.XPATH, './/a[@title]')
                title = link_element.get_attribute("title")
                product_link = link_element.get_attribute("href")

                # Pobranie ceny produktu
                price_element = product.find_element(By.XPATH, './/div[@data-name="listingPrice"]//div[@data-price-type="final"]')
                price = price_element.text.strip()

                # Pobranie URL obrazka produktu
                img_element = product.find_element(By.XPATH, './/img')
                image_url = img_element.get_attribute("src")

                # Pobieranie opinii (łączenie oceny oraz liczby opinii)
                try:
                    review_element = product.find_element(By.XPATH, './/p[contains(@class, "text-base") and contains(@class, "leading-none")]')
                    rating = review_element.find_element(By.XPATH, './/span[contains(@class, "font-bold")]').text.strip()
                    opinions = review_element.find_element(By.XPATH, './/span[not(contains(@class, "font-bold"))]').text.strip()
                    reviews = f"{rating} {opinions}"
                except Exception as e:
                    reviews = ""
                    logger.info("Brak opinii dla produktu '{}'.", title)

                # Zapis do pliku CSV
                writer.writerow({
                    "title": title,
                    "product_link": product_link,
                    "price": price,
                    "image_url": image_url,
                    "reviews": reviews,
                })
                logger.info("Scraped: {}", title)
            except Exception as e:
                logger.error("Błąd przy przetwarzaniu produktu: {}", e)

        # Sprawdzenie, czy przycisk „nawiguj do następnej strony” jest dostępny
        try:
            next_arrow = driver.find_elements(By.XPATH, '//a[@aria-label="nawiguj do następnej strony"]')
            if not next_arrow:
                logger.info("Brak przycisku 'następna strona' – zakończono scraping.")
                break
        except Exception as e:
            logger.error("Błąd przy sprawdzaniu następnej strony: {}", e)
            break

        page += 1

# Zamknięcie przeglądarki
driver.quit()
logger.complete()
logger.info("Zakończono scraping. Dane zapisane w pliku: {}", csv_filename)
