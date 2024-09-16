import requests
import json
import discord
from discord.ext import commands

# Google Sheets setup
spreadsheet_id = '1OdVWhN9oaLe8YRzcZYlvp1HtcjozDhUsYLKKxd30UJs'
sheet_name = 'Results'
sheet_range = 'A:W'
full_url = f'google_sheet_link'

def fetch_sheet_data():
    response = requests.get(full_url)
    response_text = response.text[47:-2]  # Clean the response to get valid JSON
    data = json.loads(response_text)
    
    # Extract rows and headers
    headers = [header['label'] for header in data['table']['cols']]
    rows = data['table']['rows']
    
    records = []
    for row in rows:
        record = {headers[i]: row['c'][i]['v'] if row['c'][i] else '' for i in range(len(headers))}
        records.append(record)
    
    return records

def fetch_unqiue_sectors():
    response = requests.get(full_url)
    response_text = response.text[47:-2]
    data = json.loads(response_text)

    # Extract sectors
    sectors = set()
    for row in data['table']['rows']:
        try:
            sector = row['c'][7]['v']
            sectors.add(sector)
        except (IndexError, KeyError, TypeError):
            # Handle or log the error if necessary
            pass    
    return sectors

def format_market_cap(market_cap: float) -> str:
    if market_cap >= 1_000_000_000:
        formatted = f"${market_cap / 1_000_000_000:.2f}B"
    elif market_cap >= 1_000_000:
        formatted = f"${market_cap / 1_000_000:.2f}M"
    elif market_cap >= 1_000:
        formatted = f"${market_cap / 1_000:.2f}K"
    else:
        formatted = f"${market_cap:.2f}"
    return formatted

def decode_market_cap(market_cap) -> float:
    if isinstance(market_cap, float) or isinstance(market_cap, int):
        market_cap = str(market_cap)  # Convert to string if it's float or int

    if market_cap[-1].lower() == 'b':
        decoded = float(market_cap[:-1]) * 1e9
    elif market_cap[-1].lower() == 'm':
        decoded = float(market_cap[:-1]) * 1e6
    elif market_cap[-1].lower() == 'k':
        decoded = float(market_cap[:-1]) * 1e3
    else:
        try:
            decoded = float(market_cap)
        except ValueError:
            decoded = 0.0  # Return a default value or handle the error case
    return decoded

def filter_displayed_value(value, default='N/A'):
    if value == '' or value is None or value == '#NAME?' or (isinstance(value, str) and  '$' in value and value.count('0') > 2):
        return default
    
    return value

def format_date(date):
    # Extract the year, month, and day
    year = date[5:9]
    month = date[10:11]
    day = date[12:13]

    # Define month names
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

    # Convert month and day to integers
    month = int(month)
    day = int(day)

    # Format the date
    return f"{months[month]} {day:02}, {year}"

def format_average_change(change):
    change = change * 100
    if str(change) == '0':
        return change
    if not "-" in str(change):
        return f"+{change}%"
    return f"{change}%"

# Discord Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!sc ', intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="!sc help"))

# Custom help command
@bot.command(name='help')
async def help_command(ctx):
    response = (
        "```\n"
        "StockChecker Bot Commands\n"
        "\n"
        "!sc stock [query] - Fetch stock data for a company\n"
        "!sc sectors - Fetch unique sectors\n"
        "!sc highest [top] [sector] [market_cap_min] - Fetch N top stocks by sector and market cap\n"
        "\n"
        "Example Usage:\n"
        "!sc stock AAPL\n"
        "!sc stock Apple Inc.\n"
        "!sc sectors\n"
        "!sc highest 5 Technology 500M\n"
        "```"
    )
    await ctx.send(response)

@bot.command(name='stock')
async def fetch_stock(ctx, * ,query):
    processing_response = await ctx.send(f"Fetching stock data for {query}...")
    data = fetch_sheet_data()

    # Search for the company
    for row in data:
        if row['Ticker'].lower() == query.lower() or query.lower() in row['Company Name'].lower():
            response = (
                f"**{filter_displayed_value(row['Company Name'])} ({filter_displayed_value(row['Ticker'])})**\n"
                f"Price: ${row['Price']}\n"
                f"Market Cap: {str(filter_displayed_value(format_market_cap(float(row['Market Cap']))))}\n"
                f"Industry: {filter_displayed_value(row['Industry'])}\n"
                f"BarChart Analysis: {row['BarChart Rec']}\n"
                f"Benzinga Analysis: {row['Benzinga Rec']}\n"
                f"MarketBeat Analysis: {row['MarketBeat Rec']}\n"
                f"Zacks Analysis: {row['Zacks Rec']}\n"
                f"StockTargetAdvisor Analysis: {row['StockTargetAdvisor Updated Rec']}\n"
                f"StockChecker Bot Analysis: {row['StockChecker Rec']}\n"
                f"**Weighted Average Analysis Score: {round(row['Average Value'],2)}/5**\n"
                f"**Average Change: {format_average_change(row['Average Change'])}%**\n"
                f"Last Updated: {format_date(row['Date Updated'])}"
            )  
            await processing_response.delete()
            await ctx.send(response)
            return
    
    await ctx.send("Company not found!")

@bot.command(name='sectors')
async def fetch_sectors(ctx):
    sectors = fetch_unqiue_sectors()
    sectors.remove('N/A')
    response = '\n'.join(sectors)
    await ctx.send(f"**Unique Sectors:**\n{response}")

@bot.command(name='highest')
async def fetch_best(ctx, top = 5, sector = 'All', market_cap_min = '0'):
    processing_response = await ctx.send(f"Fetching top {top} stocks with sector: {sector} and market cap >= {market_cap_min}...")
    data = fetch_sheet_data()
    
    # Filter by sector
    if sector != 'All':
        data = [row for row in data if row['Sector'].lower() == sector.lower()]
    
    # Filter by market cap
    data = [row for row in data if filter_displayed_value(row['Market Cap'], 0.0) >= decode_market_cap(market_cap_min)]

    # Sort by Average Value Rec
    data.sort(key=lambda x: x['Average Value'], reverse=True)
    
    # Fetch top stocks
    top = min(top, len(data))
    response = ''
    for i in range(top):
        row = data[i]
        response += (
            f"No. {i + 1}\n"
            f"**{filter_displayed_value(row['Company Name'])} ({filter_displayed_value(row['Ticker'])})**\n"
            f"Price: ${filter_displayed_value(row['Price'])} Last Updated: {format_date(row['Date Updated'])}\n"
            f"Market Cap: {str(filter_displayed_value(format_market_cap(float(row['Market Cap']))))}\n"
            f"Industry: {row['Industry']}\n"
            f"** Weighted Average Analysis Score: {round(row['Average Value'],2)}/5**\n"
            f"Average Change: **{format_average_change(row['Average Change'])}%**\n"
            "\n"
        )
    
    await processing_response.delete()
    await ctx.send(response)


@bot.command(name='change')
async def fetch_best(ctx, top = 5, sector = 'All', market_cap_min = '0'):
    processing_response = await ctx.send(f"Fetching top {top} stocks with sector: {sector} and market cap >= {market_cap_min}...")
    data = fetch_sheet_data()
    
    # Filter by sector
    if sector != 'All':
        data = [row for row in data if row['Sector'].lower() == sector.lower()]
    
    # Filter by market cap
    data = [row for row in data if filter_displayed_value(row['Market Cap'], 0.0) >= decode_market_cap(market_cap_min)]

    # Sort by Average Value Rec
    data.sort(key=lambda x: x['Average Change'], reverse=True)
    
    # Fetch top stocks
    top = min(top, len(data))
    response = ''
    for i in range(top):
        row = data[i]
        response += (
            f"No. {i + 1}\n"
            f"**{filter_displayed_value(row['Company Name'])} ({filter_displayed_value(row['Ticker'])})**\n"
            f"Price: ${filter_displayed_value(row['Price'])} Last Updated: {format_date(row['Date Updated'])}\n"
            f"Market Cap: {str(filter_displayed_value(format_market_cap(float(row['Market Cap']))))}\n"
            f"Industry: {row['Industry']}\n"
            f"Weighted Average Analysis Score: **{round(row['Average Value'],2)}/5**\n"
            f"**Average Change: {format_average_change(row['Average Change'])}%**\n"
            "\n"
        )
    
    await processing_response.delete()
    await ctx.send(response)

# Run the bot
bot.run('TOKEN')