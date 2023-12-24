# Stock Analyzer

Stock Analyzer is a tool for analyzing stock data, retrieving financial information, and providing scores based on various factors. It includes modules for data collection, general analysis, selenium-based analysis, detailed analysis, and database population.

## Overview

The Stock Analyzer project addresses the need for a comprehensive tool to assess stock performance and make informed investment decisions. It combines web scraping techniques, financial analysis, and data visualization to provide users with valuable insights into the stocks they are interested in. The main features of the Stock Analyzer include:

Data Collection: Utilizes web scraping to collect stock data from MarketWatch, extracting relevant information for analysis.

General Analysis: Performs a broad analysis of stock data, calculating scores based on key financial metrics and industry benchmarks.

Selenium-based Analysis: Utilizes Selenium to retrieve detailed financial information, enhancing the depth of analysis for a more accurate score.

Detailed Analysis: Incorporates in-depth analysis, including net income growth, EPS growth, analyst recommendations, and target prices, contributing to a refined overall score.

Database Population: Populates databases, supporting Google Sheets and MongoDB, to store and organize the analyzed stock data

## configuration.json
start: The number of the stock to start analyzing. This is used to specify the starting point when analyzing a list of stocks.

end: The number of stocks to analyze. Together with the start parameter, this determines the range of stocks to be analyzed.

secondRound: Specifies how many stocks you want to bring to the second round of analysis. If set to "all," all stocks will go through the second round.

minimumVolume: The volume requirement for the stocks. It must be a string and is used in the get_data function.

maxNA: The maximum number of NA's to be analyzed. If the number of NA's exceeds this threshold for a stock, it won't be analyzed.

database: Specifies whether to populate the Google Sheets, MongoDB, or both. It accepts values "gs," "mongodb," "all," or null (if you don't want to populate any database).

useSelenium: Specifies whether to use Selenium to retrieve financials and analysis. Set to true if you want to use Selenium, false otherwise.

googleCloudCredPath: Path to the JSON file containing Google Cloud credentials. It is used when populating Google Sheets.

## Additional information
If you want to use google sheet or mongodb create a folder called creds and place the following files
mongodbcreds.json:
{
    "connection_string": "mongodb+srv://<username>:<password>@cluster0.cs66unx.mongodb.net/?retryWrites=true&w=majority"
}
&
credentials.json
in configuration put the path of where you will place google clouds credentials.json. The default path is creds/credentials.jsons
