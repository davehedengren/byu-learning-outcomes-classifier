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

## Next Steps

Future enhancements could include:

1. Propose candidate learning objectives based on course information (syllabus, etc)