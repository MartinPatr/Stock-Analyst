import numpy as np
from get_data import get_api_data

def calculate_stock_score(stock_info):
    market_cap = float(stock_info['Market Cap'])
    pe = float(stock_info['P/E'])
    ps = float(stock_info['P/S'])
    pb = float(stock_info['P/B'])
    ev_sales = float(stock_info['EV/Sales'])
    current_ratio = float(stock_info['Current Ratio'])
    debt_to_equity = float(stock_info['Debt to Equity'])
    sector = stock_info['Sector']

    # Adjustments for sector
    sector_adjustments = {
        'technology': 1.15,
        'finance': 1.0,
        'healthcare': 1.0,
        'industrial': 0.9,
        'consumer': 1.0,
        'energy': 0.9,
        'utilities': 0.9,
        'materials': 0.9,
    }

    # Weights for each metric
    weights = {
        'market_cap': 0.05,
        'pe': 0.225,
        'ps': 0.225,
        'pb': 0.225,
        'ev_sales':0.175,
        'current_ratio': 0.275,
        'debt_to_equity': 0.275
    }

    market_cap_score = np.tanh(market_cap / 1e12)

    # Scoring function that gives higher score for values below the average
    # and lower scores for values above the average
    def score_below_avg(value, avg):
        if value < 0:
            return 0  # Very low score for negative values
        return 1 / (1 + np.exp((value - avg) / avg))

    # Scoring function that gives higher score for values above the average
    # and lower scores for values below the average
    def score_above_avg(value, avg):
        if value < 0:
            return 0  # Very low score for negative values
        return np.tanh(value / avg)  # Use tanh to scale the score between 0 and 1

    # PE ratio, typical average is 25
    pe_score = score_below_avg(pe, 25)

    # PS ratio, typical average is 5
    ps_score = score_below_avg(ps, 5)

    # PB ratio, typical average is 3
    pb_score = score_below_avg(pb, 3)

    # EV/Sales ratio, typical average is 4
    ev_sales_score = score_below_avg(ev_sales, 4)

    # Current Ratio, typical average is 1
    current_ratio_score = score_above_avg(current_ratio, 1)

    # Debt to Equity, typical average is 1
    debt_to_equity_score = score_below_avg(debt_to_equity, 1)

    # print("Market Cap Score:", market_cap_score)
    # print("P/E Score:", pe_score)
    # print("P/S Score:", ps_score)
    # print("P/B Score:", pb_score)
    # print("EV/Sales Score:", ev_sales_score)
    # print("Current Ratio Score:", current_ratio_score)
    # print("Debt to Equity Score:", debt_to_equity_score)

    score = (weights['market_cap'] * market_cap_score +
                weights['pe'] * pe_score +
                weights['ps'] * ps_score +
                weights['pb'] * pb_score +
                weights['ev_sales'] * ev_sales_score +
                weights['current_ratio'] * current_ratio_score +
                weights['debt_to_equity'] * debt_to_equity_score)
    
    # Adjust score based on sector
    print(f"Initial Score: {score:.2f}")
    sector_adjustment = sector_adjustments.get(sector.lower(), 1.0)
    score *= sector_adjustment

    return score

# Example usage:
# stock_info = {
#         'Ticker': 'AAPL',
#         'Price': '145.86',
#         'Volume': '1000000',
#         'Market Cap': '2.4e12',
#         'Sector': 'Technology',
#         'Description': 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.',
#         'P/E': '28.5',
#         'P/S': '6.7',
#         'P/B': '35.2',
#         'EV/Sales': '6.5',
#         'Current Ratio': '1.2',
#         'Debt to Equity': '1.5'
# }


if __name__ == "__main__":
    stock_data = {
        'Ticker': 'RBLX'
    } 
    try:
        stock_info = get_api_data(stock_data)
        print(stock_info)
    except Exception as e:
        print(e)
        print("Error grabbing stock data from API")
    stock = calculate_stock_score(stock_info)
    print(f"Stock Score: {stock:.2f}")
