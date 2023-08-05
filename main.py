import time
from datacollection import get_frontpage_url, get_data
from general_analysis import calculate_score

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
            if i == numStocks:  
                break
       
        # Sort the stocks based on the score in descending order
        sorted_stocks = sorted(stocks, key=lambda x: x['Score'], reverse=True)
    
        print(len(sorted_stocks))
        # Print out the companies with the highest scores
        i = 0
        for stock in sorted_stocks:            
            if i == 10:
                break
            print()
            print("--------------------------------------------------")
            print(f"Company: {stock['Ticker']}, Score: {stock['Score']}, Industry: {stock['Industry']}, Sector: {stock['Sector']}")           
            print(f"Price: {stock['Price']}, Market Cap: {stock['Market Cap']}")
            print(f"P/E: {stock['P/E']}, P/S: {stock['P/S']}, P/B: {stock['P/B']}, EV/Sales: {stock['EV/Sales']}")
            print(f"Description: {stock['Description']}") 
            i += 1

stock_analysis(100)