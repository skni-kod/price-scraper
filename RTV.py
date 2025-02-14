import re
from loguru import logger
import csv
import json
from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


firefox_binary_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
service = Service("geckodriver.exe")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.binary_location = firefox_binary_path
driver = webdriver.Firefox(service=service, options=options)


fieldnames = ["title", "date", "price", "product_link", "rating", "num_of_opinions", "tech_details"]
today_date = datetime.today().strftime("%d-%m-%Y")
output_file = f"RTV_telefony_{today_date}.csv"

logger.remove()
logger.add(f'log_RTV_{today_date}.log',
           format="{time: MMMM D, YYYY - HH:mm:ss} {level} --- <red>{message}</red>",
           serialize=True,
           level='INFO',)

with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()


    page = 1
    while True:

        
        if page == 1:
            url = "https://www.euro.com.pl/telefony-komorkowe.bhtml"
        else:
            url = f"https://www.euro.com.pl/telefony-komorkowe,strona-{page}.bhtml" 
        print(f"Scraping strony {page}: {url}")

        driver.get(url)

        #Czekamy na załadowanie produktów (na razie na sleep)
        time.sleep(4)
        

        # Pobieramy wszystkie produkty na stronie
        products = driver.find_elements(By.XPATH,
                                        '//div[@class="product-medium-box"]')    
        if not products:
            logger.info("Brak produktów na stronie, kończę scraping")
            break

         # Iteracja po produktach na stronie
        for product in products:

            try:
                # Pobranie tytułu oraz linku
                link_element = product.find_element(By.XPATH, './/a[@class="product-medium-box-intro__link"]')
                title = link_element.text
                product_link = link_element.get_attribute("href")

                # Pobranie ceny
                parted_price_total = product.find_element(By.XPATH, './/span[@class="parted-price-total"]')
                parted_price_decimal = product.find_element(By.XPATH, './/span[@class="parted-price-decimal"]')

                price_total_text = f"{parted_price_total.text.strip()},{parted_price_decimal.text.strip()}"

                # Zapis do pliku CSV
                writer.writerow({
                    "title": title,
                    "date": today_date,
                    "price": price_total_text,
                    "product_link": product_link,

                })
                print(f"Scraped: {title}")
                

            except Exception as e:
                logger.error(f"Błąd przy przetwarzaniu produktu: {e}")


        # Czekamy na przycisk 'Załaduj więcej'
        try:
            next_button = driver.find_element(By.XPATH, '//a[@data-aut-id="show-more-products-button"]')
            if next_button.is_enabled():
                print("Przechodzę na następną stronę...")
                page += 1
            else:
                logger.error(f"Brak przycisku 'Załaduj więcej' – zakończono scraping.")
                break
        except Exception as e:
            logger.error(f"Błąd przy klikaniu przycisku 'Załaduj więcej': {e}")
            break

driver.quit()
logger.info("Zakończono scraping. Dane zapisane w pliku:")
print("Zakończono scraping. Dane zapisane w pliku:", output_file)