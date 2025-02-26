import time
import os
import csv
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from loguru import logger

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

# Lista User-Agentów
user_agents = [
    # Tylko desktopowe User-Agenty:
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

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
        # Wybierz losowy User-Agent
        
        user_agent = random.choice(user_agents)
        options.set_preference("general.useragent.override", user_agent) #rotacja agentami musi być bo mediamarkt ma zabezpieczenia przed szybkim ładowaniem stron, więc albo 
        #nowa sesja webdriver to zmienia albo losowy user-agent, któreś z tych, ale działa

        # Inicjalizacja przeglądarki z nowym User-Agentem
        driver = webdriver.Firefox(service=service, options=options)

        url = f"https://mediamarkt.pl/pl/category/smartfony-25983.html?page={page}"
        logger.info(f"Przetwarzanie strony: {url} z User-Agent: {user_agent}")

        # Otwórz stronę
        driver.get(url)
        driver.execute_script("document.body.style.transform = 'scale(0.3)'") #jak ktoś to usunie to zamiast 12 produktów będzie pokazywać 9, scrollowanie przez strone nie działa

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.XPATH, '//div[@data-test="mms-product-card"]'))
            )

            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")

   
            products = soup.find_all("div", {"data-test": "mms-product-card"})
            logger.info(f"Znaleziono {len(products)} produktów na stronie {page}.")

            # Jeśli nie ma produktów, zakończ pętlę
            if not products:
                logger.info("Brak produktów na stronie. Kończenie scrapowania.")
                driver.quit() 
                break

            for product in products:
                try:
                    title = product.find("p", {"data-test": "product-title"}).text.strip().replace("Smartfon", "")
                except:
                    title = ""
                    logger.info(f"Nie wykryto tytułu dla produktu na stronie {page}.")

                try:
                    price = product.find("span", {"class": "sc-e0c7d9f7-0 bPkjPs"}).text.strip()
                except:
                    price = 0
                    logger.info(f"Nie wykryto ceny dla: {title}")

                try:
                    link_element = product.find("a", {"data-test": "mms-router-link-product-list-item-link"})
                    full_link = f"https://mediamarkt.pl{link_element.get('href')}" if link_element else "Brak linku"
                except:
                    full_link = "Brak linku"
                    logger.info(f"Nie wykryto linku dla: {title}")

                try:
                    num_of_opinions = product.find("span", {"data-test": "mms-customer-rating-count"}).text
                except:
                    num_of_opinions = 0
                    logger.info(f"Nie wykryto liczby opinii dla: {title}")

                try:
                    rating = product.find("div", {"data-test": "mms-customer-rating"}).get("aria-label")
                    rating_value = rating.split(":")[1].split()[0] if rating else 0
                except:
                    rating_value = 0
                    logger.info(f"Nie wykryto oceny dla: {title}")

                # Zapisz dane do pliku CSV
                writer.writerow({
                    "title": title,
                    "product_link": full_link,
                    "price": price,
                    "num_of_opinions": num_of_opinions,
                    "rating": rating_value,
                })
                logger.info(f"Zapisano produkt: {title}")

            # Przejdź do następnej strony

            page += 1
        except:
            break

        # Zamknij przeglądarkę przed przejściem do następnej strony
        driver.quit()

# Zamknij przeglądarkę po zakończeniu
logger.info("Zakończono scraping.")