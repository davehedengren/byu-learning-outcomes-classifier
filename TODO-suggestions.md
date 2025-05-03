# Suggesting Additional Learning Outcomes TODO

- [x] Create `suggest_outcomes.py` script file.
- [x] Add basic structure: imports (pandas, os, openai, json, argparse, dotenv, collections, jinja2), argument parsing (input CSV, output CSV, maybe API model), API key loading.

**Data Pre-processing:**
- [x] Load `classified_learning_outcomes_cleaned.csv` (or specified input).
- [x] Add pre-filtering step:
    - [x] Filter out rows matching placeholder text (e.g., "No learning outcomes found").
    - [x] Filter out rows with zero confidence scores across all aims.
- [x] Combine `learning_outcome_title` and `learning_outcome_details` into `full_outcome_text` if not already done during loading.
- [x] Group the filtered DataFrame by `course_url`.
- [x] Define a function to apply to each course group:
    - [x] Determine the modal `best_aim` for the group (handle ties, e.g., take the first mode).
    - [x] Concatenate all `full_outcome_text` within the group, separated by newlines (`\n`).
    - [x] Get the first value for `course_name`, `course_title`, `department`, `college`.
    - [x] Return a Pandas Series or dictionary with these aggregated values.
- [x] Apply the function to the grouped data to create a `courses_summary_df` (one row per course).

**Core Suggestion Logic:**
- [x] Define the list of all BYU Aims.
- [x] Create OpenAI client instance.
- [x] Define the Pydantic or JSON schema model for the expected structured output (implicitly defined by prompt: `{"suggested_outcomes": ["outcome1", "outcome2", "outcome3"]}`).
- [x] Start iterating through rows of `courses_summary_df`:
    - [x] Identify non-modal aims (all aims - modal aim).
    - [x] Create a dictionary or structure to hold suggestions for the current course.
    - [x] For each `target_aim` in the non-modal aims list:
        - [x] Create `prompt_templates` directory.
        - [x] Extract Aim definitions (from `classify_outcomes.py` for now).
        - [x] Create `system_prompt_suggest.j2` template file.
        - [x] Create `user_prompt_suggest.j2` template file.
        - [x] Modify script to load templates and definitions.
        - [x] Craft the system prompt using Jinja Template.
        - [x] Craft the user prompt using Jinja Template.
        - [x] Make the OpenAI API call (`client.chat.completions.create`) using `response_format={ "type": "json_object" }`.
        - [x] Parse the JSON response.
        - [x] Store the list of 3 suggestions, associated with the `target_aim`.
        - [x] Implement error handling (API errors, JSON parsing errors).
        - [x] Add delays between API calls (`time.sleep`).
    - [x] Append the collected suggestions for the course to a results list.

**Output:**
- [x] Convert the results list (containing course info + suggestions for each non-modal aim) into a final DataFrame.
- [x] Structure the DataFrame columns appropriately (e.g., `course_url`, `course_name`, ..., `modal_aim`, `all_existing_outcomes_text`, `suggested_[Aim1]_1`, `suggested_[Aim1]_2`, ..., `suggested_[Aim3]_3`).
- [x] Save the final DataFrame to the specified output CSV (`classified_learning_outcomes_cleaned_with_suggested_aims.csv`).

**Final Steps:**
- [ ] Add docstrings and comments.
- [ ] Test the script.
- [ ] Commit `suggest_outcomes.py`, `TODO-suggestions.md`, and `prompt_templates/` directory. 