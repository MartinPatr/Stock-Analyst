def extract_ticker_symbols(input_file, output_file):
    with open(input_file, "r") as file:
        lines = file.readlines()

    ticker_symbols = []
    for line in lines:
        ticker = line.split("|")[0]  # Extract the ticker symbol from the line
        ticker_symbols.append(ticker)

    with open(output_file, "w") as file:
        for ticker in ticker_symbols:
            file.write(ticker + "\n")


# Example usage
input_filename = "nasdaqlisted.txt"
output_filename = "validtickers.txt"

extract_ticker_symbols(input_filename, output_filename)
