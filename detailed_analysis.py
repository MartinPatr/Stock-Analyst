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
        update_score_analysis(data)
    except:
        data['Recommendation'] = False
        data['Target Price'] = False
        data['Score'] = 0

# Updates the score of the ticker based on the information that we found on the analysis page
def update_score_analysis(data):
    # Update the score based on the expert recommendation
    if data['Recommendation'] == 'Buy':
        data['Score'] = round(data["Score"] * 1.33,2)
    elif data['Recommendation'] == 'Overweight':
        data['Score'] = round(data["Score"] * 1.15,2)
    elif data['Recommendation'] == 'Hold':
        pass
    elif data['Recommendation'] == 'Underweight':
        data['Score'] = round(data["Score"] * 0.85,2)
    elif data['Recommendation'] == 'Sell':
        data['Score'] = round(data["Score"] * 0.67,2)
    else:
        data["Score"] = 0
    
    # Update the score based on the target price
    current_price = float(data['Price'])
    target_price = float(data['Target Price'])

    price_difference = target_price - current_price
    price_total = target_price + current_price
    price_difference_percentage = (price_difference/(price_total/2))/2
    data["Score"] = round(data["Score"] * (1 + price_difference_percentage),2)

# Close the driver
def close_driver():
    driver.close()

