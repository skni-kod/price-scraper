# Biblioteki
import sys
from loguru import logger
import re
import csv
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Konfiguracja Firefoksa i Geckodrivera
# Dla osób z windowsem https://github.com/mozilla/geckodriver/releases/download/v0.35.0/geckodriver-v0.35.0-win32.zip

firefox_binary_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
service = Service("geckodriver.exe")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.binary_location = firefox_binary_path
driver = webdriver.Firefox(service=service, options=options)



# Definiujemy pola CSV
fieldnames = ["title", "price", "product_link", "num_of_opinions", "rating"] 
today_date = datetime.today().strftime("%d-%m-%Y")
output_file = f"morele_telefony_{today_date}.csv"

logger.remove()
logger.add(f'log_morele_{today_date}.log',
           format="{time: MMMM D, YYYY - HH:mm:ss} {level} --- <red>{message}</red>",
           serialize=True,
           level='WARNING',)

with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
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

        # Ponieważ strona ładuje się statycznie, nie trzeba czekać na załadowanie elementów.
        # Jeśli jednak w przyszłości strona zacznie ładować dane dynamicznie, można odkomentować poniższe linie:
        #
        # try:
        #     # Czekamy aż produkty się załadują
        #     wait = WebDriverWait(driver, 10)
        #     wait.until(EC.presence_of_all_elements_located((By.XPATH, '//div[@data-name="listingTile"]')))
        # except Exception as e:
        #     print("Błąd oczekiwania na produkty:", e)
        #     break

        products = driver.find_elements(By.XPATH,
                                        '//div[@class="cat-product card"]')

        if not products:
            print("Brak produktów na stronie, kończę scraping.")
            break

        # Iteracja po produktach na stronie
        for product in products:
            try:
                # Pobranie tytułu oraz linku produktu
                link_element = product.find_element(By.XPATH, './/a[@class="productLink"]')
                title = link_element.get_attribute("title")
                product_link = link_element.get_attribute("href")
                title = title.replace("Smartfon", "").strip()  # Obcięcie słowa "smartfon" z nazwy

                # Pobranie ceny
                try:
                    price_element = WebDriverWait(product, 1).until(
                        EC.presence_of_element_located((By.XPATH, './/div[@class="price-new"]'))
                    )
                    price_text = price_element.text.strip()
                except:
                    price_text = ""
                    logger.error(f"Nie wykryto ceny dla: {title}")

                try:
                    num_of_opinions = product.find_element(By.XPATH, './/span[@class="rating-count"]').text
                    match = re.search(r"\d+", num_of_opinions)
                    num_of_opinions = int(match.group()) if match else 0
                except:
                    num_of_opinions = 0
                    logger.error(f"Nie wykryto liczby opinii dla: {title}")

                try:
                    rating = product.find_element(By.XPATH,'.//input[@type="radio" and @checked="checked"]').get_attribute("value")
                except:
                    rating = 0
                    logger.error(f"Nie wykryto oceny dla: {title}")

                # Zapis do pliku CSV
                writer.writerow({
                    "title": title,
                    "price": price_text,
                    "product_link": product_link,
                    "num_of_opinions": num_of_opinions,
                    "rating": rating,
                })
                print(f"Scraped: {title}")
            
            except Exception as e:
                logger.error(f"Błąd podczas przetwarzania produktu: {str(e)}")
    
        # Sprawdzenie, czy przycisk „nawiguj do następnej strony” jest dostępny
        try:
            next_arrow = driver.find_elements(By.XPATH, '//a[@class="pagination-btn" and i[@class="icon-arrow-right"]]')

            if not next_arrow:
                print("Brak przycisku 'następna strona' – zakończono scraping.")
                break
        except Exception as e:
            print("Błąd przy sprawdzaniu następnej strony:", e)
            break

        page += 1

        # Opcjonalnie: opóźnienie przed przejściem do kolejnej strony
        # time.sleep(1)

# Zamknięcie przeglądarki
driver.quit()
print("Zakończono scraping. Dane zapisane w pliku:", output_file)