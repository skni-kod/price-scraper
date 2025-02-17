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

firefox_binary_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
service = Service("geckodriver.exe")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.binary_location = firefox_binary_path
driver = webdriver.Firefox(service=service, options=options)

# Plik CSV, do którego zapiszemy dane
output_file = "mediaExpert_telefony.csv"
# Definiujemy pola CSV
fieldnames = ["title", "date", "price", "product_link", "rating", "num_of_opinions", "tech_details"] #Fajnie by było znać datę kiedy jaka cena występowała
today_date = datetime.today().strftime("%d-%m-%Y")

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

        driver.get(url)

        # Ponieważ strona ładuje się statycznie, nie trzeba czekać na załadowanie elementów.
        # Jeśli jednak w przyszłości strona zacznie ładować dane dynamicznie, można odkomentować poniższe linie:
        #
        try:
            # Czekamy aż produkty się załadują
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_all_elements_located((By.XPATH, '//div[@data-v-5ad6e584]')))
        except Exception as e:
            print("Błąd oczekiwania na produkty:", e)
            break

        products = driver.find_elements(By.XPATH,
                                        '//div[@data-v-5ad6e584]')

        if not products:
            print("Brak produktów na stronie, kończę scraping.")
            break

        # Iteracja po produktach na stronie
        for product in products:

            try:
                # Pobranie tytułu oraz linku produktu
                link_element = product.find_element(By.XPATH, './/a[@href]')
                title = link_element.text
                product_link = link_element.get_attribute("href")

                # Pobranie ceny produktu
                cala = product.find_element(By.XPATH,'.//span[@class="whole"]').text.strip()
                grosze =product.find_element(By.XPATH,'.//span[@class="cents"]').text.strip()
                waluta = product.find_element(By.XPATH,'.//span[@class="currency"]').text.strip()

                price_text = f"{cala}.{grosze} {waluta}"
                #price_text = price_element.text.strip()



                #Moim zdaniem niepotrzebne jest to pobieranie url'a obrazka
                # Pobranie URL obrazka produktu
                # img_element = product.find_element(By.XPATH, './/img')
                # image_url = img_element.get_attribute("src")

                # Pobieranie danych technicznych
                tech_details = {}

                # Część 1: Dane widoczne (np. kody systemowy/producenta)
                try:
                    code_elements = product.find_elements(By.XPATH,
                                                          './/span[@class="is-regular"]')
                    for p in code_elements:
                        #if text and ':' in text: Komputronik zawsze ma podany jakiś kod producenta lub systemowy, szkoda czasu żeby ciągle to sprawdzać
                            # key, value = text.split(":", 1)
                            # tech_details[key.strip()] = value.strip()
                        key, value = p.text.split(":", 1)
                        tech_details[key.strip()] = value.strip()
                except Exception as e:
                    print("Błąd przy pobieraniu danych kodowych:", e)

                # Część 2: Szczegóły techniczne z accordionu
                try:
                    accordion = product.find_element(By.XPATH, './/table[contains(@class, "list") and contains(@class, "attributes")]')
                    details_container = accordion.find_elements(By.XPATH, './/tr[@class="item"]')
                    for detail in details_container:
                        # key = detail.find_element(By.XPATH,'.//th//span[@class="attribute-name"]').text.strip().replace(":", "")
                        key = detail.find_element(By.XPATH,'.//th//span[contains(@class, "attribute-name")]').text.strip().replace(":", "")
                        value = detail.find_element(By.XPATH,'.//td//span[contains(@class, "attribute-value")]').text.strip()
                        tech_details[key] = value


                except Exception as e:
                    print("Błąd przy pobieraniu szczegółów technicznych:", e)

                # Pobieranie opinii (łączymy ocenę oraz liczbę opinii w jedno pole "reviews")
                try:
                    review_element = product.find_element(By.XPATH,
                                                          './/div[contains(@class, "product-rating")]')
                    fullStar = review_element.find_elements(By.XPATH,
                                                           './/i[contains(@class, "is-filled")]')
                    halfStar = review_element.find_elements(By.XPATH,
                                                           './/svg[contains(@class, "is-half-filled")]')
                    opinions = review_element.find_element(By.XPATH,
                                                           './/span[contains(@class, "count-number")]').text.strip()
                    # opinions = product.find_element(By.XPATH,
                    #                                        'div[0]/div[0]/div[1]/div[0]/span[0]/span[0]').text.strip()

                    rating = len(fullStar)
                    # print(rating)
                    if len(halfStar)>0:
                        rating += 0.5


                    # match = re.search(r"\d+", opinions)
                    # opinions = int(match.group()) if match else 0
                except:
                    rating = 0
                    opinions = 0

                #if(opinions !=0): opinions = opinions - 1

                # Zapis do pliku CSV
                writer.writerow({
                    "title": title,
                    "date": today_date,
                    "price": price_text,
                    "product_link": product_link,
                    #"image_url": image_url,
                    "rating": rating,
                    "num_of_opinions": opinions,
                    "tech_details": json.dumps(tech_details, ensure_ascii=False)
                })
                print(f"  Scraped: {title}")
            except Exception as e:
                print("Błąd przy przetwarzaniu produktu:", e)

        # Sprawdzenie, czy przycisk „nawiguj do następnej strony” jest dostępny
        try:
            number = driver.find_element(By.XPATH, '//div[@class="lastpage-button"]').text
            # print(number)
            if int(number) <= page:
                print("Ostatnia strona – zakończono scraping.")
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