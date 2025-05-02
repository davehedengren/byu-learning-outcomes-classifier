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

1.  **Data Extraction (Scraping):** Gather course information and learning outcomes from the official BYU Course Catalog.
2.  **Outcome Classification:** Use an AI model to classify each extracted learning outcome against the four BYU Aims.
3.  **Data Analysis & Visualization:** Explore the classified data using an interactive dashboard.

### Step 1: Data Extraction (`course_scraper.py`)

*   **Process:** The `course_scraper.py` script automates the collection of data from the BYU Course Catalog website.
    *   It first identifies all course pages from the main catalog listings (e.g., `https://catalog.byu.edu/courses?page=1`).
    *   It then visits each individual course page (e.g., `https://catalog.byu.edu/courses/01452-023`) to extract:
        *   Course Name (e.g., CMLIT 420R)
        *   Course Title (e.g., 12th-Century Renaissance)
        *   Department
        *   College
        *   Stated Learning Outcomes (including title and details, if available).
*   **Output:** The scraper saves the extracted data into a CSV file, typically `learning_outcomes.csv`. Each row represents a single learning outcome for a specific course. If a course has multiple learning outcomes, it results in multiple rows.
*   **Data Source URLs:**
    *   Main listing (paginated): `https://catalog.byu.edu/courses?page=1`, `https://catalog.byu.edu/courses?page=2`, etc.
    *   Individual course pages (example): `https://catalog.byu.edu/courses/01452-023`

### Step 2: Outcome Classification (`classify_outcomes.py`)

*   **Process:** After extracting the learning outcomes, the `classify_outcomes.py` script uses an AI model (specifically, OpenAI's GPT models accessed via API) to classify each learning outcome.
    *   It takes the raw `learning_outcomes.csv` (or a specified input file) as input.
    *   For each outcome, it combines the title and details (handling cases where one might be missing) and sends it to the OpenAI API.
    *   A detailed system prompt guides the AI to evaluate the outcome against the definitions of the four BYU Aims (see `aims_of_a_BYU_education.md` for the detailed descriptions used in the prompt).
    *   The script requests the AI to return confidence scores (0-100) for each of the four aims in a structured JSON format.
*   **Output:** Saves the results, including the original course data, the confidence scores for each aim (`confidence_Aim_Name`), and a `best_aim` column (the aim with the highest score), to an output CSV file (defaults to `classified_learning_outcomes.csv`).
*   **Features:**
    *   Handles missing outcome titles or details.
    *   Designed to resume processing if interrupted by checking the output file for already classified outcomes.
    *   Supports command-line arguments for input/output files and save frequency (`python classify_outcomes.py --help`).

### Step 3: Data Analysis & Visualization (`dashboard.py`)

*   **Process:** An interactive web application built with Streamlit (`dashboard.py`) allows users to explore the classification results.
*   **Input:** Reads the classified data, preferably from a cleaned version (`data/classified_learning_outcomes_cleaned.csv`), but can also process the direct output of the classifier. It includes logic to harmonize college names and filter out placeholder text or zero-confidence entries.
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
        python course_scraper.py # Or specify output: python course_scraper.py --output learning_outcomes.csv
        ```
        *(Review `course_scraper.py --help` if available for options)*
    *   **Step 2: Classify Outcomes:**
        ```bash
        python classify_outcomes.py --input learning_outcomes.csv --output classified_learning_outcomes.csv
        ```
        *(Adjust input/output filenames as needed. Use `--help` for more options like save frequency.)*
    *   **Step 3: Analyze Results:**
        ```bash
        streamlit run dashboard.py
        ```
        *(This will start the Streamlit server and open the dashboard in your web browser. Ensure the dashboard points to the correct classified data file, potentially `data/classified_learning_outcomes_cleaned.csv` after running a cleaning script if available, or the direct output like `classified_learning_outcomes.csv`)*

## Future Enhancements

*   Propose candidate learning objectives for missing Aims based on course information (syllabus, etc.).
*   Integrate syllabus data scraping and analysis.
*   Refine the classification prompt or model for higher accuracy.
*   Develop more advanced analytics or comparison features in the dashboard.