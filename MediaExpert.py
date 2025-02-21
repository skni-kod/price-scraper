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

firefox_binary_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
service = Service("geckodriver.exe")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.binary_location = firefox_binary_path
driver = webdriver.Firefox(service=service, options=options)

# Definiujemy pola CSV
fieldnames = ["date", "title", "price",  "rating", "num_of_opinions", "product_link"] #Fajnie by było znać datę kiedy jaka cena występowała
today_date = datetime.today().strftime("%d-%m-%Y")
output_file = f"mediaExpert_{today_date}.csv"

logger.remove()
logger.add(f'mediaExpert_{today_date}.log',
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
            url = "https://www.mediaexpert.pl/smartfony-i-zegarki/smartfony"
        else:
            url = f"https://www.mediaexpert.pl/smartfony-i-zegarki/smartfony?page={page}"
        print(f"Scraping strony {page}: {url}")
        logger.info(f"Scraping strony {page}: {url}")

        driver.get(url)
        time.sleep(1)

        # Ponieważ strona ładuje się statycznie, nie trzeba czekać na załadowanie elementów.
        # Jeśli jednak w przyszłości strona zacznie ładować dane dynamicznie, można odkomentować poniższe linie:
        #
        try:
            # Czekamy aż produkty się załadują
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.offer-box")))
        except Exception as e:
            # print("Błąd oczekiwania na produkty:", e)
            logger.error(f"Błąd oczekiwania na produkty: {e}")
            break
        time.sleep(1)

        products = driver.find_elements(By.CSS_SELECTOR, "div.offer-box")
        products_count = len(products)
        print(f"Znaleziono {products_count} produktów.")


        if not products:
            print("Brak produktów na stronie, kończę scraping.")
            break


        def process_product(index, retries=3):
            """
            Próbuje odczytać dane produktu o danym indeksie, przy maksymalnie `retries` próbach.
            Jeśli element staje się "stale", następuje ponowienie próby.
            """
            for attempt in range(retries):
                try:
                    # Pobierz aktualną listę produktów, aby nie operować na "starych" referencjach
                    products = driver.find_elements(By.CSS_SELECTOR, "div.offer-box")
                    product = products[index]

                    # Przewiń produkt do widoku – wymusza załadowanie lazy-loaded elementów
                    driver.execute_script("arguments[0].scrollIntoView(true);", product)
                    time.sleep(1)  # trochę czasu na załadowanie elementu

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

                    try:
                        # Pobranie tytułu oraz linku produktu
                        link_element = product.find_element(By.XPATH, './/a[@href]')
                        title = link_element.text
                        title = title.replace("Smartfon", "").strip()
                        product_link = link_element.get_attribute("href")

                        # Pobranie ceny produktu
                        try:
                            cala = product.find_element(By.XPATH, './/span[@class="whole"]').text.strip()
                            grosze = product.find_element(By.XPATH, './/span[@class="cents"]').text.strip()
                            waluta = product.find_element(By.XPATH, './/span[@class="currency"]').text.strip()
                            price_text = f"{cala}.{grosze} {waluta}"
                        except:
                            price_text = "Brak Danych"
                            logger.error(f"Nie wykryto ceny: {title}")
                        # price_text = price_element.text.strip()


                        return product_name, rating, reviews, price_text, product_link
                    except:
                        logger.error(f"Problem z pobraniem")

                except StaleElementReferenceException:
                    if attempt < retries - 1:
                        time.sleep(1)
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
                    print(f"Produkt '{product_name}' został już przetworzony, pomijam duplikat.")
                    continue
                seen_products.add(product_name)


                # Zapis do pliku CSV
                writer.writerow({
                    "date": today_date,
                    "title": product_name,
                    "price": price_text,
                    "rating": rating,
                    "num_of_opinions": reviews,
                    "product_link": product_link
                    # "tech_details": json.dumps(tech_details, ensure_ascii=False)
                })
                print(f"  Scraped: {product_name}")

            except Exception as e:
                print(f"Błąd przy produkcie numer {i}: {e}")
                # Sprawdzenie, czy przycisk „nawiguj do następnej strony” jest dostępny
        try:
            number = driver.find_element(By.XPATH, '//div[@class="lastpage-button"]').text
            # print(number)
            if int(number) <= page:
                print("Ostatnia strona – zakończono scraping.")
                logger.info("Ostatnia strona – zakończono scraping.")
                break
        except Exception as e:
            print("Błąd przy sprawdzaniu następnej strony:", e)
            logger.error(f"Błąd przy sprawdzaniu następnej strony: {e}")
            break

        page += 1

driver.quit()
print("Zakończono scraping. Dane zapisane w pliku:", output_file)
logger.info(f"Zakończono scraping. Dane zapisane w pliku: {output_file}")