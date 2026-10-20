"""
PA Juvenile Court Annual Report 2019
Appendix 25: Delinquency Dispositions by Race and Ethnicity

This data set contains one row per county with COUNTY, TOTAL DISPOSITIONS, WHITE NON-HISPANIC, BLACK NON-HISPANIC,
HISPANIC, OTHER, UNKNOWN. We create a DataFrame and CSV with county, year, n_white, n_black, n_hispanic, n_other, 
n_unknown, dispositions.

The dispositions do not include dispositions resulting from review / placement review.
"""

# Import the libraries we need for finding text patterns, reading PDF text, and building DataFrames

import re
import pdfplumber
import pandas as pd

# We create variables that are used in the code because the process of extracting the data is the same 
# for each Appendix 25 table in each year. Adding variables allows for simple adaptation of the code for
# each year. YEAR is the year the Juvenile Court Annual Report was published and represents the year 
# that the dispositions data is from. 

YEAR = 2019
PDF_PATH = f"PDFs/{YEAR}_Juvenile_Court_Annual_Report.pdf"
HEADER = "COUNTY TOTAL DISPOSITIONS WHITE NON-HISPANIC BLACK NON-HISPANIC HISPANIC OTHER UNKNOWN" 

# We use a list comprehension to create a list of pairs of page numbers and associated text. We then use 
# another list comprehension to find the pages that contain the table header - "County Total Dispositions White
# Non-Hispanic Black Non-Hispanic Hispanic Other Unknown" and a line that only states "Appendix 25." We used an assert 
# to check that two pages were selected, because we can see in the PDF that the data table spans over two pages, and we 
# wanted to ensure that we correctly filtered the Table of Contents.

with pdfplumber.open(PDF_PATH) as pdf:
    pages = [(i, p.extract_text() or "") for i, p in enumerate(pdf.pages)]
table_pages = [(i, t) for i, t in pages
               if re.search(r"^Appendix 25\s*$", t, re.M) and HEADER in t]
print("Pages used:", [i + 1 for i, _ in table_pages])
assert len(table_pages) == 2, f"expected 2 Appendix 25 pages, found {len(table_pages)}"

# We then take the page text, which is laid out with a name and four associated values with one county per line, 
# and use the re library to identify this text pattern. The bottom two lines from the PDF are "TOTAL" and "% OF TOTAL," 
# and the text pattern excludes % OF TOTAL line because it begins with percent sign, not a letter, so doesn't match the 
# pattern. We use nested for loops to create the rows for the DataFrame by splitting the page text into lines, 
# identifying the county and its associated data values in each line, and then placing the county's information in a 
# list and add that list to the rows list. 

# We convert the values to integers. 

row_re = re.compile(r"^([A-Z][A-Z ]+?)\s+((?:[\d,]+\s+){5}[\d,]+)$")

rows = []
for _, text in table_pages:
    for line in text.splitlines():
        m = row_re.match(line.strip())
        if m and m.group(1) != "COUNTY":
            nums = [int(x.replace(",", "")) for x in m.group(2).split()]
            rows.append([m.group(1)] + nums)

# We then create a DataFrame with the list of rows and the column names. 

race = pd.DataFrame(rows, columns=["county", "dispositions", "n_white", "n_black",
                                   "n_hispanic", "n_other", "n_unknown"])

# We then removed the TOTAL row from the DataFrame for later validation purposes and added a year column for later 
# joining purposes. We also reorder the columns.

total_row = race[race["county"] == "TOTAL"]
race = race[race["county"] != "TOTAL"].reset_index(drop=True)
cat_cols = ["n_white", "n_black", "n_hispanic", "n_other", "n_unknown"]
race = race[["county"] + cat_cols + ["dispositions"]]
race.insert(1, "year", YEAR)

# We then validated the number of county rows, that there were no duplicate counties, that each county's race
# and ethniicty types sum to the total value for that county, and that all the counties summed to the total values for 
# the state.

count_cols = cat_cols + ["dispositions"]
assert len(race) == 67, f"found {len(race)} counties"
assert race["county"].is_unique, "duplicate county"
assert (race[cat_cols].sum(axis=1) == race["dispositions"]).all(), "categories do not sum to total"
assert (race[count_cols].sum().values
        == total_row[count_cols].values[0]).all(), "county sums differ from TOTAL row"
print("All checks passed")

# We then convert the DataFrame to a CSV file, and exclude the index column. 

race.to_csv(f"pa_race_ethnicity_{YEAR}.csv", index=False)
print(race.head())