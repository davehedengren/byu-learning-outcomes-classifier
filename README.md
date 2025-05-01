# BYU Learning Outcomes Extractor

## Project Goal

The goal of this project is to extract all learning outcomes for every course offered at Brigham Young University (BYU). For each course, the scraper should also extract the course name, department, and college.

Once the full dataset is collected, it can potentially be used with an LLM classifier to identify which of the BYU Aims are associated with each stated learning outcome.

The BYU Aims (expected outcomes of a BYU education) are:
1.  Spiritually Strengthening
2.  Intellectually Enlarging
3.  Character Building
4.  Lifelong Learning and Service.

(Source: [BYU Mission Goals Alignment](https://sites.lib.byu.edu/internal/naslo/docs/missionGoalsAlignment.pdf))

## Data Source

All course information is available on the BYU Course Catalog website:
- Main listing (paginated): [https://catalog.byu.edu/courses?page=1](https://catalog.byu.edu/courses?page=1), [https://catalog.byu.edu/courses?page=2](https://catalog.byu.edu/courses?page=2), etc.
- Individual course pages (example): [https://catalog.byu.edu/courses/01452-023](https://catalog.byu.edu/courses/01452-023) (CMLIT 420R)

## Expected Output Format

The scraper should produce a CSV file (`learning_outcomes.csv`) with the following columns:

`course_name, course_url, course_title, department, college, learning_outcome_id, learning_outcome_title, learning_outcome_details`

Each row will represent a single learning outcome for a specific course. If a course has multiple learning outcomes, it will result in multiple rows in the CSV.

**Example Rows (from CMLIT 420R):**

```csv
course_name,course_url,course_title,department,college,learning_outcome_id,learning_outcome_title,learning_outcome_details
CMLIT 420R,https://catalog.byu.edu/courses/01452-023,12th-Century Renaissance,Comparative Arts and Letters,College of Humanities,1,Literary Periodization,"Articulate with considerable sophistication basic concepts and issues in literary periodization, showing an ability to deal with problems, texts, and figures specific to the European twelfth century and Middle Ages more broadly."
CMLIT 420R,https://catalog.byu.edu/courses/01452-023,12th-Century Renaissance,Comparative Arts and Letters,College of Humanities,2,Research and Writing,"Conduct thorough research into a problem specific to the period in question -- the European 12th century -- and write in a professional, scholarly manner about it."
CMLIT 420R,https://catalog.byu.edu/courses/01452-023,12th-Century Renaissance,Comparative Arts and Letters,College of Humanities,3,"Multilingual Study, Research, and Writing","Show an ability to read, study, research, and write about literary texts from the European 12th century in at least two languages."
```

## Implementation

### Web Scraper (Completed)

-   [x] **Setup Project:** Initialize Python environment (`venv`), install necessary libraries (`selenium`, `pandas`, `beautifulsoup4`, `lxml`).
-   [x] **Scrape Course List:** (Handled by providing `course_urls.txt`)
    -   *(Assumes `course_urls.txt` is generated separately or provided)*
-   [x] **Scrape Individual Course Page & Save HTML:**
    -   Function takes a course URL.
    -   Uses Selenium to fetch HTML and save locally (`course_pages/`).
-   [x] **Extract Data from HTML:**
    -   Function takes local HTML content.
    -   Uses BeautifulSoup to parse HTML.
    -   Extracts Course Name (Code), Course Title, Department, College.
    -   Extracts Learning Outcomes (handling different structures).
    -   Assigns sequential `learning_outcome_id`.
    -   Handles cases with no outcomes.
-   [x] **Data Storage:**
    -   Stores extracted data.
    -   Uses `pandas` to write/append to `learning_outcomes.csv`.
-   [x] **Error Handling & Politeness:**
    -   Basic error handling for download/parsing.
    -   Delay between download requests.
    -   User-agent randomization.
-   [x] **Refinement & Testing:**
    -   Iteratively tested and refined extraction logic.

### CSV Cleaning (Completed)

-   [x] **Implement Robust CSV Cleaning:**
    -   Created `clean_csv.py` to handle problematic CSV files.
    -   Supports multiple encodings (UTF-8, Latin-1, etc.) with automatic fallback.
    -   Removes line breaks, HTML entities, and cleans text fields.
    -   Implements progressive parsing fallbacks for malformed CSV files.
    -   Handles quoted fields and multiline entries.
    -   Provides detailed diagnostics during processing.
-   [x] **Command-line Interface:**
    -   Script accepts input and output file parameters
    -   Example: `python clean_csv.py --input raw_data.csv --output cleaned_data.csv`
-   [x] **Testing:**
    -   Successfully tested on large datasets (~8,000 rows)
    -   Successfully handles various formatting issues

### Learning Outcome Classification (Completed)

-   [x] **Setup OpenAI API Access:**
    -   Installed `openai` library and `python-dotenv` library
    -   Created secure API key loading mechanism from `.env` file
-   [x] **Read Scraped Data:**
    -   Created `classify_outcomes.py` script that reads CSV input
    -   Added support for resuming interrupted classifications
-   [x] **Define Classification Function:**
    -   Implemented a function that analyzes learning outcome content
    -   Created detailed system prompt with comprehensive BYU Aims descriptions
    -   Configured OpenAI API to return structured JSON with confidence scores
    -   Added error handling for failed API calls
-   [x] **Process CSV and Classify:**
    -   Script processes each row incrementally with configurable save frequency
    -   Handles missing data gracefully
    -   Includes progress tracking and informative logging
    -   Adds 1-second delay between API calls to manage rate limits
-   [x] **Store Classification Results:**
    -   Adds confidence scores (0-100) for each of the four BYU Aims
    -   Identifies and records the highest confidence aim
    -   Saves to specified output CSV file incrementally
-   [x] **Command-line Interface:**
    -   Script accepts input, output, and save frequency parameters
    -   Example: `python classify_outcomes.py --input learning_outcomes.csv --output classified_outcomes.csv --save-frequency 5`
-   [x] **Refinement & Cost Management:**
    -   Tested with small subsets before full dataset
    -   Added incremental saving to prevent data loss
    -   Skips already processed items when resuming

## Next Steps

Future enhancements could include:

1. **Analytics Dashboard:** Create visualizations of classification results to identify patterns across departments and colleges.
2. **Validation Tools:** Develop tools to evaluate classification accuracy and refine the model.
3. **Integration with BYU Systems:** Explore how the classification data could be integrated with BYU systems to help faculty align courses with university aims.
4. **Improved Classification Algorithm:** Experiment with different prompts or models to improve classification accuracy.