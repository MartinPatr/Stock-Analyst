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
#driver = webdriver.Chrome(options=options)


def get_frontpage_url(stock_symbol):
    url = f"https://www.marketwatch.com/investing/stock/{stock_symbol}/company-profile?mod=mw_quote_tab"
    print()
    print(url)
    print("Ticker: " + stock_symbol)
    html = requests.get(url)
    if html.status_code == 200:
        return html
    else:
        print("Unable to retrieve front page statistics")
        return False

def get_data(html,stock_symbol):
    if html is False:
        return html

    # Create a dictionary to store the data
    data = {
        'Ticker': '',
        'Price': '',
        'Industry': '',
        'Sector': '',
        'Description': '',
        'Market Cap': '',
        'P/E': '',
        'P/S': '',
        'P/B': '',
        'EV/Sales': '',
        'Current Ratio': '',
        "Cash Ratio": "",
        'Gross Margin': '',
        'Debt to Equity': '',
        '% of Insider Purchasing': '',
        'Score': '',
    }

    #Use BeautifulSoup to parse the html
    soup = BeautifulSoup(html.text, 'html.parser')
    
    # Finding main page stats
    pe_ratio_element = soup.find_all('td', {'class': 'w25'})
    pe_description_element = soup.find('p', {'class': 'description__text'})
    pe_value_element = soup.find_all('bg-quote', {'class': 'value'})
    pe_sector_element = soup.find_all('span', {'class': 'primary'})
    pe_na_element = soup.find_all('td',{'class':'is-na'})
    if len(pe_na_element) > 13:
        print("Not enough information")
        return False
    elif len(pe_ratio_element) == 29:
        data['Ticker'] = stock_symbol
        data['Price'] = pe_value_element[0].text
        data['Industry'] = pe_sector_element[6].text
        data['Sector'] = pe_sector_element[7].text
        data['Description'] = pe_description_element.text
        data['Market Cap'] = pe_ratio_element[8].text
        data['P/E'] = pe_ratio_element[0].text
        data['P/S'] = pe_ratio_element[3].text
        data['P/B'] = pe_ratio_element[4].text
        data['EV/Sales'] = pe_ratio_element[7].text
        data['Current Ratio'] = pe_ratio_element[13].text
        data['Cash Ratio'] = pe_ratio_element[15].text
        data['Gross Margin'] = pe_ratio_element[16].text
        data['Debt to Equity'] = pe_ratio_element[24].text
    else:
        print("Unable to retrieve main page statistics")
        return False


    # Finding insider trading stats
    try:
        purchasingElements = soup.find_all('span', {'class': 'secondary purchase'})
        sellingElements = soup.find_all('span', {'class': 'secondary sale'})
        amountBuying = len(purchasingElements)
        amountSelling = len(sellingElements)
        data['% of Insider Purchasing'] = round(((amountBuying/(amountBuying + amountSelling))*100))
    except:
        pass
    
    return data
            
def calculate_score(data):
    score = 0
    if data['P/E'] and float(data['P/E'].replace(",", "")) < 20:
        score += 1
    else:
        score -= 1
    if data['P/S'] and float(data['P/S'].replace(",", "")) < 2:
        score += 1
    else:
        score -= 1
    if data['P/B'] and float(data['P/B'].replace(",", "")) < 2:
        score += 1
    else:
        score -= 1
    if data['Current Ratio'] and float(data['Current Ratio'].replace(",", "")) > 1.5:
        score += 1
    else:
        score -= 1
    if data['Cash Ratio'] and float(data['Cash Ratio'].replace(",", "")) < 10:
        score += 1
    else:
        score -= 1
    if data['Gross Margin'] and float(data['Gross Margin'].replace(",", "")) > 40:
        score += 1
    else:
        score -= 1
    if data['Debt to Equity']  and float(data['Debt to Equity'].replace(",", "")) > 1:
        score += 1
    else:
        score -= 1    
    if data['% of Insider Purchasing'] and float(data['% of Insider Purchasing']) > 50:
        score += 1
    else:
        score -= 1

    data['Score'] = score



calculate_data(100)




# Selenium test
def selenium_test():
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

