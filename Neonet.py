import csv
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger

# Utworzenie folderu output, jeśli nie istnieje
os.makedirs("output", exist_ok=True)

# Ustawienia nazwy sklepu oraz daty
shop_name = "neonet"
today = datetime.now().strftime("%Y-%m-%d")
csv_filename = f"output/{shop_name}_{today}.csv"
log_filename = f"output/log_{shop_name}_{today}.log"

# Konfiguracja logowania przy użyciu loguru
logger.remove()
log_format = "{time:YYYY-MM-DD HH:mm:ss,SSS} - {level} - {message}"
logger.add(log_filename, level="INFO", format="{time} - {level} - {message}", encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)

logger.info("Rozpoczęto scraping.")
logger.info("Plik CSV: {}", csv_filename)
logger.info("Plik logu: {}", log_filename)

# Konfiguracja Firefoksa i Geckodrivera
firefox_binary_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
service = Service("geckodriver.exe")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.binary_location = firefox_binary_path
driver = webdriver.Firefox(service=service, options=options)

with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
    fieldnames = ["title", "product_link", "price", "image_url", "reviews"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    base_url = "https://www.neonet.pl/smartfony-i-navi/smartfony.html"

    # Pobieramy maksymalną liczbę stron z paginacji
    driver.get(base_url)
    try:
        pagination_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "section.listingPaginationScss-paginationSection-1VV input[type='number']")
            )
        )
        max_page = int(pagination_input.get_attribute("max"))
        logger.info("Maksymalna liczba stron: {}", max_page)
    except Exception as e:
        logger.error("Nie udało się pobrać maksymalnej liczby stron: {}", e)
        max_page = 1

    page = 1
    while page <= max_page:
        url = base_url if page == 1 else f"{base_url}?p={page}"
        logger.info("Scraping strony {}: {}", page, url)
        driver.get(url)

        # czekamy na pojawienie się przynajmniej jednego produktu
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "section[data-neonet-product-id]"))
            )
        except Exception as e:
            logger.error("Produkty nie załadowały się na stronie {}: {}", page, e)

        # Szybsze scrollowanie – skracamy opóźnienia do 0.5 sekundy
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            for _ in range(2):
                body.send_keys(Keys.END)
                time.sleep(0.5)
                body.send_keys(Keys.HOME)
                time.sleep(0.5)
            body.send_keys(Keys.END)
            time.sleep(0.5)
        except Exception as e:
            logger.error("Błąd podczas wysyłania klawiszy END/HOME: {}", e)

        # Czekamy do 5 sekund, aż załadują się przynajmniej 20 produktów
        try:
            WebDriverWait(driver, 5).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "section[data-neonet-product-id]")) >= 20
            )
        except Exception as e:
            logger.info("Nie udało się załadować pełnej liczby produktów, pobieram to co jest dostępne.")

        products = driver.find_elements(By.CSS_SELECTOR, "section[data-neonet-product-id]")
        if not products:
            logger.info("Brak produktów na stronie, przechodzę do kolejnej.")
            page += 1
            continue

        # Iteracja po produktach
        for product in products:
            try:
                title_element = product.find_element(By.XPATH, './/h2[contains(@class, "listingItemHeaderScss-name")]')
                title = title_element.text.strip()
                link_element = title_element.find_element(By.XPATH, "./ancestor::a")
                product_link = link_element.get_attribute("href")
                price_element = product.find_element(By.XPATH, './/span[@data-marker="UIPriceSimple"]')
                price = price_element.text.strip()

                try:
                    img_element = product.find_element(By.XPATH, './/img')
                    image_url = img_element.get_attribute("src")
                except Exception as e:
                    image_url = ""
                    logger.info("Brak obrazka dla produktu '{}'.", title)

                try:
                    review_section = product.find_element(By.CSS_SELECTOR, "section.ratingStarsScss-wrapper-1mq")
                    rating_span = review_section.find_element(By.CSS_SELECTOR, "span.ratingStarsScss-rating-3xe")
                    style_attr = rating_span.get_attribute("style")  # np. "width: 100%;"
                    rating_percent = style_attr.split("width:")[1].split("%")[0].strip()
                    rating_value = round(float(rating_percent) / 20, 1)
                    count_span = review_section.find_element(By.CSS_SELECTOR, "span.ratingStarsScss-count-1T-")
                    review_count_text = count_span.text.strip()
                    review_count = review_count_text.strip("()")
                    reviews = f"{rating_value}/5 ({review_count} opinii)"
                except Exception as e:
                    reviews = ""
                    logger.info("Brak opinii dla produktu '{}'.", title)

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

        page += 1

driver.quit()
logger.info("Zakończono scraping. Dane zapisane w pliku: {}", csv_filename)
logger.complete()
