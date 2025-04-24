import csv
import requests
from bs4 import BeautifulSoup
from config import (driver, date, setup_logging)

# Define shop name
shop_name = "elektromarket"
shop_url = "https://elektromarket.pl"

# Define CSV filenames
csv_filename = f"output/{shop_name}_{date}.csv"
log_filename = f"output/log_{shop_name}_{date}.log"

# Define CSV columns
fieldnames = ["date", "title", "price", "product_link", "availability"]

# Function for downloading page content (also handles connection problems)
def fetch_page(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error loading the page {url}: {e}")
        return None

# Setup logger
logger = setup_logging(log_filename)
logger.info("Starting scraping.")
logger.info("CSV File: {}", csv_filename)
logger.info("Log File: {}", log_filename)

with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    links = ["telefony-100/telefony-stacjonarne-101.html", "telefony-100/telefony-komorkowe-i-smartfony-102.html"]

    for link in links:
        page = 1

        while True:
            # Currently all smartphones are temporarily unavailable, so this is a temporary link
            url = f"https://elektromarket.pl/kategorie/{link}?priceFrom=&priceTill=&orderBy=priceHit&perPage=20&page={page}"

            page_content = fetch_page(url)
            if not page_content:
                break
            soup = BeautifulSoup(page_content, "html.parser")

            products = soup.find_all(class_='left')

            for product in products:
                availability = False
                price_text = "0"
                product_info = product.find_next_sibling(class_="right")
                try:
                    # Retrieve title and product link
                    link_element = product.find('a')
                    title = link_element.get('title', 'Brak tytułu')
                    product_link = link_element.get('href', '')

                    # Skip downloading prices for unavailable items
                    if product_info.find('span', class_='boxRed'):
                        logger.info(f"  Product temporarily unavailable: {title}")

                    # Retrieve product price
                    else:
                        availability = True
                        try:
                            price_element = product_info.find(class_="priceCurrent")
                            if price_element and price_element.contents:
                                price_text = f"{price_element.contents[0]}.{price_element.find('sup').text}"
                        except Exception as e:
                            logger.error(f"Error while checking price: {e}")

                    writer.writerow({
                        "title": title,
                        "date": date,
                        "price": price_text,
                        "product_link": shop_url + product_link,
                        "availability": availability
                    })
                    logger.info(f"  Scraped: {title}")
                except Exception as e:
                    logger.error(f"Error processing product: {e}")

            try:
                if not soup.find(class_='forward'):
                    logger.info("No 'next page' button - scraping finished.")
                    break
            except Exception as e:
                logger.error(f"Error checking next page: {e}")
                break

            page += 1
    logger.complete()
    logger.info(f"Scraping completed. Data saved in file: {csv_filename}")