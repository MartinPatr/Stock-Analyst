from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import time

# Set up the Firefox WebDriver with desired options
firefox_driver_path = '/Users/martinpatrouchev/Downloads/geckodriver'

firefox_options = Options()
firefox_options.headless = True

driver = webdriver.Firefox(executable_path=firefox_driver_path, firefox_options=firefox_options)




def get_frontpage_url(stock_symbol):
    url = f"https://www.marketwatch.com/investing/stock/{stock_symbol}/company-profile?mod=mw_quote_tab"
    print(url)
    print("Ticker: " + stock_symbol)
    driver.get(url)


def get_data(stock_symbol):
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
        'Score': '',
        'Recommendation': '',
        'Target Price': '',
    }

    # Get the html from the page
    html = driver.page_source

    #Use BeautifulSoup to parse the html
    soup = BeautifulSoup(html.content, 'html.parser')
    
    # Finding main page stats
    pe_ratio_element = soup.find_all('td', {'class': 'w25'})
    pe_description_element = soup.find('p', {'class': 'description__text'})
    pe_value_element = soup.find_all('bg-quote', {'class': 'value'})
    pe_sector_element = soup.find_all('span', {'class': 'primary'})
    pe_na_element = soup.find_all('td',{'class':'is-na'})
    print(pe_ratio_element)
    if len(pe_na_element) > 8:
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

    # Finding analyst recommendation
    button = driver.find_element_by_xpath("//button[@instrument-target='analystestimates']")
    button.click()
    time.sleep(1.5)

    # Get the html from the page
    html = driver.page_source
    #Use BeautifulSoup to parse the html
    soup = BeautifulSoup(html.content, 'html.parser')
    pe_ratio_element = soup.find_all('td', {'class': 'w25'})

    data['Recommendation'] = pe_ratio_element[0].text
    data['Target Price'] = pe_ratio_element[1].text



def calculate_data(numStocks):
    stocks = []
    with open('validtickers.txt', 'r') as file:
        for i, line in enumerate(file):
            tickerList = line.strip().split()
            ticker = str(tickerList[0])
        
            get_frontpage_url(ticker)
            data = get_data(html, ticker)
            if data == False:
                pass
            else:
                calculate_score(data)
                stocks.append(data)
            if i == numStocks:  
                break
       
        driver.quit()
        # Sort the stocks based on the score in descending order
        sorted_stocks = sorted(stocks, key=lambda x: x['Score'], reverse=True)
    
        # Print out the companies with the highest scores
        i = 0
        for stock in sorted_stocks:
            if i == 10:
                break
        
            print()
            print("--------------------------------------------------")
            print(f"Company: {stock['Ticker']}, Score: {stock['Score']}, Industry: {stock['Industry']}, Sector: {stock['Sector']}")           
            print(f"Description: {stock['Description']}") 

    

def calculate_score(data):
    score = 0
    if data['P/E'] != "N/A" and float(data['P/E'].replace(",", "")) < 20:
        score += 1
    else:
        score -= 1
    if data['P/S'] != "N/A" and float(data['P/S'].replace(",", "")) < 2:
        score += 1
    else:
        score -= 1
    if data['P/B'] != "N/A" and float(data['P/B'].replace(",", "")) < 2:
        score += 1
    else:
        score -= 1
    if data['Current Ratio'] != "N/A" and float(data['Current Ratio'].replace(",", "")) > 1.5:
        score += 1
    else:
        score -= 1
    if data['Debt to Equity'] != "N/A" and float(data['Debt to Equity'].replace(",", "")) < 1:
        score += 1
    else:
        score -= 1
    data['Score'] = score




soup = get_frontpage_url("AAPL")
print(get_data("AAPL"))
