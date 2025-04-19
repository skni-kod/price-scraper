import csv
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import driver, date, setup_logging

# Shop name and file paths
shop_name = "neonet"
csv_filename = f"output/{shop_name}_{date}.csv"
log_filename = f"output/log_{shop_name}_{date}.log"

# Initialize logger
logger = setup_logging(log_filename)
logger.info("Starting scraping.")
logger.info("CSV File: {}", csv_filename)
logger.info("Log File: {}", log_filename)

# Open CSV for writing
with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
    fieldnames = ["date", "title", "product_link", "price", "image_url", "reviews"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    base_url = "https://www.neonet.pl/smartfony-i-navi/smartfony.html"

    # Get max pages from pagination control
    driver.get(base_url)
    try:
        pagination_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "section.listingPaginationScss-paginationSection-1VV input[type='number']")
            )
        )
        max_page = int(pagination_input.get_attribute("max"))
        logger.info("Max number of pages: {}", max_page)
    except Exception as e:
        logger.error("Failed to retrieve max pages: {}", e)
        max_page = 1

    page = 1
    while page <= max_page:
        url = base_url if page == 1 else f"{base_url}?p={page}"
        logger.info("Scraping page {}: {}", page, url)
        driver.get(url)

        # Wait for at least one product to appear
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "section[data-neonet-product-id]"))
            )
        except Exception as e:
            logger.error("Products did not load on page {}: {}", page, e)

        # Fast scrolling to load additional products
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
            logger.error("Error sending END/HOME keys: {}", e)

        # Wait for at least 20 products or proceed with what’s available
        try:
            WebDriverWait(driver, 5).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "section[data-neonet-product-id]")) >= 20
            )
        except Exception:
            logger.info("Could not load full number of products, proceeding with available ones.")

        products = driver.find_elements(By.CSS_SELECTOR, "section[data-neonet-product-id]")
        if not products:
            logger.info("No products on page {}, continuing.", page)
            page += 1
            continue

        # Iterate over products and extract data
        for product in products:
            try:
                title_el = product.find_element(By.XPATH, './/h2[contains(@class, "listingItemHeaderScss-name")]')
                title = title_el.text.strip()
                link_el = title_el.find_element(By.XPATH, "./ancestor::a")
                product_link = link_el.get_attribute("href").strip()

                price_el = product.find_element(By.XPATH, './/span[@data-marker="UIPriceSimple"]')
                price = price_el.text.strip()

                try:
                    img_el = product.find_element(By.XPATH, './/img')
                    image_url = img_el.get_attribute("src").strip()
                except Exception:
                    image_url = ""
                    logger.info("No image for '{}'.", title)

                try:
                    review_section = product.find_element(By.CSS_SELECTOR, "section.ratingStarsScss-wrapper-1mq")
                    rating_span = review_section.find_element(By.CSS_SELECTOR, "span.ratingStarsScss-rating-3xe")
                    style = rating_span.get_attribute("style")  # e.g. "width: 80%;"
                    pct = style.split("width:")[1].split("%")[0].strip()
                    rating_value = round(float(pct) / 20, 1)
                    count_span = review_section.find_element(By.CSS_SELECTOR, "span.ratingStarsScss-count-1T-")
                    count_text = count_span.text.strip().strip("()")
                    reviews = f"{rating_value}/5 ({count_text} reviews)"
                except Exception:
                    reviews = ""
                    logger.info("No reviews for '{}'.", title)

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

        page += 1

# Quit the driver and finish logging
from config import driver as _driver
_driver.quit()
logger.info("Scraping completed. Data saved in {}", csv_filename)
logger.complete()