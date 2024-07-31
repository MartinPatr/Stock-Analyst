import json
import sys
import time
from datetime import date
from get_data import get_recommendation_data, get_api_data, start_session, end_session
from general_analysis import calculate_stock_score
from populate_dbs import initialize_google_api, populate_sheet

def main(numberStart=0, numberEnd=6000):
    start_time = time.time()
    with open('data/tickers.txt', 'r') as file:
        wks = initialize_google_api("creds/credentials.json")
        if not wks:
            return
        session = start_session()
        for i, line in enumerate(file):
            if i >= numberStart:
                if i >= numberEnd:
                    break
                ticker = line.split(',')[0] 
                print("Processing number " + str(i) + ": " + ticker)
                stock_info = {
                    'Ticker': ticker,
                    'Company Name': 'N/A',
                    'Price': 'N/A',
                    'Volume': 'N/A',
                    'Market Cap': '0',
                    'Date': date.today().strftime("%m/%d/%Y"),
                    'Industry': 'N/A',
                    'Sector': 'N/A',
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
                    'Debt to Equity': 'N/A'
                }
                # Get webscraped recommendation data
                get_recommendation_data(stock_info, session)     

                # Get API data
                api_response = get_api_data(stock_info)

                # Calculate stock score
                if api_response:
                    calculate_stock_score(stock_info)
 

                print(stock_info)

                # Initialize the Google Sheets API, if the user wants to populate the Google Sheets
                populate_sheet(wks, stock_info)
                print("--------------------------------------------------")
                print()

    
    # Calculate the elapsed time
    end_session(session)

    end_time = time.time()  
    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time} seconds" + " for " + str(numberEnd - numberStart) + " stocks")

def read_values(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
    start = data.get('start', 0)
    end = data.get('end', 200)
    return start, end

# Function to update values in the JSON file
def update_values(filename):
    _, end = read_values(filename)
    new_start = end
    new_end = (end + 200) % 5782
    data = {
        "start": new_start,
        "end": new_end
    }
    with open(filename, 'w') as file:
        json.dump(data, file)

if __name__ == "__main__":
    try:
        start, end = sys.argv[1], sys.argv[2] if len(sys.argv) > 1 else read_values('data/indices.json')
        main(start, end)
    except Exception as e:
        print(e)
        print("Error in main function")

