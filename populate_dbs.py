import pygsheets
import json
import certifi
from pymongo import MongoClient

# Initialize Google API, return worksheet
def initialize_google_api(credentialsPath):
    service_file = credentialsPath; 
    gc = pygsheets.authorize(service_file=service_file)
    sheet_name = "Stock Analyzer - Results"
    sh = gc.open(sheet_name)
    wks = sh.worksheet_by_title("Results")
    return wks

# Populate the sheet with the stocks
def populate_sheet(wks,stock):    
    # Get the existing data from the worksheet
    data = wks.get_values(start='A1', end='A99999', returnas='matrix', majdim='ROWS')
    existing_data = [item for sublist in data for item in sublist]
    row = len(existing_data)

    # Iterate through the list of stocks
    ticker = stock['Ticker']
    stock_data = [list(stock.values())]
    # Remove ticker's status
    stock_data[0].pop(3)
    # Remove "Volume: " from the volume
    stock_data[0][3] = stock_data[0][3].replace("Volume: ", "")
    # Add % to certain values
    stock_data[0][16] =  str(stock_data[0][16]) + "%" if stock_data[0][16] != False else str(stock_data[0][16])
    stock_data[0][17] = str(stock_data[0][17]) + "%" if stock_data[0][17] != False else str(stock_data[0][17])
    stock_data[0][20] = str(stock_data[0][20]) + "%" if stock_data[0][20] != False else str(stock_data[0][20])

    # Check if the stock's ticker is already in the sheet
    if ticker in existing_data:
        # Update the existing row with the new data
        index = existing_data.index(ticker) + 1
        print(f"Updating Row for {ticker}: " + str(index))
        wks.update_values("A" + str(index) + ":" + "Z" + str(index), values=stock_data)
    else:
        # Append the new stock data to the bottom of the sheet
        row += 1
        print(f"Adding Row for {ticker}: " + str(row))
        wks.update_values("A" + str(row) + ":" + "Z" + str(row), values=stock_data)

def populate_db(stock):
    config_file_path = 'creds/mongodbcreds.json'
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