# Biblioteki
import csv
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Konfiguracja Firefoksa i Geckodrivera
service = Service("/usr/local/bin/geckodriver")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
driver = webdriver.Firefox(service=service, options=options)

# Plik CSV, do którego zapiszemy dane
output_file = "komputronik_telefony.csv"
# Definiujemy pola CSV
fieldnames = ["title", "product_link", "price", "image_url", "reviews", "tech_details"]

with open(output_file, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    page = 1
    while True:
        # Ustalanie URL: dla pierwszej strony używamy podstawowego adresu, a kolejne strony mają parametr ?p=
        if page == 1:
            url = "https://www.komputronik.pl/category/1596/telefony.html"
        else:
            url = f"https://www.komputronik.pl/category/1596/telefony.html?p={page}"
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
                                        '//div[@data-name="listingTile"]')
        if not products:
            print("Brak produktów na stronie, kończę scraping.")
            break

        # Iteracja po produktach na stronie
        for product in products:
            try:
                # Pobranie tytułu oraz linku produktu
                link_element = product.find_element(By.XPATH, './/a[@title]')
                title = link_element.get_attribute("title")
                product_link = link_element.get_attribute("href")

                # Pobranie ceny produktu
                price_element = product.find_element(By.XPATH,
                                                     './/div[@data-name="listingPrice"]//div[@data-price-type="final"]')
                price = price_element.text.strip()

                # Pobranie URL obrazka produktu
                img_element = product.find_element(By.XPATH, './/img')
                image_url = img_element.get_attribute("src")

                # Pobieranie danych technicznych
                tech_details = {}

                # Część 1: Dane widoczne (np. kody systemowy/producenta)
                try:
                    code_elements = product.find_elements(By.XPATH,
                                                          './/div[contains(@class, "mt-6") and contains(@class, "hidden")]/p')
                    for p in code_elements:
                        text = p.text.strip()
                        if text and ':' in text:
                            key, value = text.split(":", 1)
                            tech_details[key.strip()] = value.strip()
                except Exception as e:
                    print("Błąd przy pobieraniu danych kodowych:", e)

                # Część 2: Szczegóły techniczne z accordionu
                try:
                    accordion = product.find_element(By.XPATH, './/div[@data-role="accordion"]')
                    details_container = accordion.find_element(By.XPATH, './/div[contains(@class, "py-4")]')
                    detail_elements = details_container.find_elements(By.XPATH, './/div[@class="py-1"]')
                    for detail in detail_elements:
                        spans = detail.find_elements(By.TAG_NAME, "span")
                        if len(spans) >= 2:
                            key = spans[0].get_attribute("textContent").strip().replace(":", "")
                            value = spans[1].get_attribute("textContent").strip()
                            tech_details[key] = value
                except Exception as e:
                    print("Błąd przy pobieraniu szczegółów technicznych:", e)

                # Pobieranie opinii (łączymy ocenę oraz liczbę opinii w jedno pole "reviews")
                try:
                    review_element = product.find_element(By.XPATH,
                                                          './/p[contains(@class, "text-base") and contains(@class, "leading-none")]')
                    rating = review_element.find_element(By.XPATH,
                                                         './/span[contains(@class, "font-bold")]').text.strip()
                    opinions = review_element.find_element(By.XPATH,
                                                           './/span[not(contains(@class, "font-bold"))]').text.strip()
                    reviews = f"{rating} {opinions}"
                except Exception as e:
                    reviews = ""

                # Zapis do pliku CSV
                writer.writerow({
                    "title": title,
                    "product_link": product_link,
                    "price": price,
                    "image_url": image_url,
                    "reviews": reviews,
                    "tech_details": json.dumps(tech_details, ensure_ascii=False)
                })
                print(f"  Scraped: {title}")
            except Exception as e:
                print("Błąd przy przetwarzaniu produktu:", e)

        # Sprawdzenie, czy przycisk „nawiguj do następnej strony” jest dostępny
        try:
            next_arrow = driver.find_elements(By.XPATH, '//a[@aria-label="nawiguj do następnej strony"]')
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
