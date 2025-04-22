import csv
import json
import glob
import os
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import driver, setup_logging

# Configuration
shop_name = "neonet"
output_folder = "output"
os.makedirs(output_folder, exist_ok=True)

# Find the most recent CSV file
csv_files = glob.glob(os.path.join(output_folder, f"{shop_name}_*.csv"))
if not csv_files:
    print("No CSV files found.")
    exit(1)

def extract_date_from_filename(filename):
    base = os.path.basename(filename).replace(f"{shop_name}_", "").replace(".csv", "")
    try:
        return datetime.strptime(base, "%d-%m-%Y-%H-%M-%S")
    except ValueError:
        return None

csv_files_with_dates = [(f, extract_date_from_filename(f)) for f in csv_files]
csv_files_with_dates = [x for x in csv_files_with_dates if x[1] is not None]
if not csv_files_with_dates:
    print("No CSV files with valid date format found.")
    exit(1)

csv_files_with_dates.sort(key=lambda x: x[1], reverse=True)
input_csv, detected_date = csv_files_with_dates[0]

# Output file paths
timestamp = detected_date.strftime("%d-%m-%Y-%H-%M-%S")
output_csv = f"{output_folder}/tech_details_{shop_name}_{timestamp}.csv"
log_filename = f"{output_folder}/log_tech_details_{shop_name}_{timestamp}.log"

# Logger
logger = setup_logging(log_filename)
logger.info("Starting technical details scraper.")
logger.info("Input file: {}", input_csv)
logger.info("Output file: {}", output_csv)
logger.info("Log file: {}", log_filename)

# Load product links from input CSV
product_data = []
with open(input_csv, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get("product_link"):
            product_data.append({"product_link": row["product_link"]})

logger.info("Found {} products to process.", len(product_data))

# Scraping function
def scrape_tech_details(url):
    tech_details = {}
    for attempt in range(3):
        try:
            driver.get(url)
            container = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//section[@class="FeaturedTechnicalSpecificationsScss-root-oUb" and @role="presentation"]')
                )
            )
            table = container.find_element(By.XPATH, './/table[@data-id="tableFeaturedTechnicalSpecifications"]')
            rows = table.find_elements(By.XPATH, './/tr')
            for row in rows:
                try:
                    key = row.find_element(By.XPATH, './td[1]').text.strip().replace(":", "")
                    value = row.find_element(By.XPATH, './td[2]').text.strip()
                    tech_details[key] = value
                except Exception as inner_e:
                    logger.info("Error processing detail: {}", inner_e)
            return tech_details
        except Exception as e:
            logger.error("Attempt {} failed for URL {}: {}", attempt + 1, url, e)
            time.sleep(1)
    return tech_details

# Save results to output file
with open(output_csv, mode="w", newline="", encoding="utf-8") as tech_csvfile:
    writer = csv.DictWriter(tech_csvfile, fieldnames=["product_link", "tech_details"])
    writer.writeheader()
    for item in product_data:
        url = item["product_link"]
        logger.info("Processing: {}", url)
        details = scrape_tech_details(url)
        writer.writerow({
            "product_link": url,
            "tech_details": json.dumps(details, ensure_ascii=False)
        })
        logger.info("Finished processing: {}", url)

from config import driver as _driver
_driver.quit()
logger.info("Technical details scraping completed. Data saved to file: {}", output_csv)
logger.complete()