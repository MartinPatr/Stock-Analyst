import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Define the credentials to access the Google Sheets API
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# Open the Google Sheet
sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1osQvs0ijyp2lpjnUqOC5f3mw2TjKqMH51xoBI__L__c/edit?usp=sharing').sheet1

# Define the column number to copy (replace A with the actual column letter)
column_number = 1

# Get the contents of the column as a list
column_contents = sheet.col_values(column_number)

# Write each item to a separate line in a text file
with open('tickets.txt', 'w') as f:
    f.write('\n'.join(column_contents))