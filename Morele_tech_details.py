from config import(driver, date, setup_logging)
import glob
import json
from datetime import datetime
import os
import csv
from selenium.webdriver.common.by import By


# Create output folder if it does not exist
output_folder = "output"
os.makedirs(output_folder, exist_ok = True)

shop_name = "morele"

# Define CSV columns
fieldnames = ["date", "title", "product_link", "price", "image_url", "reviews"]
 
# Define CSV filenames
csv_filename = f"output/{shop_name}_{date}.csv"
log_filename = f"output/log_{shop_name}_{date}.log"

# Setup logger
logger = setup_logging(log_filename)
logger.info("Starting scraping.")
logger.info("CSV File: {}", csv_filename)
logger.info("Log File: {}", log_filename)


csv_pattern = os.path.join(output_folder, f"{shop_name}_*.csv")
csv_files = glob.glob(csv_pattern)
if not csv_files:
    logger.error("CSV files matching pattern not found {}", csv_pattern)
    exit(1)

def extract_date(filename):
    base = os.path.basename(filename)
    date_str = base.replace(f"{shop_name}_","").replace(".csv","")
    try:
        return datetime.strptime(date_str, "%d-%m-%Y-%H-%M-%S")
    except ValueError:
        return None
    
csv_files_with_date = [(file, extract_date(file)) for file in csv_files if extract_date(file) is not None]
if not csv_files_with_date:
    logger.error("None of the CSV files have the correct date format.")
    exit(1)
    
csv_files_with_date.sort(key=lambda x: x[1], reverse=True)
latest_csv_file = csv_files_with_date[0][0]
logger.info("Selected CSV file: {}", latest_csv_file)

product_data = []
with open(latest_csv_file, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get("product_link"):
            product_data.append({
                "product_link": row["product_link"],
                })
            
logger.info("Found {} products to process.", len(product_data))
def scrape_tech_details(url):
    tech_details = {}
    tech_details2 = {}
    try:
        driver.get(url)
        # time.sleep(2) someday it might be useful
        attributes_container = driver.find_element(By.CSS_SELECTOR, '#specification')
        expert_recom = attributes_container.find_element(By.CSS_SELECTOR, 'div > div.product-specification__wrapper > div.expert-table.c-label-description--orange > ul')
        data_phone = expert_recom.find_elements(By.XPATH, './/li')


        tech_data = []
        for i in data_phone:
            tech_data.append(i.text.strip())

        tech_details = {item.split("\n", 1)[0]: item.split("\n", 1)[1] for item in tech_data}
        tech_data.clear()
        
        spec_table = attributes_container.find_element(By.CSS_SELECTOR,'div > div.product-specification__wrapper > div.product-specification__table')
        data_phone = spec_table.find_elements(By.XPATH,'.//div[@class="group__specification"]')

        for j in data_phone:
            tech_data.append(j.text.strip())
            
        for item in tech_data: 
            text = item.split('\n') 
            for j in range(0, len(text) - 1, 2): 
                tech_details2[text[j]] = text[j + 1]  
        tech_details.update(tech_details2)
    except Exception as e:
            logger.error("Błąd przy otwieraniu URL {}: {}", url, e)
    return tech_details

tech_csv_filename = os.path.join(output_folder, f"tech_details_{shop_name}_{date}.csv")
fieldnames = ["product_link", "tech_details"]

with open(tech_csv_filename, mode="w", newline="", encoding="utf-8") as tech_csvfile:
    writer = csv.DictWriter(tech_csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for item in product_data:
        url = item["product_link"]
        logger.info("Processing: {}", url)
        details = scrape_tech_details(url)
        writer.writerow({
            "product_link": url,
            "tech_details": json.dumps(details, ensure_ascii=False)
        })

driver.quit()
logger.complete()
logger.info("The download of technical details has been completed. Data saved in file: {}", tech_csv_filename)