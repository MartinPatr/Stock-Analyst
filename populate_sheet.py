import pygsheets

# Initialize Google API, return worksheet
def initialize_google_api():
    service_file = 'creds/stock-analyzer-399116-08d460de6a23.json'
    gc = pygsheets.authorize(service_file=service_file)
    sheet_name = "Stock Analyzer - Results"
    sh = gc.open(sheet_name)
    wks = sh.worksheet_by_title("Results")
    return wks

# Populate the sheet with the stocks
def populate_sheet(wks,stocks):    
    # Get the existing data from the worksheet
    data = wks.get_values(start='A1', end='A99999', returnas='matrix', majdim='ROWS')
    existing_data = [item for sublist in data for item in sublist]
    row = len(existing_data)

    # Iterate through the list of stocks
    for stock in stocks:
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
            print("Adding row: " + str(index))
            wks.update_values("A" + str(index) + ":" + "Z" + str(index), values=stock_data)
        else:
            # Append the new stock data to the bottom of the sheet
            row += 1
            print("Updating Row: " + str(row))
            wks.update_values("A" + str(row) + ":" + "Z" + str(row), values=stock_data)


# data = {
#     'Ticker': 'APPL',
#     'Score': 67,
#     'Price': '53.01',
#     'Industry': 'a',
#     'Sector': 'b',
#     'Description': 'c',
#     'Market Cap': 'd',
#     'P/E': 'f',
#     'P/S': 'f',
#     'P/B': 'f',
#     'EV/Sales': 'g',
#     'Current Ratio': 't',
#     "Cash Ratio": "y",
#     'Gross Margin': 'u',
#     'Debt to Equity': 'o',
#     '% of Insider Purchasing': 'p',
#     }


# data2 = {
#     'Ticker': 'ALGM',
#     'Score': 67,
#     'Price': '54.01',
#     'Industry': 'a',
#     'Sector': 'basdas',
#     'Description': 'c',
#     'Market Cap': 'd',
#     'P/E': 'f',
#     'P/S': 'f',
#     'P/B': 'f',
#     'EV/Sales': 'g',
#     'Current Ratio': 't',
#     "Cash Ratio": "y",
#     'Gross Margin': 'u',
#     'Debt to Equity': 'o',
#     '% of Insider Purchasing': 'p',
#     }

# stocks = [data, data2]
# wks = initialize_google_api()
# populate_sheet(wks, stocks)