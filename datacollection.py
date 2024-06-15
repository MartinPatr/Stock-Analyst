from datetime import date
from urllib.request import urlopen
import certifi
import json
import requests
from bs4 import BeautifulSoup


# Main function to get data
def get_data(ticker):
    # Create a dictionary to store the data
    stock_info = {
        'Ticker': ticker,
        'Price': '1',
        'Volume': '1',
        'Market Cap': '1',
        'Date': date.today().strftime("%m/%d/%Y"),
        'Industry': '1',
        'Sector': '1',
        'Description': '1',
        'P/E': '2',
        'P/S': '2',
        'P/B': '2',
        'EV/Sales': '2',
        'Current Ratio': '2',
        'Debt to Equity': '2',
        'BarChart Recommendation': '',
        'Score': ''
    }


    # Get api data
    try:
        get_api_data(stock_info)
    except Exception as e:
        print(e)
        print("Error with fetching API Data")
        return None

    # Start webscraping and get recommendation data
    try:
        session = start_session()
        get_bar_chart_data(stock_info, session)

    except Exception as e:
        print(e)
        print("Error with fetching Recommendation Data")
        return None
    finally:
        end_session(session)
    

    return stock_info

# Getting API Data
def get_api_data(stock_info):
    ticker = stock_info["Ticker"]
    # Getting company profile information
    url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={get_api_key()}"
    company_profile_data = get_jsonparsed_api_data(url)
    stock_info['Volume'] = company_profile_data["volAvg"]
    stock_info['Market Cap'] = company_profile_data["mktCap"]
    stock_info['Industry'] = company_profile_data["industry"]
    stock_info['Sector'] = company_profile_data["sector"]
    stock_info['Description'] = company_profile_data["description"]

    # Getting company metrics information
    url = f"https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?period=annual&apikey={get_api_key()}"
    company_metrics_data = get_jsonparsed_api_data(url)
    stock_info['P/E'] = company_metrics_data["peRatio"]
    stock_info['P/S'] = company_metrics_data["priceToSalesRatio"]
    stock_info['P/B'] = company_metrics_data["pbRatio"]
    stock_info['EV/Sales'] = company_metrics_data["evToSales"]
    stock_info['Current Ratio'] = company_metrics_data["currentRatio"]
    stock_info['Debt to Equity'] = company_metrics_data["debtToEquity"]
   
def get_jsonparsed_api_data(url):
    response = urlopen(url, cafile=certifi.where())
    data = response.read().decode("utf-8")
    return json.loads(data)[0]

def get_api_key():
    with open('creds/creds.json', 'r') as file:
        data = json.load(file)
    return data["api_key"]

def start_session():
    # Initialize a session
    session = requests.Session()

    # Set a User-Agent header to make the request look like it is coming from a browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    })

    return session

def end_session(session):
    session.close()


def get_bar_chart_data(stock_info, session):
    ticker = stock_info["Ticker"]
    url = f"https://www.barchart.com/stocks/quotes/{ticker}/analyst-ratings"
    html = get_frontpage_url(session, ticker, url)
    if html is not None:
        try:
            soup = BeautifulSoup(html.text, 'html.parser')
            div_element = soup.find('div', class_='block__colored-header rating buy-mod')
            stock_info['BarChart Recommendation'] = div_element.text
        except Exception as e:
            print(e)
            print("Error with fetching Bar Chart Data with " + ticker)


# Get the page html
def get_frontpage_url(session, ticker, url):
    url.format(ticker=ticker)
    print(url)
    html = session.get(url)  # Use session to make the request
    if html.status_code == 200:
        return html
    else:
        print("Error with request html: " + url)
        

if __name__ == "__main__":
    print(get_data("AAPL"))