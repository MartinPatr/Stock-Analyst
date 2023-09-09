import time
from datacollection import get_frontpage_url, get_data
from general_analysis import calculate_score
from detailed_analysis import update_score, close_driver

# Calculate the final score for each stock
def stock_analysis(startStock,numStocks, secondRound):
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
                check_number_requests(i)

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
                    data = get_data(html)
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
            else:
                print("Skipping stock: " + str(i+1))
        # Sort the stocks based on the score in descending order
        sorted_stocks = sorted(stocks, key=lambda x: x['Score'], reverse=True)
        
        # Only keep the top secondRound stocks
        i = 0
        for i,stock in enumerate(sorted_stocks.copy()):
            # If the user wants to analyze all the stocks, break
            if type(secondRound) == str and secondRound.lower() == "all":
                break
            elif i >= secondRound:
                sorted_stocks.remove(stock)

        # Run detailed analysis on the top 100 stocks
        for i, stock in enumerate(sorted_stocks):
            print()
            print("Detailed analysis: " + str(i+1))
            print("Current Score: " + str(stock['Score']))
            update_score(stock)
            print("Updated Score: " + str(stock['Score']))

        # Close the driver
        close_driver()

        # Sort the stocks based on the score in descending order
        sorted_stocks = sorted(sorted_stocks, key=lambda x: x['Score'], reverse=True)


        # Add stocks that should be ignored to the ignore to ignoretickers.txt
        with open("data/ignoretickers.txt", "a") as file:
            for stock in removeStocks:
                file.write(stock['Ticker'] + "\n")

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
def check_number_requests(i):
    # If the number of requests is 0, return
    if i == 0:
        return
    # Sleep for 1 minute every 1000 requests to avoid getting blocked
    elif i % 1000 == 0:
        print("Sleeping for 1 minute")
        time.sleep(60)
    # Sleep for 30 seconds every 250 requests to avoid getting blocked
    elif i % 250 == 0:
        print("Sleeping for 30 seconds")
        time.sleep(30)

            
# Run the program
stocks = stock_analysis(0,2999,50)
print_data(stocks,25)