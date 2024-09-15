import numpy as np
from get_data import get_api_data

def calculate_stock_score(stock_info):
    try: 
        print("Calculating stock score for", stock_info['Ticker'] + "...")
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
            'technology': 1.4,
            'financial services': 0.9,
            'healthcare': 1.3,
            'industrials': 1,
            'energy': 0.8,
            'utilities': 1,
            'consumer defensive': 1,
            'communication services': 1,
            'basic materials': 1,
            'real estate': 1.3,
            'consumer cyclical': 1.1
        }

        # Weights for each metric
        weights = {
            'market_cap': 0.05,
            'pe': 0.18,
            'ps': 0.18,
            'pb': 0.18,
            'ev_sales':0.15,
            'current_ratio': 0.2,
            'debt_to_equity': 0.2
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

        score = (weights['market_cap'] * market_cap_score +
                    weights['pe'] * pe_score +
                    weights['ps'] * ps_score +
                    weights['pb'] * pb_score +
                    weights['ev_sales'] * ev_sales_score +
                    weights['current_ratio'] * current_ratio_score +
                    weights['debt_to_equity'] * debt_to_equity_score)
        
        # Adjust score based on sector
        sector_adjustment = sector_adjustments.get(sector.lower(), 1.0)
        score *= sector_adjustment
        score = round(score*5,2)

        calculate_recommendation_score(stock_info, score)
    except Exception as e:
        print("Failed to get stockchecker score due to missing data: ", e)

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


def calculate_recommendation_score(stock_info,score):
    if score > 4:
        stock_info['StockChecker Recommendation'] = 'Heavy Buy - ' + str(score) + '/5'
    elif score > 3:
        stock_info['StockChecker Recommendation'] = 'Light Buy - ' + str(score) + '/5'
    elif score > 2:
        stock_info['StockChecker Recommendation'] = 'Hold - ' + str(score) + '/5'
    elif score > 1:
        stock_info['StockChecker Recommendation'] = 'Light Sell - ' + str(score) + '/5'
    else:
        stock_info['StockChecker Recommendation'] = 'Heavy Sell - ' + str(score) + '/5'


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
