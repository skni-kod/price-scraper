import csv

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from config import (driver, date, setup_logging)

# Define shop name and date settings
shop_name = "rtv_euro_agd"

# Define CSV columns (change order later)
fieldnames = ["date","title", "product_link", "price", "rating", "num_of_opinions"]
# Define CSV filenames
csv_filename = f"output/{shop_name}_{date}.csv"
log_filename = f"output/log_{shop_name}_{date}.log"

# Setup logger
logger = setup_logging(log_filename)
logger.info("Starting scraping.")
logger.info("CSV File: {}", csv_filename)
logger.info("Log File: {}", log_filename)

try:
    with open(csv_filename , mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        page = 1
        while True: 
            # Determine URL: use base URL for the first page; subsequent pages include the ,strona- parameter
            if page == 1:
                url = "https://www.euro.com.pl/telefony-komorkowe.bhtml"
            else:
                url = f"https://www.euro.com.pl/telefony-komorkowe,strona-{page}.bhtml"
            logger.info(f"Scraping page {page}: {url}")

            driver.get(url)

            #Waiting for the products to load
            try:
                WebDriverWait(driver, 10).until(
                EC.visibility_of_all_elements_located((By.CLASS_NAME, "product-medium-box"))
            )
            except TimeoutException:
                logger.warning("Element 'product-medium-box' did not appear")
            

            # Retrieve all products on page
            products = driver.find_elements(By.XPATH,
                                            '//div[@class="product-medium-box"]')    
            if not products:
                logger.info("No products found on the page, ending scraping.")
                break

            # Iterate over the products on the page
            for product in products:
                try:
                    # Retrieve product title and link
                    link_element = product.find_element(By.XPATH, './/a[@class="product-medium-box-intro__link"]')
                    title = link_element.text
                    product_link = link_element.get_attribute("href")

                    # Retrieve product price
                    parted_price_total = product.find_element(By.XPATH, './/span[@class="parted-price-total"]')
                    parted_price_decimal = product.find_element(By.XPATH, './/span[@class="parted-price-decimal"]')
                    price_total_text = f"{parted_price_total.text.strip()},{parted_price_decimal.text.strip()}"

                    # Retrieve product rating
                    try:
                        rating = "{}/5".format(product.find_element(By.XPATH, './/span[@class="client-rate__rate"]').text)
                        num_of_opinions = product.find_element(By.XPATH, './/span[@class="client-rate__opinions"]').text.split()[0]
                    except Exception as e:
                            logger.info("No reviews for product '{}'.", title)
                            rating = ""
                            num_of_opinions = ""

                    writer.writerow({
                        "date": date,
                        "title": title,
                        "product_link": product_link,
                        "price": price_total_text,
                        "rating": rating,
                        "num_of_opinions": num_of_opinions,
                    })
                    logger.info(f"Scraped: {title}")
                    
                except Exception as e:
                    logger.error("Error processing product: {}", e)

            # Check if the "Załaduj więcej" button is available
            try:
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//a[@data-aut-id="show-more-products-button"]'))
                )
                page += 1
            except TimeoutException:
                logger.info("No 'Załaduj więcej' button found – ending scraping.")
                break
finally:
    driver.quit()
    logger.complete()
    logger.info(f"Scraping completed. Data saved in file: {csv_filename }")