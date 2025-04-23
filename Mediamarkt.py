from config import(create_driver, date, setup_logging)
import csv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json

# Define shop name
shop_name = "mediamarkt"

# Define CSV columns
fieldnames = ["date","title", "product_link", "price", "image_url", "reviews"]
# Define CSV filenames
csv_filename = f"output/{shop_name}_{date}.csv"
log_filename = f"output/log_{shop_name}_{date}.log"

# Setup logger
logger = setup_logging(log_filename)
logger.info("Starting scraping.")
logger.info("CSV File: {}", csv_filename)
logger.info("Log File: {}", log_filename)

# Opening the CSV file for writing
with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    page = 1
    while True:
        driver = create_driver()
        
        url = f"https://mediamarkt.pl/pl/category/smartfony-25983.html?page={page}"
        logger.info(f"Processing page: {url}")

        driver.get(url)
        driver.execute_script("document.body.style.transform = 'scale(0.3)'")
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.XPATH, '//div[@data-test="mms-product-card"]')))
          
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            json_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_scripts:
                try:
                    json_data = json.loads(script.string)
                    
                    if json_data.get('@type') == 'ItemList':
                        for item in json_data.get('itemListElement', []):
                            product = item.get('item', {})
                            
                            # Reading the data
                            title = product.get('name').replace("Smartfon ", "")
                            price = product.get('offers', {}).get('price')
                            rating_value = product.get('aggregateRating', {}).get('ratingValue')
                            opinion_count = product.get('aggregateRating', {}).get('reviewCount')
                            image_url = product.get('image')
                            reviews = str(rating_value) + "/" + str(opinion_count)
                            product_link = product.get('url')
                            
                            writer.writerow({
                            "date": date,
                            "title": title,
                            "product_link": product_link,
                            "price": price,
                            "image_url": image_url,
                            "reviews": reviews,
                        })
                            logger.info(f"Saved product: {title}")
                            
                except json.JSONDecodeError as e:
                    logger.error(f"Error while parsing JSON: {e}")
                    continue
                
            page += 1
            driver.quit()
            button = soup.find('button', {'data-test': 'mms-search-srp-loadmore'})
            if button == None:
                logger.info("No more pages to scrape")
                break
        except Exception as e:
            logger.error(f"Error during page processing {page}: {e}")
            driver.quit()
            break

# Close the browser when finished
logger.info("Terminating script.")