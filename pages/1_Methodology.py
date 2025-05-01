import streamlit as st

st.set_page_config(layout="wide", page_title="Methodology")

st.title("Project Methodology")

st.markdown("""
This page outlines the process used to gather, clean, and classify BYU course learning outcomes 
according to the Aims of a BYU Education.
""")

st.header("1. Data Extraction (Web Scraping)")
st.markdown("""
The initial step involved extracting course details and learning outcomes from the BYU Course Catalog website.

*   **Course URLs:** A list of individual course page URLs was compiled (represented by `course_urls.txt`).
*   **HTML Fetching:** Selenium was used to navigate to each course URL and download the raw HTML content of the page. Pages were saved locally (`course_pages/`) for parsing.
*   **Data Parsing:** BeautifulSoup was employed to parse the saved HTML files.
    *   Extracted key information: Course Code (e.g., CMLIT 420R), Course Title, Department, and College.
    *   Located and extracted stated Learning Outcomes, handling various formats and structures found across different course pages.
    *   Assigned a sequential ID to each outcome within a course.
    *   Handled courses explicitly stating no learning outcomes were available.
*   **Storage:** Extracted data for each learning outcome was stored as a row in a CSV file (`learning_outcomes.csv`).
*   **Politeness:** Delays between download requests and user-agent randomization were used to minimize load on the catalog server.
""")

st.header("2. Data Cleaning")
st.markdown("""
The raw scraped data often contained formatting inconsistencies and potentially problematic characters. A dedicated cleaning script (`clean_csv.py`) was developed to address this.

*   **Encoding Handling:** Supported reading files with different text encodings (UTF-8, Latin-1, etc.) with automatic fallback.
*   **Text Cleaning:** Removed extraneous line breaks, decoded HTML entities (like `&amp;`), and standardized whitespace in text fields (titles, details, etc.).
*   **CSV Parsing:** Implemented robust CSV parsing to handle potentially malformed rows, quoted fields, and multiline entries.
*   **Output:** Produced a cleaned CSV file (`classified_learning_outcomes_cleaned.csv` or similar) ready for classification.
""")

st.header("3. Learning Outcome Classification (LLM)")
st.markdown("""
The core analysis involved using a Large Language Model (LLM) via the OpenAI API to classify each learning outcome against the four BYU Aims:

1.  **Spiritually Strengthening**
2.  **Intellectually Enlarging**
3.  **Character Building**
4.  **Lifelong Learning and Service**

*   **Setup:** Configured secure access to the OpenAI API.
*   **Input:** The classification script (`classify_outcomes_batch.py`) reads the cleaned CSV data.
*   **Classification Prompt:** A detailed system prompt was crafted, providing the LLM with descriptions of each BYU Aim and instructing it to return confidence scores (0-100) for *each* aim for a given learning outcome, formatted as structured JSON.
*   **API Interaction:** For each learning outcome:
    *   Sent the outcome text and the system prompt to the LLM (specifically, a GPT model).
    *   Received the JSON response containing the four confidence scores.
    *   Handled potential API errors or timeouts gracefully.
*   **Processing:**
    *   Processed outcomes incrementally, saving progress frequently to prevent data loss and allow resumption.
    *   Included delays between API calls to adhere to rate limits.
*   **Output Storage:**
    *   Appended the four confidence scores as new columns to the data.
    *   Identified the aim with the highest confidence score and added it as a `best_aim` column.
    *   Saved the results incrementally to the final classified CSV file (e.g., `classified_learning_outcomes_cleaned.csv`).
""")

st.header("4. Dashboard Visualization")
st.markdown("""
Finally, this Streamlit dashboard (`dashboard.py`) was created to load the classified data and provide interactive visualizations and exploration capabilities, including filtering by college/department and viewing aim distributions.
""") 