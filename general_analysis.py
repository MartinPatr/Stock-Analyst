# Description: This file contains the functions used to perform the general analysis of the stocks
import math
from datacollection import fix_volume

# Calculate the score of the stock
def calculate_score(data):
    # Weightages for each factor
    weightages = {
        'P/E': 0.2,
        'P/S': 0.15,
        'P/B': 0.15,
        'EV/Sales': 0.15,
        'Current Ratio': 0.125,
        'Cash Ratio': 0.125,
        'Gross Margin': 0.1,
        'Debt to Equity': 0.1,
        '% of Insider Purchasing': 0.05,
    }

    # Ideal ranges for each factor 
    ideal_ranges = {
        'P/E': (-15, 15),
        'P/S': (-1.5, 1.5),
        'P/B': (-1.5, 1.5),
        'EV/Sales': (-3, 3),
        'Current Ratio': (2, 4), 
        'Cash Ratio': (-10, 10),
        'Gross Margin': (0, 200), 
        'Debt to Equity': (-20, 20),
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

            # Apply a linear adjustment if factor_score is less than -0.5
            if factor_score < -0.5:
                difference =  abs(factor_score // 0.5)
                factor_score = -0.5 + ((-1 * (difference * 0.05)))

            # Apply logarithmic adjustment if factor_score is less than -0.25
            elif factor_score < -0.25:
                factor_score = -0.25 + (1 - abs(factor_score / -0.25)) * math.log(abs(factor_score) + 0.25)

            # If volume is greater than 1 million, increase the factor score by 33% if it is positive and decrease it by 33% if it is negative
            if fix_volume(data['Volume']) > 1000000:
                factor_score = factor_score * 1.25 if factor_score > 0 else factor_score * 0.75

            score += factor_score


    # Store the overall score in the data dictionary
    score = round(score, 2) * 100
    data['Score'] = score
