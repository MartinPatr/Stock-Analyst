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



# Updates the score of the ticker
def update_score(data):
    # Get the ticker symbol
    stock_symbol = data["Ticker"]
    url = f"https://www.marketwatch.com/investing/stock/{stock_symbol}/analystestimates?mod=mw_quote_tab"
    print(url)
    print("Ticker: " + stock_symbol)
    driver.get(url)
    get_analyst_estimates(data)
    
# Selenium test
def get_analyst_estimates(data):
 
    # Wait for the page to load
    time.sleep(1)
    try:
        # Close pop up window
        closeBtn = driver.find_element(By.CLASS_NAME, 'close-btn')
        closeBtn.click()
        time.sleep(1)
    except:
        pass

    # Get the html from the page
    html = driver.page_source
    #Use BeautifulSoup to parse the html
    soup = BeautifulSoup(html, 'html.parser')
    pe_ratio_element = soup.find_all('td', {'class': 'w25'})
    try:
        data['Recommendation'] = pe_ratio_element[0].text
        data['Target Price'] = pe_ratio_element[1].text
        
    except:
        data['Recommendation'] = False
        data['Target Price'] = False
        data['Score'] = 0

 

def close_driver():
    driver.close()

