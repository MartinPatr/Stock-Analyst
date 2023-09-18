from bs4 import BeautifulSoup
import requests
import time
from datetime import date


# Get the front page 
def get_frontpage_url(stock_symbol):
    # Check if the stock symbol is not false
    if stock_symbol is False:
        return stock_symbol

    url = f"https://www.marketwatch.com/investing/stock/{stock_symbol}/company-profile?mod=mw_quote_tab"
    print(url)
    print("Ticker: " + stock_symbol)
    html = requests.get(url)
    if html.status_code == 200:
        return html
    else:
        check_error(html)
        html = requests.get(url)
        return html


# Get the data from the front page
def get_data(html,volumeRequired, numInfo):
    if html is False:
        return html

    #Use BeautifulSoup to parse the html
    soup = BeautifulSoup(html.text, 'html.parser')

    
    # Create a dictionary to store the data
    data = {
        'Ticker': soup.find('span', {'class': 'company__ticker'}).text,
        'Score': '',
        'Price': '',
        'State': 'Open',
        'Volume': '',
        'Date': date.today().strftime("%m/%d/%Y"),
        'Industry': '',
        'Sector': '',
        'Description': '',
        'P/E': '',
        'P/S': '',
        'P/B': '',
        'EV/Sales': '',
        'Current Ratio': '',
        "Cash Ratio": "",
        'Gross Margin': '',
        'Debt to Equity': '',
        '% of Insider Purchasing': '',
        'Net Income %': '',
        'Target Price': '',
        'Recommendation': '',
        'EPS %': '',
    }
    # The requirement variables
    volumeRequired = fix_volume(volumeRequired)
    

    

    # Finding main page stats
    pe_ratio_element = soup.find_all('td', {'class': 'w25'})
    pe_description_element = soup.find('p', {'class': 'description__text'})
    pe_value_element = soup.find_all('bg-quote', {'class': 'value'})
    pe_sector_element = soup.find_all('span', {'class': 'primary'})
    pe_na_element = soup.find_all('td',{'class':'is-na'})
    volume_elements = soup.find_all('span', {'class': 'primary'})
    volume = volume_elements[1].text
    state = soup.find('div', {'class': 'status'})
    # Too many NA's
    if len(pe_na_element) > numInfo:
        print("Not enough information")
        return False
    # Stock is closed
    elif state.text == "Closed":
        print("Stock is closed")
        data['State'] = "Closed"
        return data
    elif len(pe_ratio_element) == 29:
        stockVolume = fix_volume(volume)
        if stockVolume < volumeRequired:
            print("Not enough volume")
            return False
        data['Price'] = pe_value_element[0].text
        data['Volume'] = volume
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
        print("Unable to retrieve insider trading statistics")
        pass
    
    return data


# Fix volume given 
def fix_volume(volume):
    if "M" in volume:
        volume = float(volume.replace("M","").replace("Volume: ","").strip()) * 1000000
        return volume
    elif "B" in volume:
        volume = float(volume.replace("B","").replace("Volume: ","").strip()) * 1000000000
        return volume
    elif "K" in volume:
        volume = float(volume.replace("K","").replace("Volume: ","").strip()) * 1000
        return volume
    else:
        return float(volume)

# Check for 403 Error
def check_error(html):
    if html.status_code == 403:
        check_status(html)
    else:
        return 

# Continuously check for 403 Error
def check_status(html):
    delay = 5  # Initial delay time in seconds
    while html.status_code == 403:
        print("Checking for 403 Error")
        time.sleep(delay)
        delay = min(delay * 2, 60*60)  # Double the delay time, capped at 1 hour
        html = requests.get("https://www.marketwatch.com/investing/stock/AAPL/company-profile?mod=mw_quote_tab")
        if html.status_code == 200:
            print("403 Error has been resolved")
            break
    return


# html = get_frontpage_url("ACMR")
# print(get_data(html, "ACMR"))
