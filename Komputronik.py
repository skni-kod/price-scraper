import csv
from selenium.webdriver.common.by import By
from config import (driver, date, setup_logging)

# Define shop name and date settings
shop_name = "komputronik"

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

with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    page = 1
    while True:
        # Determine URL: use base URL for the first page; subsequent pages include the ?p= parameter
        if page == 1:
            url = "https://www.komputronik.pl/category/1596/telefony.html"
        else:
            url = f"https://www.komputronik.pl/category/1596/telefony.html?p={page}"
        logger.info("Scraping page {}: {}", page, url)

        driver.get(url)
        products = driver.find_elements(By.XPATH, '//div[@data-name="listingTile"]')
        if not products:
            logger.info("No products found on the page, ending scraping.")
            break

        # Iterate over the products on the page
        for product in products:
            try:
                # Retrieve product title and link
                link_element = product.find_element(By.XPATH, './/a[@title]')
                title = link_element.get_attribute("title")
                product_link = link_element.get_attribute("href")

                # Retrieve product price
                price_element = product.find_element(By.XPATH, './/div[@data-name="listingPrice"]//div[@data-price-type="final"]')
                price = price_element.text.strip()

                # Retrieve product image URL
                img_element = product.find_element(By.XPATH, './/img')
                image_url = img_element.get_attribute("src")

                # Retrieve reviews (combining rating and number of opinions)
                try:
                    review_element = product.find_element(By.XPATH, './/p[contains(@class, "text-base") and contains(@class, "leading-none")]')
                    rating = review_element.find_element(By.XPATH, './/span[contains(@class, "font-bold")]').text.strip()
                    opinions = review_element.find_element(By.XPATH, './/span[not(contains(@class, "font-bold"))]').text.strip()
                    reviews = f"{rating} {opinions}"
                except Exception as e:
                    reviews = ""
                    logger.info("No reviews for product '{}'.", title)

                # Write product data to CSV
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
                logger.error("Error processing product: {}", e)

        # Check if the "next page" button is available
        try:
            next_arrow = driver.find_elements(By.XPATH, '//a[@aria-label="nawiguj do następnej strony"]')
            if not next_arrow:
                logger.info("No 'next page' button found – ending scraping.")
                break
        except Exception as e:
            logger.error("Error checking for next page: {}", e)
            break

        page += 1

# Close the browser
driver.quit()
logger.complete()
logger.info("Scraping completed. Data saved in file: {}", csv_filename)
