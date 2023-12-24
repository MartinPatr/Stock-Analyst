import time
import json
from datacollection import get_frontpage_url, get_data
from general_analysis import calculate_score
from selenium_analysis import get_financials, close_driver
from detailed_analysis import update_score,retrieve_financials, retrieve_analysis
from populate_dbs import initialize_google_api, populate_sheet, populate_db
import concurrent.futures

# Calculate the final score for each stock
# startStock: The number of the stock to start analyzing
# numStocks: The number of stocks to analyze
# secondRound: How many stocks you want to bring to the second round
# volume: The volume requirement for the stocks(Must be a string) - Used in get_data
# numInfo: The maximum number of NA's to be analyized - Used in get_data
# db: Whether or not to populate the Google Sheets, mongodb, or both
# selenium: Whether or not to use Selenium to retrieve the financials and analysis
def stock_analysis(startStock,numStocks, secondRound, volume, numInfo, db=None, selenium=False ,configurationPath="configuration.json"):
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
        if type(secondRound) == str and secondRound.lower() != "all":
            # Sort the stocks based on the score in descending order
            stocks = sorted(stocks, key=lambda x: x['Score'], reverse=True)
            # Only keep the top secondRound stocks
            for i,stock in enumerate(stocks.copy()):
                # If the user wants to analyze all the stocks, break
                if i >= secondRound:
                    stocks.remove(stock)

    # Combat memory leaks
    ignoreStocks = file = html = tickerlist = None

    # Number of threads
    num_threads = 2  # You can adjust this to the desired number of threads

    segment_size = len(stocks) // num_threads
    stock_segment_1 = stocks[:segment_size]
    stock_segment_2 = stocks[segment_size:]
    print()
    print("Running round 2 with " + str(num_threads) + " threads")
    # Function for the thread to execute
    def process_stock(stock,i, segment):
        get_second_round_info(startStock, numStocks, i, stock, selenium, segment)

    # Create a thread pool with two threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []

        # Submit each stock in the first segment for processing in the first thread
        for i, stock in enumerate(stock_segment_1):
            future = executor.submit(process_stock, stock,i,1)
            futures.append(future)

        # Submit each stock in the second segment for processing in the second thread
        for i, stock in enumerate(stock_segment_2):
            future = executor.submit(process_stock, stock,i,2)
            futures.append(future)

        # Wait for all threads to finish
        concurrent.futures.wait(futures)
    
    if selenium:
        # Close the driver
        close_driver()

    # Add stocks that should be ignored to the ignore to ignoretickers.txt
    with open("data/ignoretickers.txt", "a") as file:
        for stock in removeStocks:
            file.write(stock['Ticker'] + "\n")

    # Update db
    if db is not None:
        # Initialize the Google Sheets API, if the user wants to populate the Google Sheets
        wks = initialize_google_api(configurationPath) if db == "gs" or db == "all" else False
        print()
        print("Populating")
        for stock in stocks:
            # Populate the Google Sheets
            print()
            if db == "gs" or db == "all":
                populate_sheet(wks, stock)
            if db == "mongodb" or db == "all":
                populate_db(stock)
    else:
        # Sort the stocks based on the score in descending order
        sorted_stocks = sorted(stocks, key=lambda x: x['Score'], reverse=True)
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
def check_number_requests(start,end,i,selenium = True):
    # If its the first stock, return
    if i == start:
        return
    numStocks = end - start + 1
    numThousands = numStocks // 500
    if numThousands == 0: 
        numThousands = 1
    # If the number of requests is 0, return
    if i == 0:
        return
    # Sleep for x minutes(Depends on how much is being analyized total) every 1000 requests to avoid getting blocked
    elif i % 1000 == 0:
        print("Sleeping for " + str(numThousands) + " minutes")
        time.sleep(60*(numThousands))
    # Sleep for 30 seconds every 250 requests to avoid getting blocked
    elif i % 250 == 0:
        print("Sleeping for 30 seconds")
        time.sleep(30)
    # Sleep for 15 seconds every 50 requests to avoid getting blocked
    elif i % 25 == 0 and not selenium:
        print("Sleeping for 15 seconds")
        time.sleep(15)

def get_second_round_info(startStock,numStocks,i,stock,selenium,threadNum):
    # Run detailed analysis on the top 100 stocks
    check_number_requests(startStock,numStocks,i, selenium)
    print(f"Thread {threadNum} - Current Score for {stock['Ticker']}:  {stock['Score']}")
    url = update_score(stock)
    # Check if the user wants to use selenium
    if selenium:
        get_financials(stock,url)
    # If the user doesn't want to use selenium
    else:
        retrieve_financials(stock)
        retrieve_analysis(stock)
    print(f"Thread {threadNum} - Updated Score for {stock['Ticker']}:  {stock['Score']}")
            
# Function to read configurations from JSON file
def read_configurations(file_path):
    with open(file_path, 'r') as file:
        config_data = json.load(file)
    return config_data

# Path to the JSON file
config_file_path = 'configuration.json'
configurations = read_configurations(config_file_path)

# Use configurations to initialize stock_analysis
stocks = stock_analysis(
    configurations["start"],
    configurations["end"],
    configurations["secondRound"],
    configurations["minumumVolume"],
    configurations["maxNA"],
    configurations["database"],
    configurations["useSelenium"],
    configurations["googleCloudCredPath"]
)

print_data(stocks,10)