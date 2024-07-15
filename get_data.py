import re
from urllib.request import urlopen
import certifi
import json
import requests
from bs4 import BeautifulSoup


# Main function to get data
def get_recommendation_data(stock_info , session):
    # Create a dictionary to store the data
    # Start webscraping and get recommendation data
    with open("data/urls.json", 'r') as file:
        urls_data = json.load(file)
        for item in urls_data:
            get_html_recommendation_data(stock_info, session, item)

    return stock_info

# Getting API Data
def get_api_data(stock_info, current_call=0):
    print("Getting api data for " + stock_info["Ticker"] + "...")
    try:
        ticker = stock_info["Ticker"]
        # Getting company profile information
        # url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={get_api_key()}"
        # company_profile_data = get_jsonparsed_api_data(url)
        # stock_info['Company Name'] = company_profile_data["companyName"]
        # stock_info['Price'] = company_profile_data["price"]
        # stock_info['Volume'] = company_profile_data["volAvg"]
        # stock_info['Market Cap'] = company_profile_data["mktCap"]
        # stock_info['Industry'] = company_profile_data["industry"]
        # stock_info['Sector'] = company_profile_data["sector"]

        # Getting company metrics information
        url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?period=annual&apikey={get_api_key()}"
        company_metrics_data = get_jsonparsed_api_data(url)
        stock_info['P/E'] = company_metrics_data["peRatio"]
        stock_info['P/S'] = company_metrics_data["priceToSalesRatio"]
        stock_info['P/B'] = company_metrics_data["pbRatio"]
        stock_info['EV/Sales'] = company_metrics_data["evToSales"]
        stock_info['Current Ratio'] = company_metrics_data["currentRatio"]
        stock_info['Debt to Equity'] = company_metrics_data["debtToEquity"]
    except Exception as e:
        if hasattr(e, 'code') and e.code == 429:
            update_api_key()
            return "Fail - New"
        else:
            print(e)
            print("Error with getting data from API for " + stock_info["Ticker"])
            return False

    if current_call == 125:
        update_api_key()
        return "Success - New"
    
    return True
        
# Get the json parsed data from the API
def get_jsonparsed_api_data(url):
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    return json.loads(data)[0]

# Get the API key
def get_api_key():
    with open('creds/api_keys.json', 'r') as file:
        data = json.load(file)

    index = data.get('current_index', 0)
    keys = data.get('api_keys', [])
    
    return keys[index]

# Update the API key
def update_api_key():
    json_file_path = 'creds/api_keys.json'
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    
    # Get the current index and API keys
    current_index = data.get('current_index', 0)
    api_keys = data.get('api_keys', [])
    new_index = (current_index + 1) % len(api_keys)
    data['current_index'] = new_index
    
    # Write the updated data back to the JSON file
    with open(json_file_path, 'w') as file:
        json.dump(data, file, indent=4)

# Start a session
def start_session():
    # Initialize a session
    session = requests.Session()

    # Set a User-Agent header to make the request look like it is coming from a browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    })

    return session

# End the session
def end_session(session):
    session.close()

# Getting recommendation data based on json file urls
def get_html_recommendation_data(stock_info, session, json_url_data):
    ticker = stock_info["Ticker"].lower() if json_url_data["is_ticker_lower"] else stock_info["Ticker"]
    url = json_url_data["url"]
    html = get_frontpage_url(session, ticker, url)
    if html is not None:
        try:
            soup = BeautifulSoup(html.text, 'html.parser')
            
            # From BarChart
            if json_url_data["element_name"] == 'specific' and "BarChart" in json_url_data["name"]:
                rating_elements = soup.find_all(json_url_data["element_type"], class_=re.compile(r'block__colored-header.*'))
                rating_element = rating_elements[-1].get_text(strip=True)

                rating_values = soup.find_all('div', class_='block__average_value')
                block__average_value = rating_values[-1].get_text(strip=True)

                target_element = rating_element + " - " + block__average_value + "/5"

            # From TheGlobeandMail - NOT USED RIGHT NOW
            elif json_url_data["element_name"] == 'specific' and "TheGlobeandMail" in json_url_data["name"]:
                rating_values = soup.find_all(json_url_data["element_type"], style=re.compile(r'height:.*'))
                rating_value = rating_values[3].get_text(strip=True)

                if float(rating_value) > 4.5: 
                    target_element = "Strong Buy"
                elif float(rating_value) > 4:
                    target_element = "Moderate Buy"
                elif float(rating_value) > 3:
                    target_element = "Hold"
                elif float(rating_value) > 2:
                    target_element = "Moderate Sell"
                else:
                    target_element = "Strong Sell"

                target_element = target_element + " - " + rating_value + "/5"

            # From Benzinga
            elif json_url_data["element_name"] == 'specific' and "Benzinga" in json_url_data["name"]:
                target_element = soup.find('span', class_='analyst-rating-label')  

                rating_value = soup.find('div', class_='analyst-rating-score-circle')

                target_element = target_element.get_text(strip=True) + " - " + rating_value.get_text(strip=True) + "/5"
           
            # From Zacks
            elif "Zacks" in json_url_data["name"]:
                target_element = soup.find(json_url_data["element_type"], class_=json_url_data["element_name"])
                target_element = target_element.get_text(strip=True)
                match = re.search(r'-(.*?)of', target_element)

                rating_value = abs(int(target_element[0]) - 6)

                target_element = match.group(1).strip() + " - " + str(rating_value) + "/5"
            
            # From MarketBeat
            elif "MarketBeat" in json_url_data["name"]:
                target_element = soup.find(json_url_data["element_type"], class_=json_url_data["element_name"])
                target_element = target_element.get_text(strip=True)

                rating_value = soup.find('div', class_='key-stat-details')
                rating_value = rating_value.get_text(strip=True)

                target_element = target_element + " - " + rating_value[0] + "/3"
            
            else:
                target_element = soup.find(json_url_data["element_type"], class_=json_url_data["element_name"])
                target_element = target_element.get_text(strip=True)

            stock_info[json_url_data["name"]] = target_element
            print("Data from " + json_url_data["name"] + " for " + ticker + " is: " + stock_info[json_url_data["name"]])

        except Exception as e:
            print(e)
            print("Error with fetching data from " + json_url_data["name"] + " for " + ticker)
    print()

# Get the page html
def get_frontpage_url(session, ticker, url):
    url = url.format(ticker=ticker)
    print("Attempting to get data from: " + url + "...")
    html = session.get(url)  # Use session to make the request
    if html.status_code == 200:
        return html
    else:
        print("Error with request html: " + url + " Status Code:" +  str(html.status_code))
        
if __name__ == "__main__":
    update_api_key()
    # session = start_session()
    # data = get_recommendation_data("ENVX", session)
    # print("BarChart = " + data["BarChart Recommendation"])
    # print("Benzinga = " + data["Benzinga Recommendation"])
    # print("MarketBeat = " + data["MarketBeat Recommendation"])
    # print("Zacks = " + data["Zacks Recommendation"])
    # print("StockTargetAdvisor = " + data["StockTargetAdvisor Recommendation"])
    # print("StockChecker = " + data["StockChecker Recommendation"])
    # # print("TheGlobeandMail = " + data["TheGlobeandMail Recommendation"])
    # print("Score = " + str(data["Score"]))
    # end_session(session)