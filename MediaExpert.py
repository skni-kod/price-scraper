from loguru import logger
import csv
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from config import (driver, date, setup_logging)

# Settings of the shop
shop_name = "MediaExpert"

# Define CSV columns
fieldnames = ["date", "title", "product_link", "price", "image_url", "rating", "num_of_opinions"]

# Definition of file names
csv_filename = f"output/{shop_name}_{date}.csv"
log_filename = f"output/log_{shop_name}_{date}.log"


# Configuration of logger
logger = setup_logging(log_filename)
logger.info("Beggining of scrapping.")
logger.info("CSV file: {}", csv_filename)
logger.info("Log file: {}", log_filename)

with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    page = 1
    while True:
        # Set of URL: we'll use first page for basic address, another ones with have "p="
        if page == 1:
            url = "https://www.mediaexpert.pl/smartfony-i-zegarki/smartfony"
        else:
            url = f"https://www.mediaexpert.pl/smartfony-i-zegarki/smartfony?page={page}"
        logger.info("Scraping strony {}: {}", page, url)

        driver.get(url)

        try:
            # We're waiting for the goods to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.offer-box")))
        except Exception as e:
            logger.error("Error while awaiting for the goods: {}", e)
            break
        # time.sleep(1)

        products = driver.find_elements(By.CSS_SELECTOR, "div.offer-box")
        products_count = len(products)
        logger.info("Found {} products.", products_count)

        if not products:
            logger.info("No goods were found on this page, end of scrapping.")
            break


        def process_product(index, retries=3):
            for attempt in range(retries):
                try:
                    # Download current list of goods, to avoid operating on old references
                    products = driver.find_elements(By.CSS_SELECTOR, "div.offer-box")
                    product = products[index]

                    # Scroll to product's view - it forces load of lazy-loaded
                    driver.execute_script("arguments[0].scrollIntoView(true);", product)
                    time.sleep(1)

                    # Download product's name (if there are none - we probably have a wrong product)
                    product_name_elements = product.find_elements(By.CSS_SELECTOR, "h2.name a")
                    if not product_name_elements:
                        return None
                    product_name = product_name_elements[0].text.strip()

                    # Download of product's image URL
                    try:
                        image_link = product.find_element(By.CSS_SELECTOR, 'div.picture-image img.is-loaded')
                        image = image_link.get_attribute("src")
                    except:
                        logger.error("Couldn't download the image URL")
                        image = None

                    # Download opinions, thinking about half and full stars
                    try:
                        rating_element = product.find_element(By.CSS_SELECTOR, "div.product-rating")
                        # Full stars (eg. <i class="icon-star01 is-filled">)
                        full_stars = rating_element.find_elements(By.CSS_SELECTOR, "i.icon-star01.is-filled")
                        # Half-stars (eg. <svg class="is-half-filled">)
                        half_stars = rating_element.find_elements(By.CSS_SELECTOR, "svg.is-half-filled")
                        rating = len(full_stars) + 0.5 * len(half_stars)
                        # Download numer of opinions
                        reviews_elements = rating_element.find_elements(By.CSS_SELECTOR, "span.count-number")
                        reviews = reviews_elements[0].text.strip() if reviews_elements else "0"
                    except Exception:
                        rating = None
                        reviews = None
                        logger.info("No reviews for product '{}'", product_name)

                    try:
                        # Title and link download
                        link_element = product.find_element(By.CSS_SELECTOR, 'h2.name a.ui-link')
                        product_link = link_element.get_attribute("href")

                        # Download of price
                        try:
                            whole = product.find_element(By.XPATH, './/span[@class="whole"]').text.strip()
                            cents = product.find_element(By.XPATH, './/span[@class="cents"]').text.strip()
                            currency = product.find_element(By.XPATH, './/span[@class="currency"]').text.strip()
                            price_text = f"{whole}.{cents}{currency}"
                        except:
                            price_text = None
                            logger.info("No price was found for {}", product_name)
                        return image, product_name, rating, reviews, price_text, product_link
                    except:
                        logger.error("Issues with data scrapping")

                except StaleElementReferenceException:
                    if attempt < retries - 1:
                        # time.sleep(1)
                        continue  # Try again
                    else:
                        raise


        seen_products = set()

        for i in range(products_count):
            try:
                result = process_product(i)
                if result is None:
                    continue  # We skip element if it doesn't have any data
                image, product_name, rating, reviews, price_text, product_link = result

                # Checking for copies
                if product_name in seen_products:
                    logger.info("Product '{}' was already scrapped, skipping it's copy", product_name)
                    continue
                seen_products.add(product_name)

                # Deleting NNBSP (Unicode U+202F) from pridce
                price_text = price_text.replace("\u202F", "")

                # Saving to SCV file
                writer.writerow({
                    "date": date,
                    "title": product_name,
                    "price": price_text,
                    "rating": rating,
                    "num_of_opinions": reviews,
                    "product_link": product_link,
                    "image_url": image
                })
                logger.info("Scraped: {}", product_name)

            except Exception as e:
                logger.error("Error while scrapping product: {}", e)

        # Checking, if there another page's button is available
        try:
            number = driver.find_element(By.XPATH, '//div[@class="lastpage-button"]').text
            # print(number)
            if int(number) <= page:
                logger.info("Last page - end of scrapping.")
                break
        except Exception as e:
            logger.error("Error while checking for next page: {}", e)
            break

        page += 1

driver.quit()
logger.complete()
logger.info(f"End of scrapping. Collected data saved to file: {csv_filename}")