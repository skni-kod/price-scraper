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
today_date = datetime.today().strftime("%d-%m-%Y")
csv_filename = f"output/{shop_name}_{today_date}.csv"
log_filename = f"output/log_{shop_name}_{today_date}.log"

# Konfiguracja logowania przy użyciu loguru:
logger.remove()
log_format = "{time:YYYY-MM-DD HH:mm:ss,SSS} - {level} - {message}"
logger.add(log_filename, level="INFO", format="{time} - {level} - {message}", encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)

logger.info("Rozpoczęto scraping.")
logger.info("Plik CSV: {}", csv_filename)
logger.info("Plik logu: {}", log_filename)

# Definiujemy pola CSV
fieldnames = ["date", "title", "price", "product_link"]


with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    page = 1

    while True:
        # Aktualnie wszystkie smartfony chwilowo niedostępne, dlatego ustawiłem stacjonarne
        url = f"https://elektromarket.pl/kategorie/telefony-100/telefony-stacjonarne-101.html?priceFrom=&priceTill=&orderBy=priceHit&perPage=20&page={page}"
        requested_page = requests.get(url)
        logger.info(f"Scraping strony {page}: {url}")
        soup = BeautifulSoup(requested_page.text, 'html.parser')

        products = soup.find_all(class_='left')
        # Div-y z produktem oraz z informacjami nie są pogrupowane, kolejno po sobie występują div_left, div_right, br, hr div_left itd
        products_info = soup.find_all(class_='right')

        for i in range(len(products)):
            product = products[i]
            product_info = products_info[i]
            try:
                # Pobranie tytułu oraz linku produktu
                link_element = product.find('a')
                title = link_element['title']
                product_link = link_element['href']

                # Pomijanie niedostępnych elementów
                if product_info.find('span', class_='boxRed'):
                    logger.info(f"  Produkt chwilowo niedostępny: {title}")
                    continue

                # Pobranie ceny produktu
                price_element = product_info.find(class_="priceCurrent")

                price_text = f"{price_element.contents[0]}.{price_element.find('sup').text}"

                # Zapis do pliku CSV
                writer.writerow({
                    "title": title,
                    "date": today_date,
                    "price": price_text,
                    "product_link": product_link,
                })
                logger.info(f"  Scraped: {title}")
            except Exception as e:
                logger.error(f"Błąd przy przetwarzaniu produktu: {e}")

        try:
            next_arrow = soup.find(class_='forward')
            if not next_arrow:
                logger.info("Brak przycisku 'następna strona' – zakończono scraping.")
                break
        except Exception as e:
            logger.error(f"Błąd przy sprawdzaniu następnej strony: {e}")
            break

        page += 1

    logger.info(f"Zakończono scraping. Dane zapisane w pliku: {csv_filename}")