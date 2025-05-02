# Dashboard Coverage Page TODO

- [x] Create new Streamlit page `pages/2_Coverage.py`.
- [x] Copy and adapt `load_data` function (or import if feasible) into `2_Coverage.py`.
- [x] Calculate total unique courses found in the loaded data (`df['course_url'].nunique()`).
- [x] Calculate number of outcomes per course (`df.groupby('course_url').size()`).
- [x] Generate histogram of outcomes per course using Plotly Express.
- [x] Combine outcome title and details into a single text field.
- [x] Calculate length of the combined outcome text for each row.
- [x] Calculate the 98th percentile length threshold (`df['outcome_length'].quantile(0.98)`).
- [x] Filter DataFrame to get outcomes >= 98th percentile length.
- [x] Add explanatory text about data source limitations and potential misformatted long outcomes.
- [x] Display metrics (total courses, total outcomes).
- [x] Display the histogram.
- [x] Display the list of long outcomes (course, title, details snippet, length).
- [ ] Commit changes (`pages/2_Coverage.py`, `TODO.md`). 