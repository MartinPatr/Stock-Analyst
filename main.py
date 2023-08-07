import time
from datacollection import get_frontpage_url, get_data
from general_analysis import calculate_score
from detailed_analysis import update_score, close_driver

# Calculate the final score for each stock
def stock_analysis(numStocks):
    stocks = []
    with open('data/validtickers.txt', 'r') as file:
        for i, line in enumerate(file):
            print("Number: " + str(i))
            tickerList = line.strip().split()
            ticker = str(tickerList[0])
            html = get_frontpage_url(ticker)
            try:
                data = get_data(html, ticker)
            except:
                print("Unable to retrieve main page statistics")
            if data is not False:
                # Replace empty values with False
                for key in data:
                    if data[key] == '' or data[key] == 'N/A':
                        data[key] = False
                # Calculate the score
                calculate_score(data)
                stocks.append(data)
            # Only analyze the amount of stocks specified
            if i == numStocks:  
                break
            # Sleep for 1 minute every 100 requests to avoid getting blocked
            elif i % 100 == 0 and i != 0:
                time.sleep(60)
       
        # Sort the stocks based on the score in descending order
        sorted_stocks = sorted(stocks, key=lambda x: x['Score'], reverse=True)

        # Only keep the top 100 stocks
        numStocks = 25
        i = 0
        for stock in sorted_stocks.copy():
            if i >= numStocks:
                sorted_stocks.remove(stock)
            i += 1

        # Run detailed analysis on the top 100 stocks
        for i, stock in enumerate(sorted_stocks):
            print()
            print("Detailed analysis: " + str(i))
            update_score(stock)
        # Close the driver
        close_driver()

        return sorted_stocks

             
         

# Function to print out the data
def print_data(stocks, numStocks):
    # Print out the companies with the highest scores
    for i, stock in enumerate(stocks):            
        if i == numStocks:
            break
        print()
        print("--------------------------------------------------")
        print(f"Company: {stock['Ticker']}, Score: {stock['Score']}, Industry: {stock['Industry']}, Sector: {stock['Sector']}")           
        print(f"Price: {stock['Price']}, Recommendation: {stock['Recommendation']}")
        print(f"P/E: {stock['P/E']}, P/S: {stock['P/S']}, P/B: {stock['P/B']}, EV/Sales: {stock['EV/Sales']}")
        print(f"Description: {stock['Description']}") 
        i += 1


stocks = stock_analysis(99)
print(len(stocks))
print_data(stocks,10)