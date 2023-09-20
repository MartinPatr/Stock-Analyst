from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datacollection import check_error
from detailed_analysis import update_score_financials, update_score_analysis
import time

# Set up the driver
options = Options()
options.add_argument('--disable-browser-side-navigation')
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('window-size=1920x1080')
options.add_argument("--disable-extensions")
driver = webdriver.Chrome(options=options)
ChromeOptions = webdriver.ChromeOptions()


# Gets the financials from the financials page
def get_financials(data,url):    
    
    # Get the html from the page
    driver.get(url)

    # Wait for the page to load and close the popup
    close_popup()

    # Get the html from the page
    html = driver.page_source
    # Check if the page has loaded successfully
    if "403 Forbidden" in html:
        check_error(html)
        html = driver.page_source

    soup = BeautifulSoup(html, 'html.parser')
    financial_elements = soup.find_all('tr', {'class': 'table__row'})

    # Attempt to
    try:
        # Get the position of the net income growth and eps growth
        for i, element in enumerate(financial_elements):
            element = element.find_all('td')
            try: 
                element = element[0].find_all('div')
                if element[1].text == "Net Income Growth":
                    niIndex = i
                if element[1].text == "EPS (Diluted) Growth":
                    epsIndex = i
            except:
                pass

        # Get the position of the profit margin, net income %, and eps %
        niPosition = len(financial_elements[niIndex].find_all('td')) - 2    
        epsPosition = len(financial_elements[epsIndex].find_all('td')) - 2

        data["Net Income %"] = financial_elements[niIndex].find_all('td')[niPosition].text.replace('%','').replace(',', '')
        data["EPS %"] = financial_elements[epsIndex].find_all('td')[epsPosition].text.replace('%','').replace(',', '')
        # If any of the values are NA, set the score to 0
        if data["Net Income %"] == "-" or data["EPS %"] == "-":
            print("Failed to update score as one of the values is NA")
            data['Score'] = 0
            return
        update_score_financials(data)
    except Exception as e:
        print("Failed to update score based on financials: ", e)
        data['Score'] = round(data['Score'] * 0.80,2)

    # Get the analyst estimates
    get_analyst_estimates(data)



# Gets the analyst estimates from the analyst estimates page
def get_analyst_estimates(data):
    # Go to the analyst estimates page
    try:
        button = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH,"//a[text()='Analyst Estimates']")))
        button.click()
    except Exception as e:
        print(e)
        try:
            click_button(1)
        except Exception as e:
            print(e)
            print("Could not find analyst estimates button")
            return
        
   
    # Wait for the page to load and close the popup
    close_popup()
    
    # Get the html from the page
    html = driver.page_source
    #Use BeautifulSoup to parse the html
    soup = BeautifulSoup(html, 'html.parser')
    ae_elements = soup.find_all('td', {'class': 'w25'})
    try:
        data['Recommendation'] = ae_elements[0].text
        data['Target Price'] = ae_elements[1].text
        update_score_analysis(data)
    except Exception as e:
        print("Failed to update score based on analyst estimates: ", e)
        data['Score'] = round(data['Score'] * 0.80,2)


# Close the popup window
def close_popup():
    # Wait to see if the popup appears
    try:
        button = WebDriverWait(driver, 2.5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'close-btn')))
        button.click()
        print("Closed popup")
    except:
        pass

# Try to click the button and check if it worked and if not, try again recursively
def click_button(attempts, max_attempts = 4, by = By.XPATH, value = "//a[text()='Analyst Estimates']"):
    print("Attempting to click button: ", attempts, " times")
    time.sleep(1)
    # If we have tried 3 times, raise an exception
    if attempts >= max_attempts:
        raise Exception("Reached maximum number of attempts")
    try:
        button = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH,"//a[text()='Analyst Estimates']")))
        button.click()
    except:
        click_button(attempts + 1)
        

# Close the driver
def close_driver():
    driver.close()

