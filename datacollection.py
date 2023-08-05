from bs4 import BeautifulSoup
import requests

# Get the front page 
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


# Get the data from the front page
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
