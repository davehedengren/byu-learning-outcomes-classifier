import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

BASE_URL = "https://catalog.byu.edu"
HEADERS = {
    'User-Agent': 'BYU Learning Outcomes Scraper (https://github.com/your-repo)' # Please update with your actual repo if public
}


def get_course_urls_from_page(page_num):
    """Fetches course URLs from a single catalog page."""
    page_url = f"{BASE_URL}/courses?page={page_num}"
    print(f"Fetching course list page: {page_url}")
    try:
        response = requests.get(page_url, headers=HEADERS)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        # Save the received HTML to a file for inspection
        output_filename = f"scraped_page_{page_num}.html"
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"Saved received HTML to {output_filename}")
        except IOError as e:
            print(f"Error saving HTML to {output_filename}: {e}")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching {page_url}: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    course_links = []
    # Find all anchor tags within li.course-button whose href starts with '/courses/'
    # Based on example HTML structure where <a> is inside <li class="course-button">.
    course_tags = soup.select('li.course-button a[href^="/courses/"]')

    for link in course_tags:
        href = link.get('href')
        # Ensure href exists and is a valid course link (e.g., /courses/xxxxx-xxx)
        if href and href.startswith('/courses/') and len(href.split('/')) > 2 and href.split('/')[2]:
            # Check if the href contains numbers/hyphens typical of an ID, making it more robust
            course_id_part = href.split('/')[2]
            if any(c.isdigit() for c in course_id_part):
                full_url = BASE_URL + href
                if full_url not in course_links: # Avoid duplicates
                    course_links.append(full_url)
                    # print(f"  Found course URL: {full_url}") # Optional: print found URLs

    if not course_links:
        # Updated the selector in the warning message
        print(f"Warning: No course URLs found on page {page_num}. Check selector ('li.course-button a[href^='/courses/']') or page structure (dynamic loading?).")
    # Remove placeholder comment
    # print("Parsing logic for course URLs not yet implemented.")

    return course_links


if __name__ == "__main__":
    print("Starting scraper...")
    
    # --- Initial Test: Scrape URLs from Page 1 --- 
    test_page = 1
    urls_page_1 = get_course_urls_from_page(test_page)
    
    if urls_page_1:
        print(f"\nSuccessfully fetched {len(urls_page_1)} course URLs from page {test_page}:")
        for url in urls_page_1[:5]: # Print first 5 found URLs
            print(f"- {url}")
        if len(urls_page_1) > 5:
            print("...and more.")
    else:
        print(f"Could not fetch any course URLs from page {test_page}.")

    # --- Next Steps (Placeholder) ---
    # TODO: Implement pagination to get all course URLs
    # TODO: Implement function to scrape individual course pages
    # TODO: Implement data storage to CSV
    
    print("\nScraper finished (initial run).") 