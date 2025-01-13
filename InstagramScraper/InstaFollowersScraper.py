import os
import csv
import json
import pytz
import pickle
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv("insta_secret_keys.env")


class InstagramScraper:
    HEADERS = {
        "accept": "*/*"
    }
    COOKIES_FILE = "InstagramCookies.pkl"
    SCRAPE_DATE_TIME = datetime.now(tz=pytz.utc).strftime("%d%m%Y_%H%M")

    def __init__(self):
        self.base_url = "https://www.instagram.com/"
        self.followers_api = self.get_api_key()
        self.credentials = self.get_login_credentials()
        self.driver = self.setup_driver()
        self.followers_data = []

    def get_login_credentials(self):
        """Load login credentials from .env file."""
        username = os.getenv("INSTAGRAM_USERNAME")
        password = os.getenv("INSTAGRAM_PASSWORD")
        return username, password

    def get_api_key(self):
        api_key = os.getenv("API_KEY")
        return api_key

    def setup_driver(self):
        """Set up the Selenium WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--headless')

        driver = webdriver.Remote(
            command_executor="http://localhost:4444/wd/hub",
            options=chrome_options
        )
        return driver

    def save_cookies(self):
        """Save cookies to a file."""
        with open(self.COOKIES_FILE, "wb") as file:
            pickle.dump(self.driver.get_cookies(), file)
        logger.info("Cookies saved successfully!")

    def load_cookies(self):
        """Load cookies from a file."""
        if os.path.exists(self.COOKIES_FILE):
            self.driver.get(self.base_url)
            with open(self.COOKIES_FILE, "rb") as file:
                cookies = pickle.load(file)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
            logger.info("Cookies loaded successfully!")
            return True
        else:
            logger.error("No cookies file found. Logging in manually is required.")
            return False

    def login(self):
        """Log in to Instagram."""
        try:
            self.driver.get(self.base_url)

            # Wait for login fields to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )

            username_field = self.driver.find_element(By.NAME, "username")
            password_field = self.driver.find_element(By.NAME, "password")
            username, password = self.credentials

            username_field.send_keys(username)
            password_field.send_keys(password)

            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()

            # Wait for the main page to load after login
            profile_link = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'm_hamza131')]"))
            )
            get_profile_link = profile_link.get_attribute('href')

            if get_profile_link:
                logger.info("Login successful!")
                self.save_cookies()
                self.scrape(get_profile_link)
            else:
                logger.error("Login verification failed. Profile link not found on the page.")

        except Exception as e:
            logger.error("An error occurred during login:", e)

    def convert_cookies_to_dict(self, cookies):
        """Convert a list of cookies to a dictionary format suitable for requests."""
        cookies_dict = {}
        for cookie in cookies:
            cookies_dict[cookie['name']] = cookie['value']
        return cookies_dict

    def scrape(self, profile_url):
        """Scrape Followers"""
        try:

            next_api_id = ""
            while True:

                user_agent = self.driver.execute_script("return navigator.userAgent;")
                cookies_dict = self.convert_cookies_to_dict(self.driver.get_cookies())

                url = self.followers_api.format(
                    next_api_id=next_api_id
                ).strip()

                self.HEADERS['user-agent'] = user_agent
                response = requests.get(
                    url=url,
                    cookies=cookies_dict,
                    headers=self.HEADERS
                )
                json_data = json.loads(response.content)
                next_api_id_available = json_data.get("next_max_id")
                next_api_id = next_api_id_available
                for item in json_data['users']:
                    user_id = item.get("id")
                    username = item.get("username")
                    profile_fullname = item.get("full_name")
                    private_account = item.get("is_private")
                    profile_pic_url = item.get("profile_pic_url")
                    is_verified = item.get("is_verified")

                    new_dict = {
                        "UserID":user_id,
                        "UserName":username,
                        "ProfileFullName":profile_fullname,
                        "PrivateAccount":private_account,
                        "ProfileImage":profile_pic_url,
                        "Is_Verified":is_verified
                    }
                    self.followers_data.append(new_dict)

                if not next_api_id_available:
                    break

            logger.info(f"Scraped All the Followers data successfully! OF Profile: {profile_url}")
            logger.info(self.followers_data)
            self.save_to_csv()
            logger.info("Data Saved in File Successfully!")

        except Exception as e:
            logger.error("An error occurred during scraping:", e)

    def save_to_csv(self):
        """
         This function saves all the scraped category data into a CSV file.
        """
        with open(f'Scraped_data{self.SCRAPE_DATE_TIME}.csv', 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                "UserID", "UserName", "ProfileFullName", "PrivateAccount", "ProfileImage", "Is_Verified"
            ])
            for data in self.followers_data:
                writer.writerow(data.values())

    def run(self):
        """Main script execution."""
        try:
            if self.load_cookies():

                self.driver.get(self.base_url)

                profile_link = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'm_hamza131')]"))
                )
                get_profile_link = profile_link.get_attribute('href')
                if get_profile_link:
                    self.scrape(get_profile_link)
                else:
                    logger.error("Session restoration failed. Profile link not found on the page after loading cookies.")

            else:
                self.login()

        finally:
            self.driver.quit()


if __name__ == "__main__":
    scraper = InstagramScraper()
    scraper.run()
