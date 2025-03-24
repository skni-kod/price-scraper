import os
import platform
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from loguru import logger

os.makedirs("output", exist_ok=True)

# Date format
date = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")

# Firefox and Geckodriver configuration
options = webdriver.FirefoxOptions()
options.add_argument("--headless")

# TODO: Replace with docker later
# Operating system detection
system_os = platform.system()
if system_os == "Windows":
    firefox_binary_path = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
    options.binary_location = firefox_binary_path
    service = Service("geckodriver.exe")
else:
    service = Service("/usr/local/bin/geckodriver")

driver = webdriver.Firefox(service=service, options=options)

def setup_logging(log_filename):
    logger.remove()  # Deleting default handlers
    log_format = "{time:YYYY-MM-DD HH:mm:ss,SSS} - {level} - {message}"
    logger.add(log_filename, level="INFO", format=log_format, encoding="utf-8")
    logger.add(lambda msg: print(msg, end=""), level="INFO", format=log_format)
    return logger
