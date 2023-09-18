import time
from datacollection import get_frontpage_url, get_data
from general_analysis import calculate_score
from detailed_analysis import update_score, close_driver
from populate_sheet import initialize_google_api, populate_sheet

# Calculate the final score for each stock
# startStock: The number of the stock to start analyzing
# numStocks: The number of stocks to analyze
# secondRound: How many stocks you want to bring to the second round
# volume: The volume requirement for the stocks(Must be a string) - Used in get_data
# numInfo: The maximum number of NA's to be analyized - Used in get_data
# googleSheets: Whether or not to populate the Google Sheets
def stock_analysis(startStock,numStocks, secondRound, volume, numInfo, googleSheets=False):
    stocks = []
    removeStocks = []
    ignoreStocks = []

    # Get the list of stocks to ignore
    with open('data/ignoretickers.txt', 'r') as file:
        for i, line in enumerate(file):
            ignoreStocks.append(line.strip())
            

    with open('data/validtickers.txt', 'r') as file:
        for i, line in enumerate(file):
            # Only start analyzing the stocks after the startStock
            if i >= startStock-1:
                # Only analyze the amount of stocks specified
                if i == numStocks-1:  
                    break
                # Check if the number of requests
                check_number_requests(startStock,numStocks,i)

                print()
                print("Number: " + str(i+1))
                tickerList = line.strip().split()
                ticker = str(tickerList[0])

                # Check if the ticker is on "ignore" list
                if ticker in ignoreStocks:
                    print("Ticker is on ignore list")
                    ticker = False

                html = get_frontpage_url(ticker)
                try:
                    data = get_data(html,volume,numInfo)
                except Exception as e:
                    data = False
                    print(e)
                    print("Unable to retrieve main page statistics")
                
                if data is not False:
                    if data['State'] == "Closed":
                        removeStocks.append(data)
                    else:
                        # Replace empty values with False
                        for key in data:
                            if data[key] == '' or data[key] == 'N/A':
                                data[key] = False
                        # Calculate the score
                        calculate_score(data)
                        stocks.append(data)

        # If user wants all the stocks to go to the second round, then don't sort or remove any stocks
        if type(secondRound) != str and secondRound.lower() != "all":
            # Sort the stocks based on the score in descending order
            stocks = sorted(stocks, key=lambda x: x['Score'], reverse=True)
            # Only keep the top secondRound stocks
            for i,stock in enumerate(stocks.copy()):
                # If the user wants to analyze all the stocks, break
                if i >= secondRound:
                    stocks.remove(stock)

        # Run detailed analysis on the top 100 stocks
        for i, stock in enumerate(stocks):
            print()
            print("Detailed analysis: " + str(i+1))
            print("Current Score: " + str(stock['Score']))
            update_score(stock)
            print("Updated Score: " + str(stock['Score']))

        # Close the driver
        close_driver()

        # Add stocks that should be ignored to the ignore to ignoretickers.txt
        with open("data/ignoretickers.txt", "a") as file:
            for stock in removeStocks:
                file.write(stock['Ticker'] + "\n")

        # Check if the user wants to populate the Google Sheets
        if googleSheets:
            # Initialize the Google Sheets API
            wks = initialize_google_api()
            # Populate the sheet with the stocks
            populate_sheet(wks,stocks)
        else:
            # Sort the stocks based on the score in descending order
            sorted_stocks = sorted(sorted_stocks, key=lambda x: x['Score'], reverse=True)


        return sorted_stocks



# Function to print out the data
def print_data(stocks, numStocks):
    # Print out the companies with the highest scores
    for i, stock in enumerate(stocks):            
        if i == numStocks:
            break
        print()
        print("--------------------------------------------------")
        print(f"Number: {i+1}")
        print(f"Company: {stock['Ticker']}, Score: {stock['Score']}, Industry: {stock['Industry']}, Sector: {stock['Sector']}")           
        print(f"Price: {stock['Price']}, Target Price: {stock['Target Price']} ,Recommendation: {stock['Recommendation']}, {stock['Volume']}")
        print(f"P/E: {stock['P/E']}, P/S: {stock['P/S']}, P/B: {stock['P/B']}, EV/Sales: {stock['EV/Sales']}, Net Income Growth: {stock['Net Income %']}%, Profit Margin: {stock['Gross Margin']}")
        print(f"Description: {stock['Description']}") 


# Function to check the number of requests made and sleep if necessary
def check_number_requests(start,end,i):
    numStocks = end - start + 1
    numThousands = numStocks // 500
    if numThousands == 0: 
        numThousands = 1
    # If the number of requests is 0, return
    if i == 0:
        return
    # Sleep for x minutes(Depends on how much is being analyized total) every 1000 requests to avoid getting blocked
    elif i % 1000 == 0:
        print("Sleeping for 1 minute")
        time.sleep(60*(numThousands))
    # Sleep for 30 seconds every 250 requests to avoid getting blocked
    elif i % 250 == 0:
        print("Sleeping for 30 seconds")
        time.sleep(30)

            
# Run the program
stocks = stock_analysis(51,499,"all","0",13,True)
#print_data(stocks,10)