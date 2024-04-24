from selenium import webdriver
from selenium.webdriver.common.by import By
import re  # For regex operations
import time  # For adding delay

def test_visitor_count_display():
    driver = webdriver.Chrome()  

    try:
        driver.get('http://kordis.cloud')
        time.sleep(2)  

        page_text = driver.find_element(By.TAG_NAME, "body").text
        visitor_count = int(re.search(r'Visits: (\d+)', page_text).group(1))
        
        print("Visitor Count:", visitor_count)
        assert visitor_count > 0, "Visitor count is not greater than 0."

    finally:
        driver.quit()

if __name__ == "__main__":
    test_visitor_count_display()
