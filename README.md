# BYU Learning Outcomes Aims Analyzer

## Project Goal

The goal of this project is to extract all learning outcomes for every course offered at Brigham Young University (BYU), classify each outcome according to the [Aims of a BYU Education](aims_of_a_BYU_education.md), and provide tools to analyze the distribution of these aims across the university's curriculum.

The BYU Aims are:
1.  Spiritually Strengthening
2.  Intellectually Enlarging
3.  Character Building
4.  Lifelong Learning and Service

(Source: [BYU Mission Goals Alignment](https://sites.lib.byu.edu/internal/naslo/docs/missionGoalsAlignment.pdf) and `aims_of_a_BYU_education.md`)

## Project Workflow

This project follows a multi-step workflow:

1.  **Data Extraction (Scraping):** Gather course information and learning outcomes from the official BYU Course Catalog using web scraping techniques.
2.  **Data Cleaning:** Standardize and clean the raw scraped text data.
3.  **Outcome Classification:** Use an AI model to classify each extracted learning outcome against the four BYU Aims.
4.  **Data Analysis & Visualization:** Explore the classified data using an interactive dashboard.

### Step 1: Data Extraction (`course_scraper.py`)

*   **Process:** The `course_scraper.py` script automates data collection.
    *   It likely uses tools like Selenium to fetch HTML content from individual course pages identified from the main catalog listings.
    *   Downloads HTML pages locally (e.g., into `course_pages/`) for robust parsing.
    *   Uses libraries like BeautifulSoup to parse the saved HTML, extracting: Course Name, Title, Department, College, and Learning Outcomes (title/details).
    *   Assigns sequential IDs to outcomes within a course.
*   **Output:** Saves the raw extracted data into a CSV file (e.g., `learning_outcomes.csv`).
*   **Data Source URLs:**
    *   Main listing (paginated): `https://catalog.byu.edu/courses?page=1`, `https://catalog.byu.edu/courses?page=2`, etc.
    *   Individual course pages (example): `https://catalog.byu.edu/courses/01452-023`

### Step 2: Data Cleaning (`clean_csv.py`)

*   **Process:** The `clean_csv.py` script takes the raw CSV output from the scraper and performs necessary cleaning.
    *   Handles potential text encoding issues (e.g., UTF-8, Latin-1).
    *   Removes extraneous line breaks, decodes HTML entities (e.g., `&amp;`), and standardizes whitespace.
    *   Uses robust CSV parsing to handle potential formatting issues in the raw data.
*   **Output:** Produces a cleaned CSV file (e.g., `data/learning_outcomes_cleaned.csv`) suitable for classification.

### Step 3: Outcome Classification (`classify_outcomes_batch.py`)

*   **Process:** The `classify_outcomes_batch.py` script classifies outcomes using an OpenAI GPT model.
    *   Takes the *cleaned* CSV file as input.
    *   Sends each outcome's text (title + details) along with a detailed system prompt to the OpenAI API. The prompt defines the BYU Aims and requests confidence scores (0-100) for each aim in JSON format.
    *   Processes outcomes incrementally, saving progress frequently and handling potential API errors or rate limits.
*   **Output:** Appends confidence scores (`confidence_Aim_Name`) and a `best_aim` column to the input data, saving the results to a final classified CSV file (e.g., `data/classified_learning_outcomes_cleaned.csv`).
*   **Features:**
    *   Handles missing outcome titles or details.
    *   Designed for batch processing with resumption capabilities.
    *   Supports command-line arguments (`python classify_outcomes_batch.py --help`).

### Step 4: Data Analysis & Visualization (`dashboard.py`)

*   **Process:** An interactive web application built with Streamlit (`dashboard.py`).
*   **Input:** Reads the final *classified and cleaned* data file (e.g., `data/classified_learning_outcomes_cleaned.csv`). Includes logic to harmonize college names and filter out placeholders if necessary.
*   **Features:**
    *   Displays overall aim distribution using interactive pie/donut charts.
    *   Allows filtering data by College and Department.
    *   Shows aim distribution breakdowns by College (when "All" is selected) and by Department (within a selected College) using stacked bar charts.
    *   Provides a detailed, searchable, and sortable table view of the underlying data, including course details, outcome text, best aim classification, and links to the course catalog.
    *   Includes a separate tab to view high-confidence example outcomes for each Aim, respecting the active filters.

## Setup and Usage

1.  **Prerequisites:**
    *   Python 3.x
    *   Git (for cloning the repository)
    *   An OpenAI API Key (for the classification step)

2.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

3.  **Install Dependencies:**
    *   It's recommended to use a virtual environment:
        ```bash
        python -m venv venv
        source venv/bin/activate # On Windows use `venv\Scripts\activate`
        ```
    *   Install required packages:
        ```bash
        pip install -r requirements.txt
        ```
        *(Ensure `requirements.txt` includes `pandas`, `openai`, `python-dotenv`, `streamlit`, `plotly`, `requests`, `beautifulsoup4`, etc.)*

4.  **Configure OpenAI API Key:**
    *   Create a file named `.env` in the project root directory.
    *   Add your OpenAI API key to the `.env` file:
        ```
        OPENAI_API_KEY=your_actual_openai_api_key
        ```

5.  **Run the Workflow:**
    *   **Step 1: Scrape Data:**
        ```bash
        python course_scraper.py --output learning_outcomes_raw.csv
        ```
        *(Adjust output filename as needed. Check script for options.)*
    *   **Step 2: Clean Data:**
        ```bash
        python clean_csv.py --input learning_outcomes_raw.csv --output data/learning_outcomes_cleaned.csv
        ```
        *(Adjust input/output filenames as needed. Check script for options.)*
    *   **Step 3: Classify Outcomes:**
        ```bash
        python classify_outcomes_batch.py --input data/learning_outcomes_cleaned.csv --output data/classified_learning_outcomes_cleaned.csv
        ```
        *(Adjust input/output filenames. This might overwrite the cleaned file, or use a different output name depending on the script's goal. Use `--help` for details.)*
    *   **Step 4: Analyze Results:**
        ```bash
        streamlit run dashboard.py
        ```
        *(Ensure the dashboard (`DATA_FILE` constant) points to the final classified file, e.g., `data/classified_learning_outcomes_cleaned.csv`)*

## Future Enhancements

*   Propose candidate learning objectives for missing Aims based on course information (syllabus, etc.).
*   Integrate syllabus data scraping and analysis.
*   Refine the classification prompt or model for higher accuracy.
*   Develop more advanced analytics or comparison features in the dashboard.