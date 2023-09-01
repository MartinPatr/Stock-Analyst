from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datacollection import check_error

# Set up the driver
options = Options()
options.add_argument('--disable-browser-side-navigation')
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('window-size=1920x1080')
options.add_argument("--disable-extensions")
driver = webdriver.Chrome(options=options)
ChromeOptions = webdriver.ChromeOptions()


# Updates the score of the ticker
def update_score(data):
   
   # Making sure no negative scores are used
    if data['Score'] < 0:
        lower_bound = -10
        upper_bound = 0

        score_range = upper_bound - lower_bound
        adjusted_score = (data['Score'] - lower_bound) / score_range * 4 + 5
            
        data['Score'] = max(1, min(adjusted_score, 5))
   
    # Get the ticker symbol
    stock_symbol = data["Ticker"]
    url = f"https://www.marketwatch.com/investing/stock/{stock_symbol}/financials?mod=mw_quote_tab"
    print(url)
    print("Ticker: " + stock_symbol)
    driver.get(url)
    get_financials(data)
    get_analyst_estimates(data)



# Gets the financials from the financials page
def get_financials(data):    
    
    # Wait for the page to load and close the popup
    close_popup()

    # Get the html from the page
    html = driver.page_source
    # Check if the page has loaded successfully
    if "403 Forbidden" in html:
        check_error(html)

    soup = BeautifulSoup(html, 'html.parser')
    financial_elements = soup.find_all('tr', {'class': 'table__row'})

    # Attempt to
    try:
        # Get the position of the profit margin, net income %, and eps %
        niPosition = len(financial_elements[50].find_all('td')) - 2
        epsPosition = len(financial_elements[63].find_all('td')) - 2


        data["Net Income %"] = financial_elements[50].find_all('td')[niPosition].text.replace('%','').replace(',', '')
        data["EPS %"] = financial_elements[63].find_all('td')[epsPosition].text.replace('%','').replace(',', '')
        # If any of the values are NA, set the score to 0
        if data["Net Income %"] == "-" or data["EPS %"] == "-":
            data['Score'] = 0
            return
        update_score_financials(data)
    except Exception as e:
        print("Failed to update score based on financials: ", e)
        data['Score'] = 0

# Updates the score of the ticker based on the information that we found on the financials page
def update_score_financials(data):

    # Update the score based on the net income %
    net_income = float(data["Net Income %"])
    data['Score'] = round(data["Score"] * (get_multiplier(net_income,300)),2)

    # Update the score based on the EPS
    eps = float(data["EPS %"])
    data['Score'] = round(data["Score"] * (get_multiplier(eps,300)),2)



# Gets the analyst estimates from the analyst estimates page
def get_analyst_estimates(data):
    # Go to the analyst estimates page
    try:
        button = driver.find_element(By.XPATH,"//a[text()='Analyst Estimates']")
        button.click()
    except:
        print("Stock is closed")
        data['Score'] = 0
        return
   
    # Wait for the page to load and close the popup
    close_popup()
    
    # Get the html from the page
    html = driver.page_source
    #Use BeautifulSoup to parse the html
    soup = BeautifulSoup(html, 'html.parser')
    ae_elements = soup.find_all('td', {'class': 'w25'})
    try:
        data['Recommendation'] = ae_elements[0].text
        data['Target Price'] = ae_elements[1].text
        update_score_analysis(data)
    except Exception as e:
        print("Failed to update score based on analyst estimates: ", e)
        data['Score'] = 0

# Updates the score of the ticker based on the information that we found on the analysis page
def update_score_analysis(data):    
    # Update the score based on the target price
    current_price = float(data['Price'])
    target_price = float(data['Target Price'])

    price_difference = target_price - current_price
    price_total = target_price + current_price
    price_difference_percentage = (price_difference/(price_total/2))/2
    data["Score"] = round(data["Score"] * (1 + (price_difference_percentage/1.5)) ,2)

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
        print("No recommendation found")
        data["Score"] = 0

# Gets multiplier based on the value and weight
def get_multiplier(value, weight):
    if 1 + value/weight < 0:
        return 0.10
    else:
        return 1 + value/weight

# Close the popup window
def close_popup():
    # Wait to see if the popup appears
    try:
        button = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.CLASS_NAME, 'close-btn')))
        button.click()
    except:
        pass



# Close the driver
def close_driver():
    driver.close()


# data = {
#     'Ticker': 'ACDC',
#     'Price': '11.56',
#     'Industry': '',
#     'Sector': '',
#     'Description': '',
#     'Market Cap': '',
#     'P/E': '',
#     'P/S': '',
#     'P/B': '',
#     'EV/Sales': '',
#     'Current Ratio': '',
#     "Cash Ratio": "",
#     'Gross Margin': '',
#     'Debt to Equity': '',
#     '% of Insider Purchasing': '',
#     'Score': 67,
#     }
# update_score(data)
# print(data)