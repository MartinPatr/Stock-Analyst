from datetime import date
from urllib.request import urlopen
import certifi
import json

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
        'Score': ''
    }

    # Get api data
    try:
        get_api_data(stock_info)
    except:
        print("Error with fetching API Data")
        return None

    return stock_info

# Getting API Data
def get_api_data(stock_info):
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

url = ("https://financialmodelingprep.com/api/v3/key-metrics/AAPL?period=annual&apikey=a2LggDCNFTYKqYZIpjgibbKjLPQXgUVD")

if __name__ == "__main__":
    print(get_data("AAPL"))