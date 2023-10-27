from bs4 import BeautifulSoup
from datacollection import check_error
import requests


# Updates the score of the ticker
def update_score(data):
   
   # Making sure no negative scores are used
    if data['Score'] < 0:
        lower_bound = -50
        upper_bound = 0

        score_range = upper_bound - lower_bound
        adjusted_score = (data['Score'] - lower_bound) / score_range * 4 + 5
            
        data['Score'] = max(1, min(adjusted_score, 5))
   
    # Get the ticker symbol
    stock_symbol = data["Ticker"]
    url = f"https://www.marketwatch.com/investing/stock/{stock_symbol}/financials?mod=mw_quote_tab"
    return url

# Retrieve the financials from the page
def retrieve_financials(data):
    # Get the html from the page
    url = f"https://www.marketwatch.com/investing/stock/{data['Ticker']}/financials?mod=mw_quote_tab"
    html = requests.get(url)
    if html.status_code == 403:
        check_error(html)
        html = requests.get(url)
    
    soup = BeautifulSoup(html.text, 'html.parser')
    financial_elements = soup.find_all('tr', {'class': 'table__row'})

    # Attempt to
    try:
        # Get the position of the net income growth and eps growth
        for i, element in enumerate(financial_elements):
            element = element.find_all('td')
            try: 
                element = element[0].find_all('div')
                if element[1].text == "Net Income Growth":
                    niIndex = i
                if element[1].text == "EPS (Diluted) Growth":
                    epsIndex = i
            except:
                pass

        # Get the position of the profit margin, net income %, and eps %
        niPosition = len(financial_elements[niIndex].find_all('td')) - 2    
        epsPosition = len(financial_elements[epsIndex].find_all('td')) - 2

        data["Net Income %"] = financial_elements[niIndex].find_all('td')[niPosition].text.replace('%','').replace(',', '')
        data["EPS %"] = financial_elements[epsIndex].find_all('td')[epsPosition].text.replace('%','').replace(',', '')
        # If any of the values are NA, set the score to 0
        if data["Net Income %"] == "-" or data["EPS %"] == "-":
            print("Failed to update score as one of the values is NA")
            data['Score'] = 0
            return
        update_score_financials(data)
    except Exception as e:
        print("Failed to update score based on financials: ", e)
        data['Score'] = round(data['Score'] * 0.80,2)

#  Retrieves the analyst estimates from the analyst estimates page
def retrieve_analysis(data):
    # Get the html from the page
    url = f"https://www.marketwatch.com/investing/stock/{data['Ticker']}/analystestimates?mod=mw_quote_tab"
    html = requests.get(url)
    # If the page is not found, check the error and try again
    if html.status_code == 403:
        check_error(html)
        html = requests.get(url)

    # Use BeautifulSoup to parse the html
    soup = BeautifulSoup(html.text, 'html.parser')
    ae_elements = soup.find_all('td', {'class': 'w25'})
    try:
        data['Recommendation'] = ae_elements[0].text
        data['Target Price'] = ae_elements[1].text
        update_score_analysis(data)
    except Exception as e:
        print("Failed to update score based on analyst estimates: ", e)
        data['Score'] = round(data['Score'] * 0.80,2)

# Updates the score of the ticker based on the information that we found on the financials page
def update_score_financials(data):

    # Update the score based on the net income %
    net_income = float(data["Net Income %"])
    data['Score'] = round(data["Score"] * (get_multiplier(net_income,300)),2)

    # Update the score based on the EPS
    eps = float(data["EPS %"])
    data['Score'] = round(data["Score"] * (get_multiplier(eps,300)),2)

# Updates the score of the ticker based on the information that we found on the analysis page
def update_score_analysis(data):    
    # Update the score based on the target price
    current_price = float(data['Price'])
    target_price = float(data['Target Price'])

    price_difference = target_price - current_price
    price_total = target_price + current_price
    price_difference_percentage = (price_difference/(price_total/2))/2
    data["Score"] = round(data["Score"] * (1 + (price_difference_percentage/2.5)) ,2)

    # Update the score based on the expert recommendation
    if data['Recommendation'] == 'Buy':
        data['Score'] = round(data["Score"] * 1.18,2)
    elif data['Recommendation'] == 'Overweight':
        data['Score'] = round(data["Score"] * 1.08,2)
    elif data['Recommendation'] == 'Hold':
        pass
    elif data['Recommendation'] == 'Underweight':
        data['Score'] = round(data["Score"] * 0.90,2)
    elif data['Recommendation'] == 'Sell':
        data['Score'] = round(data["Score"] * 0.80,2)
    else:
        print("No recommendation found")
        data["Score"] = 0

# Gets multiplier based on the value and weight
def get_multiplier(value, weight):
    if 1 + value/weight < 0:
        return 0.10
    else:
        return 1 + value/weight