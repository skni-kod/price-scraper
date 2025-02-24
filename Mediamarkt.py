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

# Create output folder if it doesn't exist
os.makedirs("output", exist_ok=True)

# Set shop name and date
shop_name = "mediamarkt"
today = datetime.now().strftime("%Y-%m-%d")
csv_filename = f"output/{shop_name}_{today}.csv"
log_filename = f"output/log_{shop_name}_{today}.log"

# Configure logging with loguru
logger.remove()
log_format = "{time:YYYY-MM-DD HH:mm:ss,SSS} - {level} - {message}"
logger.add(log_filename, level="INFO", format="{time} - {level} - {message}", encoding="utf-8")
logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)

logger.info("Starting scraping.")
logger.info("CSV file: {}", csv_filename)
logger.info("Log file: {}", log_filename)

# Configure Firefox and Geckodriver
firefox_binary_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
service = Service("geckodriver.exe")
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
options.binary_location = firefox_binary_path
driver = webdriver.Firefox(service=service, options=options)

with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
    fieldnames = ["title", "product_link", "price", "num_of_opinions", "rating"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    page = 1
    while True:
        url = f"https://mediamarkt.pl/pl/category/smartfony-25983.html?page={page}"
        logger.info("Scraping page {}: {}", page, url)

        try:
            driver.get(url)
        except Exception as e:
            logger.error("Failed to load page {}: {}", page, e)
            break  # Exit the loop if the page cannot be loaded


        # Wait for products to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.sc-9012a4b9-0.etGoBU"))
            )
        except Exception as e:
            logger.error("Products did not load on page {}: {}", page, e)
            page += 1
            continue

        # Scroll to load all products
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

#/html/body/div[1]/div[3]/main/div[1]/div[1]/div[2]/div/div[3]/div[1]/div
#/html/body/div[1]/div[3]/main/div[1]/div[1]/div[2]/div/div[3]/div[1]/div/div/div/a/div/p
#/html/body/div[1]/div[3]/main/div[1]/div[1]/div[2]/div/div[3]/div[1]/div/div/div/a

        # Wait for at least 10 products to load
        try:
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "div.sc-9012a4b9-0.etGoBU")) >= 10
            )
        except Exception as e:
            logger.info("Failed to load all products on page {}, scraping available products.", page)

        # Find all products
        products = driver.find_elements(By.XPATH, '//div[@class="sc-bf62a61f-0 jFPeRB sc-59354101-3 cGSKeP sc-3e0d0029-2 dFMUeJ"]')
        if not products:
            logger.info("No products found on page {}, stopping scraping.", page)
            break

        # Iterate over products
        for product in products:
            try:
                title = product.find_element(By.CSS_SELECTOR, "p").text
                product_link = product.find_element(By.XPATH, ".//div/div/a").get_attribute("href")
                price = product.find_element(By.XPATH, ".//div/div/div[4]/div/div/div[2]/span[1]").text.strip()

                try:
                    num_of_opinions = product.find_element(By.XPATH, ".//div/div/div[2]/div/div/div/div[2]/span").text.strip()
                except:
                    num_of_opinions = 0

                try:
                    rating = product.find_element(By.XPATH, ".//div/div/div[2]/div/div/div").text.strip()
                except:
                    rating = 0

                writer.writerow({
                    "title": title,
                    "product_link": product_link,
                    "price": price,
                    "num_of_opinions": num_of_opinions,
                    "rating": rating,
                })
                logger.info("Scraped: {}", title)
            except Exception as e:
                logger.error("Error processing product: {}", e)

        page += 1

driver.quit()
logger.info("Scraping completed. Data saved to: {}", csv_filename)