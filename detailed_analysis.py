from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import time
import requests



# Set up the driver
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
driver = webdriver.Chrome(options=options)


# Selenium test
def selenium_test(data, soup):
    link_element = soup.find('a', attrs={'instrument-target': 'analystestimates'})
    print(link_element)

    # Close pop up
    
    time.sleep(1)
    try:
        closeBtn = driver.find_element(By.CLASS_NAME, 'close-btn')
        closeBtn.click()
        time.sleep(1)
    except:
        pass

    # Click on the analyst estimates tab
    time.sleep(2)
    try:
        checkbox = driver.find_element(By.XPATH,"//a[text()='Analyst Estimates']")
        checkbox.click()
        time.sleep(1)
        # Get the html from the page
        html = driver.page_source
        #Use BeautifulSoup to parse the html
        soup = BeautifulSoup(html, 'html.parser')
        pe_ratio_element = soup.find_all('td', {'class': 'w25'})

        data['Recommendation'] = pe_ratio_element[0].text
        data['Target Price'] = pe_ratio_element[1].text
    except:
        pass
