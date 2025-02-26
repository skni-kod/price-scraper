# Biblioteki
import os
import glob
from loguru import logger
import json
import random
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from bs4 import BeautifulSoup

# Konfiguracja Firefoksa i Geckodrivera
# Dla osób z windowsem https://github.com/mozilla/geckodriver/releases/download/v0.35.0/geckodriver-v0.35.0-win32.zip

# Utworzenie folderu output, jeśli nie istnieje
output_folder = "output"
os.makedirs(output_folder, exist_ok = True)

# Ustawienia nazwy sklepu oraz daty
shop_name = "mediamarkt"
today = datetime.now().strftime("%Y-%m-%d")
csv_filename = os.path.join(output_folder, f"{shop_name}_{today}.csv")
log_filename = os.path.join(output_folder, f"log_tech_details_{shop_name}_{today}.log")

logger.remove()  # usuwa domyślne ustawienia
log_format = "{time:YYYY-MM-DD HH:mm:ss,SSS} - {level} - {message}"
logger.add(log_filename, level="INFO", format="{time} - {level} - {message}", encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)

logger.info("Rozpoczęto scraping.")
logger.info("Plik CSV: {}", csv_filename)
logger.info("Plik logu: {}", log_filename)

csv_pattern = os.path.join(output_folder, f"{shop_name}_*.csv")
csv_files = glob.glob(csv_pattern)
if not csv_files:
    logger.error("Nie znaleziono plików CSV pasujących do wzorca {}", csv_pattern)
    exit(1)

def extract_date(filename):
    base = os.path.basename(filename)
    date_str = base.replace(f"{shop_name}_","").replace(".csv","")
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None
csv_files_with_date = [(file, extract_date(file)) for file in csv_files if extract_date(file) is not None]
if not csv_files_with_date:
    logger.error("Żaden z plików CSV nie ma poprawnego formatu daty.")
    exit(1)
csv_files_with_date.sort(key=lambda x: x[1], reverse=True)
latest_csv_file = csv_files_with_date[0][0]
logger.info("Wybrany plik CSV: {}", latest_csv_file)

product_data = []
with open(latest_csv_file, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get("product_link"):
            product_data.append({
                "product_link": row["product_link"],
                })
logger.info("Znaleziono {} produktów do przetworzenia.", len(product_data))

firefox_binary_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
service = Service("geckodriver.exe")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.binary_location = firefox_binary_path

user_agents = [
    # Tylko desktopowe User-Agenty:
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]


def scrape_tech_details(url):
    user_agent = random.choice(user_agents)
    options.set_preference("general.useragent.override", user_agent) #rotacja agentami musi być bo mediamarkt ma zabezpieczenia przed szybkim ładowaniem stron, więc albo 
    #nowa sesja webdriver to zmienia albo losowy user-agent, któreś z tych, ale działa

    # Inicjalizacja przeglądarki z nowym User-Agentem
    driver = webdriver.Firefox(service=service, options=options)
    driver.get(url)
    tech_details = {}  
    data_site = driver.page_source
    soup = BeautifulSoup(data_site, "html.parser")
    products_info = soup.find_all("td",{"class":"sc-27ebc524-0 iIdXkJ"})
    products_info2 = soup.find_all("td",{"sc-27ebc524-0 ca-dqbf sc-35e02872-1 bbGRhm"})
    for i in range(len(products_info)):
        tech_details[products_info[i].text] = products_info2[i].text

    driver.quit()
    return tech_details

tech_csv_filename = os.path.join(output_folder, f"tech_details_{shop_name}_{today}.csv")
fieldnames = ["product_link", "tech_details"]

with open(tech_csv_filename, mode="w", newline="", encoding="utf-8") as tech_csvfile:
    writer = csv.DictWriter(tech_csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for item in product_data:
        url = item["product_link"]
        logger.info("Przetwarzanie: {}", url)
        details = scrape_tech_details(url)
        writer.writerow({
            "product_link": url,
            "tech_details": json.dumps(details, ensure_ascii=False)
        })


logger.complete()
logger.info("Zakończono pobieranie szczegółów technicznych. Dane zapisane w pliku: {}", tech_csv_filename)