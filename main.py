import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver.common.alert import Alert


GOOGLE_FORM = "https://docs.google.com/forms/d/e/1FAIpQLSdX59MCUnFldjMy8dmHtGFdgbAvenAoAszJnNF_Mt97Rewl6w/viewform?usp=sf_link"
ZILLOW_RENTALS = "https://appbrewery.github.io/Zillow-Clone/"

# XPaths for the Google Form fields
xpath_address_field = "//*[@id='mG61Hd']/div[2]/div/div[2]/div[1]/div/div/div[2]/div/div[1]/div/div[1]/input"
xpath_price_field = "//*[@id='mG61Hd']/div[2]/div/div[2]/div[2]/div/div/div[2]/div/div[1]/div/div[1]/input"
xpath_link_field = "//*[@id='mG61Hd']/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[1]/div/div[1]/input"
xpath_sq_ft_field = "//*[@id='mG61Hd']/div[2]/div/div[2]/div[5]/div/div/div[2]/div/div[1]/div/div[1]/input"
submit_xpath = "//*[@id='mG61Hd']/div[2]/div/div[3]/div[1]/div[1]/div/span/span"
redirect_xpath = "/html/body/div[1]/div[2]/div[1]/div/div[4]/a"
radio_buttons_xpaths = {
    '1': "//*[@id='i17']/div[3]/div",
    '2': "//*[@id='i20']/div[3]/div",
    '3': "//*[@id='i23']/div[3]/div",
    '4': "//*[@id='i26']/div[3]/div",
    '5+': "//*[@id='i29']/div[3]/div"
}

def scrape_rentals():
    """Scrapes rental listings from Zillow and returns a dictionary with the data."""
    website_html = requests.get(ZILLOW_RENTALS).text
    soup = BeautifulSoup(website_html, "html.parser")

    rental_listings = soup.select(".StyledPropertyCardDataWrapper")
    addresses = [listing.find("a").getText().strip() for listing in rental_listings]
    links = [listing.find("a").get("href") for listing in rental_listings]
    prices = [listing.select_one(".StyledPropertyCardDataArea-fDSTNn span").getText().split("+")[0].split("/mo")[0]
              for listing in rental_listings]

    beds = []
    for listing in rental_listings:
        try:
            bed_info = listing.select_one(".StyledPropertyCardHomeDetailsList").getText().split("bd")[0].strip()
            beds.append(bed_info)
        except IndexError:
            beds.append('--')

    footage = []
    for listing in rental_listings:
        try:
            sqft = listing.select_one(".StyledPropertyCardDataArea-dbDWjx ul").getText().split("ba\n")[1].split(" ")[0]
            footage.append(sqft)
        except IndexError:
            footage.append('--')

    rentals_dict = {
        link: [address, price, bed, footage] for address, price, bed, footage, link in
        zip(addresses, prices, beds, footage, links)
    }
    return rentals_dict


def send_data_to_google_sheet(driver, link, listing_info):
    """Sends individual listings to Google Form with Selenium."""
    try:
        address_field = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_address_field)))
        address_field.send_keys(listing_info[0])

        price_field = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_price_field)))
        price_field.send_keys(listing_info[1])

        link_field = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_link_field)))
        link_field.send_keys(link)

        # Check if the key for the radio button exists before accessing it
        radio_button_xpath = radio_buttons_xpaths.get(listing_info[2])
        if radio_button_xpath:
            radio_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, radio_button_xpath)))
            radio_button.click()
        else:
            print(f"Missing bed info for listing: {link}")

        sq_ft_field = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_sq_ft_field)))
        sq_ft_field.send_keys(listing_info[3])

        submit_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, submit_xpath)))
        submit_button.click()

        redirect_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, redirect_xpath)))
        redirect_button.click()
        time.sleep(2)

    except Exception as e:
        print(f"Error submitting data for {link}: {e}")
        print(f"Exception type: {type(e).__name__}")
        try:
            alert = Alert(driver)
            alert.accept()
            print(f"Alert accepted for URL: {link}")
        except UnexpectedAlertPresentException:
            print(f"No alert found for URL: {link}")


def run_bot():
    # Scrape rental data
    rentals_dict = scrape_rentals()
    print(rentals_dict)

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(GOOGLE_FORM)

    # Counter for successful submissions
    count = 0

    # Send data to Google Form
    for link, listing_info in rentals_dict.items():
        send_data_to_google_sheet(driver, link, listing_info)
        count += 1

        driver.refresh()

    driver.quit()

    print(f"Total number of entries made: {count}")


if __name__ == "__main__":
    run_bot()
