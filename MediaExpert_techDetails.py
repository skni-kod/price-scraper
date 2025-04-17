import csv
import json
import glob
import os
import time
import gc
from loguru import logger
from selenium.webdriver.common.by import By
from config import (driver, date, setup_logging)

# Configuration of output folder
output_folder = "output"
shop_name = "MediaExpert"

# Definition of file names
csv_filename = os.path.join(output_folder, f"{shop_name}_{date}.csv")
log_filename = os.path.join(output_folder, f"log_tech_details_{shop_name}_{date}.log")

# Configuration of login with loguru
logger = setup_logging(log_filename)
logger.info("Begging of scrapping tech details.")
logger.info("CSV file: {}", csv_filename)
logger.info("Log file: {}", log_filename)

# Searching for newest CSV file generated from first script
csv_pattern = os.path.join(output_folder, f"{shop_name}_*.csv")
csv_files = glob.glob(csv_pattern)
if not csv_files:
    logger.error("No CSV file that matches template was found {}", csv_pattern)
    exit(1)

# Because file format was mediaExpert_YYYY-MM-DD.csv, we only need to select newest
latest_csv_file = max(csv_files)
logger.info("Selected CSV file was: {}", latest_csv_file)

# Loading links from CSV file
product_data = []
with open(latest_csv_file, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get("product_link"):
            product_data.append({
                "product_link": row["product_link"],
            })
logger.info("{} products to process.", len(product_data))

def scrape_tech_details_mediaexpert(url):

    tech_details = {}
    try:
        driver.get(url)
        time.sleep(2)  # waiting for a page to laod

        # Searching for attibutes table
        table = driver.find_element(By.CSS_SELECTOR, 'table.list.attributes')
        rows = table.find_elements(By.TAG_NAME, 'tr')
        for row in rows:
            try:
                th_elements = row.find_elements(By.TAG_NAME, 'th')
                td_elements = row.find_elements(By.TAG_NAME, 'td')
                if not th_elements or not td_elements:
                    continue
                # Downloading attribute name, while removing unnecessary signs
                key = th_elements[0].text.replace(":", "").strip()
                # Downloading attibutes valeus
                value = td_elements[0].text.strip()
                tech_details[key] = value
            except Exception as inner_e:
                logger.info("Error while processing details: {}", inner_e)
    except Exception as e:
        logger.error("Error while opening URL {}: {}", url, e)
    return tech_details

# Getting result file ready in output folder
tech_csv_filename = os.path.join(output_folder, f"tech_details_{shop_name}_{date}.csv")
fieldnames = ["product_link", "tech_details"]

# Number of pages, after which we'll reset driver
restart_interval = 10

with open(tech_csv_filename, mode="w", newline="", encoding="utf-8") as tech_csvfile:
    writer = csv.DictWriter(tech_csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for i, item in enumerate(product_data, start=1):
        url = item["product_link"]
        logger.info("Processing: {}", url)
        details = scrape_tech_details_mediaexpert(url)
        writer.writerow({
            "product_link": url,
            "tech_details": json.dumps(details, ensure_ascii=False)
        })

        # Cleaning cookies and startign garbage collector
        driver.delete_all_cookies()
        gc.collect()

        # Driver's reset after restart_interval pages
        if i % restart_interval == 0:
            logger.info("Resetting of browser after {} pages", i)
            driver.quit()
            # driver = webdriver.Firefox(service=service, options=options)

# Closing browser
driver.quit()
logger.complete()
logger.info("End of processing tech details. Data saves to file: {}", tech_csv_filename)