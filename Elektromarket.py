# Biblioteki
from loguru import logger
import csv
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Utworzenie folderu output, jeśli nie istnieje
os.makedirs("output", exist_ok=True)

# Ustawienia nazwy sklepu oraz daty
shop_name = "elektromarket"
shop_url = "https://elektromarket.pl"
today_date = datetime.today().strftime("%Y-%m-%d")
csv_filename = f"output/{shop_name}_{today_date}.csv"
log_filename = f"output/log_{shop_name}_{today_date}.log"

# Funkcja od pobierania zawartości strony z uwzględnieniem możliwości problemów z łączem
def fetch_page(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Błąd podczas pobierania strony {url}: {e}")
        return None

# Konfiguracja logowania przy użyciu loguru:
logger.remove()
log_format = "{time:YYYY-MM-DD HH:mm:ss,SSS} - {level} - {message}"
logger.add(log_filename, level="INFO", format=log_format, encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)

logger.info("Rozpoczęto scraping.")
logger.info("Plik CSV: {}", csv_filename)
logger.info("Plik logu: {}", log_filename)

# Definiujemy pola CSV
fieldnames = ["date", "title", "price", "product_link", "availability"]

with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    links = ["telefony-100/telefony-stacjonarne-101.html", "telefony-100/telefony-komorkowe-i-smartfony-102.html"]

    for link in links:
        page = 1

        while True:
            # Aktualnie wszystkie smartfony chwilowo niedostępne, dlatego ustawiłem stacjonarne
            url = f"https://elektromarket.pl/kategorie/{link}?priceFrom=&priceTill=&orderBy=priceHit&perPage=20&page={page}"

            page_content = fetch_page(url)
            if not page_content:
                break
            soup = BeautifulSoup(page_content, "html.parser")

            products = soup.find_all(class_='left')

            for product in products:
                avibility = False
                price_text = "0"
                product_info = product.find_next_sibling(class_="right")
                try:
                    # Pobranie tytułu oraz linku produktu
                    link_element = product.find('a')
                    title = link_element.get('title', 'Brak tytułu')
                    product_link = link_element.get('href', '')

                    # Pomijanie pobierania ceny niedostępnych elementów
                    if product_info.find('span', class_='boxRed'):
                        logger.info(f"  Produkt chwilowo niedostępny: {title}")

                    # Pobranie ceny produktu
                    else:
                        avibility = True
                        try:
                            price_element = product_info.find(class_="priceCurrent")
                            if price_element and price_element.contents:
                                price_text = f"{price_element.contents[0]}.{price_element.find('sup').text}"
                        except Exception as e:
                            logger.error(f"Błąd przy sprawdzaniu ceny: {e}")

                    # Zapis do pliku CSV
                    writer.writerow({
                        "title": title,
                        "date": today_date,
                        "price": price_text,
                        "product_link": shop_url + product_link,
                        "availability": avibility
                    })
                    logger.info(f"  Scraped: {title}")
                except Exception as e:
                    logger.error(f"Błąd przy przetwarzaniu produktu: {e}")

            try:
                if not soup.find(class_='forward'):
                    logger.info("Brak przycisku 'następna strona' – zakończono scraping.")
                    break
            except Exception as e:
                logger.error(f"Błąd przy sprawdzaniu następnej strony: {e}")
                break

            page += 1
    logger.complete()
    logger.info(f"Zakończono scraping. Dane zapisane w pliku: {csv_filename}")