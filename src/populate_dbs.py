import pygsheets
import json
import certifi
from pymongo import MongoClient
from get_data import get_current_average

# Initialize Google API, return worksheet
def initialize_google_api(credentialsPath):
    try:
        service_file = credentialsPath; 
        gc = pygsheets.authorize(service_file=service_file)
        sheet_name = "Stock Analyzer - Results"
        sh = gc.open(sheet_name)
        wks = sh.worksheet_by_title("Results")
    except Exception as e:
        print("Failed to initialize Google API: ", e)
        print("Terminating...")
        return False
    return wks

# Populate the sheet with the stocks
def populate_sheet(wks,stock):
    print("Populating Google Sheet...")
    # Get the existing data from the worksheet
    data = wks.get_values(start='A1', end='A99999', returnas='matrix', majdim='ROWS')
    existing_data = [item for sublist in data for item in sublist]
    row = len(existing_data)

    # Iterate through the list of stocks
    ticker = stock['Ticker']

    check_NA = list(stock.values())
    if check_NA.count("N/A") > 15:
        print(f"Skipping {ticker} as there is not enough data")
        return

    # Replace certian values with google finance values
    if stock['Company Name'] is None or stock['Company Name'] == "N/A" or stock['Company Name'] == "" or stock['Company Name'].isdigit():
        stock['Company Name'] = f"=GOOGLEFINANCE(\"{ticker}\",\"name\")"

    if stock['Price'] is None or stock['Price'] == "N/A" or stock['Price'] == "":
        stock['Price'] = f"=GOOGLEFINANCE(\"{ticker}\",\"price\")"

    if stock['Market Cap'] is None or stock['Market Cap'] == "0" or stock['Market Cap'] == "":
        stock['Market Cap'] = f"=GOOGLEFINANCE(\"{ticker}\",\"marketcap\")"
    
    if stock['Volume'] is None or stock['Volume'] == "N/A" or stock['Volume'] == "":
        stock['Volume'] = f"=GOOGLEFINANCE(\"{ticker}\",\"volume\")"
    
    if stock['Industry'] is None or stock['Industry'] == "N/A" or stock['Industry'] == "":
        stock['Industry'] = "N/A"

    if stock['Sector'] is None or stock['Sector'] == "N/A" or stock['Sector'] == "":
        stock['Sector'] = "N/A"
    
    current_average_score = get_current_average(ticker)

    stock_data = list(stock.values())
    stock_data = [stock_data]

    # Check if the stock's ticker is already in the sheet
    if ticker in existing_data:
        # Update the existing row with the new data
        index = existing_data.index(ticker) + 1

        # Add formulas to the stock data
        stock_data[0].append(f"= (AD{index}+AE{index})/2")
        stock_data[0].append(f"=IF(M{index}=\"N/A\", \"N/A\", M{index} & \" - \" & AC{index} & \"/5\")")

        print(f"Updating Row for {ticker}: " + str(index))
        wks.update_values("A" + str(index) + ":" + "Z" + str(index), values=stock_data)

        new_average_score = get_current_average(ticker) 

        if current_average_score == 0:
           average_change = 0
        else:
            average_change = (new_average_score - current_average_score)/current_average_score 


        wks.update_value(f"W{index}", round(average_change,2))

    else:
        # Append the new stock data to the bottom of the sheet
        row += 1

        # Add formulas to the stock data
        stock_data[0].append(f"= (AD{row}+AE{row})/2")
        stock_data[0].append(f"=IF(M{row}=\"N/A\", \"N/A\", M{row} & \" - \" & AC{row} & \"/5\")")
        
        print(f"Adding Row for {ticker}: " + str(row))
        wks.update_values("A" + str(row) + ":" + "Z" + str(row), values=stock_data)

        average_score = 0
        wks.update_value(f"W{row}", average_score)

def populate_db(stock):

    config_file_path = 'creds/creds.json'
    # Read the JSON data from the file
    with open(config_file_path, 'r') as file:
        json_data = file.read()
    parsed_data = json.loads(json_data)
    # Get the connection string
    connection_string = parsed_data.get("connection_string")
    # Create a new client and connect to the server
    ca = certifi.where()
    client = MongoClient(connection_string, tlsCAFile=ca)

    db = client['StockAnalyzerResults']
    collection = db['Stocks']

    insert_doc = collection.insert_one(stock)
    print(f'Added to database successfully:  {insert_doc.inserted_id}')
    client.close

if __name__ == "__main__":
    stock_data = {
        'Ticker': 'RBLX',
        'Company Name': '12312',
        'Price': '0',
        'Volume': '0',
        'Market Cap': '0',
        'Date': '07/20/2021',
        'Sector': 'Technology',
        'Industry': 'Software - Application',
        'BarChart Recommendation': 'N/A',
        'Benzinga Recommendation': 'N/A',
        'MarketBeat Recommendation': 'N/A',
        'Zacks Recommendation': 'N/A',
        'StockTargetAdvisor Recommendation': 'N/A',
        'StockChecker Recommendation': 'N/A',
        'P/E': 'N/A',
        'P/S': 'N/A',
        'P/B': 'N/A',
        'EV/Sales': 'N/A',
        'Current Ratio': 'N/A',
        'Debt to Equity': 'N/A',
    }
    wks = initialize_google_api("creds/credentials.json")
    if not wks:
        print("Terminating...")
        exit()
    
    populate_sheet(wks, stock_data)


    




   