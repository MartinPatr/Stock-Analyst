# Description: This file contains the functions used to perform the general analysis of the stocks
def calculate_score(data):
    # Weightages for each factor
    weightages = {
        'P/E': 0.2,
        'P/S': 0.15,
        'P/B': 0.15,
        'Current Ratio': 0.1,
        'Cash Ratio': 0.1,
        'Gross Margin': 0.1,
        'Debt to Equity': 0.1,
        '% of Insider Purchasing': 0.1,
    }

    # Ideal ranges for each factor 
    ideal_ranges = {
        'P/E': (-15, 15),
        'P/S': (-1.5, 1.5),
        'P/B': (-1.5, 1.5),
        'Current Ratio': (2, 4), 
        'Cash Ratio': (-10, 10),
        'Gross Margin': (0, 200), 
        'Debt to Equity': (0, 3),
        '% of Insider Purchasing': (0, 200)
    }

    score = 0

    for factor, weight in weightages.items():
        if factor in ideal_ranges and data[factor] != False:
            value = data[factor]
            if not isinstance(value, int):
                value = float(value.replace(",", "").replace("%", ""))


            min_val, max_val = ideal_ranges[factor]

            # Normalize the value to a range between 0 and 1
            normalized_value = (value - min_val) / (max_val - min_val)

            # Calculate score for the factor based on its distance from the ideal range
            factor_score = (1 - abs(normalized_value - 0.5)) * weight
            score += factor_score

    # Store the overall score in the data dictionary
    score = round(score, 2) * 100
    data['Score'] = score
