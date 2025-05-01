import time
import os
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, SessionNotCreatedException
import urllib3.exceptions

BASE_URL = "https://catalog.byu.edu"
CATALOG_PAGES_DIR = "catalogue_pages"
START_PAGE = 70
MAX_PAGES = 297
URL_FILE_PATH = "course_urls.txt"
MAX_RETRIES = 3

# Browser refresh settings - restart browser every X pages to prevent crashes
PAGES_BEFORE_RESTART = 10

def setup_driver(reload=False):
    """Set up and return a configured Chrome webdriver"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    
    # Reduce memory usage
    options.add_argument("--js-flags=--expose-gc")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-background-timer-throttling")
    
    # Increase page load timeout
    options.page_load_strategy = 'normal'
    
    # Add random user-agent to avoid detection
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)} BYU Learning Outcomes Scraper")
    
    try:
        # Create a new driver
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)  # Increase timeout to 30 seconds
        
        if reload:
            print("Restarting Chrome driver...")
        
        return driver
    except Exception as e:
        print(f"Error creating Chrome driver: {e}")
        # Sleep and try again
        time.sleep(10)
        return webdriver.Chrome(options=options)

def restart_browser(driver):
    """Safely quit the existing driver and create a new one"""
    try:
        if driver:
            driver.quit()
    except:
        pass  # Ignore any errors during quit
    
    print("Doing a complete browser restart...")
    time.sleep(5)  # Wait for resources to be freed
    return setup_driver(reload=True)

def get_existing_urls():
    """Get already scraped URLs from the file to avoid duplicates"""
    if os.path.exists(URL_FILE_PATH):
        with open(URL_FILE_PATH, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def append_urls_to_file(urls):
    """Append new URLs to the file"""
    if not urls:
        print("No URLs to save")
        return
        
    existing_urls = get_existing_urls()
    new_urls = [url for url in urls if url not in existing_urls]
    
    if new_urls:
        with open(URL_FILE_PATH, 'a', encoding='utf-8') as f:
            for url in new_urls:
                f.write(f"{url}\n")
        print(f"Saved {len(new_urls)} new URLs to {URL_FILE_PATH}")
    else:
        print("No new URLs to save (all were duplicates)")

def get_course_urls_from_page(driver, page_num, retry_count=0):
    """Fetches course URLs from a single catalog page using Selenium with retry logic."""
    page_url = f"{BASE_URL}/courses?page={page_num}"
    print(f"Fetching course list page: {page_url} (Attempt {retry_count + 1}/{MAX_RETRIES + 1})")
    
    try:
        driver.get(page_url)
        
        # Wait for the course list to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li.course-button a"))
        )
        
        # Create directory if it doesn't exist
        if not os.path.exists(CATALOG_PAGES_DIR):
            os.makedirs(CATALOG_PAGES_DIR)
            print(f"Created directory: {CATALOG_PAGES_DIR}")
        
        # Save the page source for archiving
        file_path = os.path.join(CATALOG_PAGES_DIR, f"page_{page_num}.html")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print(f"Saved page source to {file_path}")
        
        # Find all course links
        course_links = []
        link_elements = driver.find_elements(By.CSS_SELECTOR, "li.course-button a")
        
        for link in link_elements:
            href = link.get_attribute('href')
            if href and "/courses/" in href:
                course_links.append(href)
        
        print(f"Found {len(course_links)} course URLs on page {page_num}")
        return course_links
        
    except (TimeoutException, WebDriverException, SessionNotCreatedException) as e:
        print(f"Error fetching {page_url}: {e}")
        
        # If we have retries left, wait with exponential backoff and try again
        if retry_count < MAX_RETRIES:
            # Exponential backoff: 5s, 15s, 45s
            wait_time = 5 * (3 ** retry_count)
            print(f"Waiting {wait_time} seconds before retrying...")
            time.sleep(wait_time)
            
            # Restart the driver to clear any state
            driver = restart_browser(driver)
            
            # Recursive call with incremented retry counter
            return get_course_urls_from_page(driver, page_num, retry_count + 1)
        else:
            print(f"Max retries exceeded for page {page_num}. Moving on...")
            return []
    except (urllib3.exceptions.MaxRetryError, urllib3.exceptions.NewConnectionError, ConnectionRefusedError) as e:
        print(f"Connection error fetching {page_url}: {e}")
        
        # These are connection errors that require a complete browser restart
        if retry_count < MAX_RETRIES:
            wait_time = 10 * (2 ** retry_count)  # Longer wait for connection issues
            print(f"Connection issue detected. Waiting {wait_time} seconds before full browser restart...")
            time.sleep(wait_time)
            
            # Force a complete browser restart
            driver = restart_browser(driver)
            
            return get_course_urls_from_page(driver, page_num, retry_count + 1)
        else:
            print(f"Max retries exceeded for page {page_num}. Moving on...")
            return []
    except Exception as e:
        print(f"Unexpected error fetching {page_url}: {e}")
        # For any other errors, attempt a restart if within retry count
        if retry_count < MAX_RETRIES:
            print(f"Trying again after 15 seconds...")
            time.sleep(15)
            driver = restart_browser(driver)
            return get_course_urls_from_page(driver, page_num, retry_count + 1)
        return []

def get_last_scraped_page():
    """Determine the last successfully scraped page from saved files"""
    if not os.path.exists(CATALOG_PAGES_DIR):
        return 0
        
    # Check for the highest page number in the directory
    page_files = [f for f in os.listdir(CATALOG_PAGES_DIR) if f.startswith('page_') and f.endswith('.html')]
    
    if not page_files:
        return 0
        
    # Extract page numbers from filenames
    page_numbers = []
    for filename in page_files:
        try:
            page_number = int(filename.replace('page_', '').replace('.html', ''))
            page_numbers.append(page_number)
        except ValueError:
            continue
            
    return max(page_numbers) if page_numbers else 0

def get_all_course_urls(driver, start_page=START_PAGE, end_page=MAX_PAGES):
    """Gets course URLs from all catalog pages in the specified range."""
    all_urls = []
    pages_since_restart = 0
    
    for page_num in range(start_page, end_page + 1):
        # Check if we need to restart the browser periodically
        if pages_since_restart >= PAGES_BEFORE_RESTART:
            print(f"Performed {pages_since_restart} page scrapes. Doing routine browser restart...")
            driver = restart_browser(driver)
            pages_since_restart = 0
        
        urls = get_course_urls_from_page(driver, page_num)
        
        # Save URLs after each page to avoid losing data if script fails
        append_urls_to_file(urls)
        all_urls.extend(urls)
        pages_since_restart += 1
        
        # Be polite to the server - random delay between requests
        if page_num < end_page:
            # Random delay between 1-3 seconds
            delay = random.uniform(1, 3)
            print(f"Waiting {delay:.2f} seconds before next request...")
            time.sleep(delay)
    
    return all_urls

def main():
    print("Starting scraper with Selenium...")
    
    # Determine where to start or resume from
    last_page = get_last_scraped_page()
    end_page = MAX_PAGES # Use the configured MAX_PAGES

    if last_page >= end_page:
        print(f"Last scraped page ({last_page}) is already >= MAX_PAGES ({end_page}). Nothing new to scrape within the limit.")
        start_page = end_page + 1 # Ensure the range is empty
    elif last_page > 0:
        resume_from = last_page + 1
        print(f"Resuming scrape from page {resume_from} (last successful page was {last_page})")
        start_page = resume_from
    else:
        print("Starting new scrape from page 1")
        start_page = START_PAGE
    
    # Check if start_page exceeds end_page before setting up driver
    if start_page > end_page:
        print(f"Start page ({start_page}) is greater than end page ({end_page}). No pages to scrape.")
        total_saved = len(get_existing_urls())
        print(f"Total unique course URLs saved: {total_saved}")
        print("\nScraper finished.")
        return # Exit early

    driver = setup_driver()
    
    try:
        print(f"Scraping pages {start_page} to {end_page}...")
        urls = get_all_course_urls(driver, start_page, end_page)
        
        print(f"\nSuccessfully found {len(urls)} total course URLs from pages {start_page}-{end_page}")
        
        # Get total count of all URLs saved so far
        total_saved = len(get_existing_urls())
        print(f"Total unique course URLs saved: {total_saved}")
            
    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Progress has been saved.")
    finally:
        try:
            driver.quit()
        except:
            pass  # Ignore errors during quit
        
    print("\nScraper finished.")

if __name__ == "__main__":
    main() 