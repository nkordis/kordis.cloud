from selenium import webdriver
from selenium.webdriver.common.by import By
import re
import time
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox') # Bypass OS security model
    options.add_argument('--disable-dev-shm-usage') # Overcome limited resource problems

    service = Service(executable_path='/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def test_visitor_count_display():
    driver = setup_driver() 

    try:
        driver.get('http://kordis.cloud')
        time.sleep(10)  

        page_text = driver.find_element(By.TAG_NAME, "body").text
        # Search for "Visits: " followed by one or more digits
        match = re.search(r'Visits: (\d+)', page_text)
        if match:
            visitor_count = int(match.group(1))
            assert visitor_count > 0, "Visitor count is not greater than 0."
            print("Visitor Count:", visitor_count)
        else:
            raise ValueError("Failed to find 'Visits: ' followed by a number in the page.")

    finally:
        driver.quit()

if __name__ == "__main__":
    test_visitor_count_display()
