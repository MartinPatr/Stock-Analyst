# Stock Analyzer
## Overview

Stock Analyzer is a tool designed to analyze stock data, populate Google Sheets with the analyzed data, and store the data in a MongoDB database. This project utilizes various APIs to gather stock information and recommendations, processes the data, and then makes it available for further analysis or reporting.

## Files Description

### main.py

The main script of the project. It performs the following tasks:
- Reads a list of stock tickers from a file (`data/tickers.txt`).
- Initializes a session for data gathering.
- Iterates through the tickers, gathering data for each one.
- Populates a Google Sheet with the gathered data.
- Optionally stores the data in a MongoDB database.

**Functions:**
- `main(numberStart=0, numberEnd=6000)`: The entry point of the script, which processes a range of tickers from the file.
  - Initializes Google Sheets API.
  - Starts a data gathering session.
  - Iterates through tickers, gathering data and populating Google Sheets.
  - Ends the session and prints the elapsed time.

### populate_db.py

This script is responsible for populating the Google Sheet with stock data and storing the data in a MongoDB database.

**Functions:**
- `initialize_google_api(credentialsPath)`: Initializes the Google Sheets API using the provided credentials and returns the worksheet object.
- `populate_sheet(wks, stock)`: Populates the Google Sheet with the provided stock data. It checks if the stock ticker already exists in the sheet and updates or adds new data accordingly.
- `populate_db(stock)`: Stores the provided stock data in a MongoDB database.

### Supporting Files

#### data/tickers.txt
- A file containing a list of stock tickers to be analyzed.

#### creds/credentials.json
- A JSON file containing the credentials required to authenticate with the Google Sheets API.

#### creds/creds.json
- A JSON file containing the connection string for the MongoDB database.

## Usage

1. **Setup Google API Credentials:**
   - Ensure you have a `credentials.json` file with the necessary Google API credentials.
   - Place this file in the `creds` directory.

2. **Setup MongoDB Credentials:**
   - Ensure you have a `creds.json` file with the necessary MongoDB connection string.
   - Place this file in the `creds` directory.

3. **Run the Main Script:**
   ```bash
   python main.py