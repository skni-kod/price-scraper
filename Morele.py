from config import(driver, date, setup_logging)
import re
import time
import csv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Define shop name and date settings
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

def get_image_url(product):
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", product)
        image_element = WebDriverWait(product, 7).until(
            EC.presence_of_element_located((By.XPATH, './/img[contains(@class, "product-image")]'))
        )
        image_url = image_element.get_attribute('src') 
        return image_url
        
    except Exception as e:
        logger.warning(f"No image: {str(e)}")
        return "No image"

with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    page = 1
    while True:
         # Determine URL: use base URL for the first page; subsequent pages include the ?p= parameter
        if page == 1:
            url = "https://www.morele.net/kategoria/smartfony-280/"
        else:
            url = f"https://www.morele.net/kategoria/smartfony-280/,,,,,,,,0,,,,/{page}/"
        print(f"Scraping strony {page}: {url}")

        driver.get(url)
        driver.execute_script("document.body.style.transform = 'scale(0.3)'")
        WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.XPATH, '//div[@class="cat-product card"]//img[contains(@class, "product-image")]')))
        time.sleep(2)
        products = driver.find_elements(By.XPATH,
                                        '//div[@class="cat-product card"]')

        if not products:
            logger.info("Brak produktów na stronie, kończę scraping.")
            break

       # Iterating through the products on the page
        for product in products:
            try:
                # Download title and product link
                image_url = get_image_url(product)
                link_element = product.find_element(By.XPATH, './/a[@class="productLink"]')
                title = link_element.get_attribute("title")
                product_link = link_element.get_attribute("href")

                try:
                    price_element = WebDriverWait(product, 1).until(
                        EC.presence_of_element_located((By.XPATH, './/div[@class="price-new"]'))
                    )
                    price = price_element.text.strip()
                    price = re.sub(r'[^\d,]', '', price)
                    price = price.replace(',', '.')
                    price = float(price)
                except:
                    price = 0
                    logger.info(f"No price detected for: {title}")

                try:
                    num_of_opinions = product.find_element(By.XPATH, './/span[@class="rating-count"]').text
                    match = re.search(r"\d+", num_of_opinions)
                    num_of_opinions = int(match.group()) if match else 0
                except:
                    num_of_opinions = 0
                    logger.info(f"No number of opinions detected for: {title}")

                try:
                    rating = product.find_element(By.XPATH,'.//input[@type="radio" and @checked="checked"]').get_attribute("value")
                except:
                    rating = 0
                    logger.info(f"No reviews for product: {title}")
                reviews = str(rating) + " " + str(num_of_opinions)
                # Saving to CSV file
                writer.writerow({
                    "date": date,
                    "title": title,
                    "product_link": product_link,
                    "price": price,
                    "image_url": image_url,
                    "reviews": reviews,
                })
                logger.info("Scraped: {}", title)
            
            except Exception as e:
                logger.error(f"Error processing product:: {str(e)}")
    
        # Sprawdzenie, czy przycisk „nawiguj do następnej strony” jest dostępny
        try:
            next_arrow = driver.find_elements(By.XPATH, '//a[@class="pagination-btn" and i[@class="icon-arrow-right"]]')

            if not next_arrow:
                logger.info("No 'next page' button found – ending scraping.")
                break
        except Exception as e:
            logger.error("Error checking for next page: {}", e)
            break

        page += 1

driver.quit()
logger.complete()
logger.info("Scraping completed. Data saved in file: {}",csv_filename)