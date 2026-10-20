"""
PA Juvenile Court Annual Report 2017
Appendix 18: Most Serious Alleged Offenses by Type 

This data set contains one row per county with COUNTY, PERSON, PROPERTY, DRUG, OTHER, TOTAL columns, and a TOTAL and 
% TOTAL row. We create a DataFrame and CSV with county, year, n_person, n_property, n_drug, n_other, and dispositions.

The dispositions do not include dispositions resulting from review / placement review.
"""

# Import the libraries we need for finding text patterns, reading PDF text, and building DataFrames

import re
import pdfplumber
import pandas as pd

# We create variables that are used in the code because the process of extracting the data is the same 
# for each Appendix 18 table in each year. Adding variables allows for simple adaptation of the code for
# each year. YEAR is the year the Juvenile Court Annual Report was published and represents the year 
# that the dispositions data is from. 

YEAR = 2017
PDF_PATH = f"PDFs/{YEAR}_Juvenile_Court_Annual_Report.pdf"
HEADER = "COUNTY PERSON PROPERTY DRUG OTHER TOTAL"   # column header printed on both pages

# We use a list comprehension to create a list of pairs of page numbers and associated text. We then use 
# another list comprehension to find the pages that contain the table header - "County Person Property Drug Other Total" 
# and a line that only states "Appendix 18." We used an assert to check that two pages were selected, because
# we can see in the PDF that the data table spans over two pages, and we wanted to ensure that we correctly filtered 
# the Table of Contents.

with pdfplumber.open(PDF_PATH) as pdf:
    pages = [(i, p.extract_text() or "") for i, p in enumerate(pdf.pages)]
table_pages = [(i, t) for i, t in pages
               if re.search(r"^Appendix 18\s*$", t, re.M) and HEADER in t]
print("Pages used:", [i + 1 for i, _ in table_pages])
assert len(table_pages) == 2, f"expected 2 Appendix 18 pages, found {len(table_pages)}"

# We then take the page text, which is laid out with a name and 5 associated values with one
# county per line, (the bottom two lines are "TOTAL" and "% TOTAL") and use the re library to identify this text 
# pattern. The text pattern excludes % TOTAL because of the character in its name. We use nested for loops to create 
# the rows for the DataFrame by separating each line, identifying the county and its associated data values 
# in each line, and then placing the county's information in a list and add that list to rows list. 

# We convert the values to integers. 

row_re = re.compile(r"^([A-Z][A-Z ]+?)\s+((?:[\d,]+\s+){4}[\d,]+)$")

rows = []
for _, text in table_pages:
    for line in text.splitlines():
        m = row_re.match(line.strip())
        if m and m.group(1) != "COUNTY":
            nums = [int(x.replace(",", "")) for x in m.group(2).split()]
            rows.append([m.group(1)] + nums)

# We then create a DataFrame with the list of rows and the column names. We name the TOTAL values column "dispositions,"
# because that is what the values represent. 

offenses = pd.DataFrame(rows, columns=["county", "n_person", "n_property",
                                       "n_drug", "n_other", "dispositions"])

# We then separated the TOTAL row from the bottom of the PDF for validation purposes and added a year column for later 
# joining purposes. 

total_row = offenses[offenses["county"] == "TOTAL"]
offenses = offenses[offenses["county"] != "TOTAL"].reset_index(drop=True)
offenses.insert(1, "year", YEAR)

# We then validated the number of county rows, that there were no duplicate counties, that each county's offense
# type sums to the total value for that county, and that all the counties summed to the total values for the state. 

count_cols = ["n_person", "n_property", "n_drug", "n_other", "dispositions"]
assert len(offenses) == 67, f"found {len(offenses)} counties"
assert offenses["county"].is_unique, "duplicate county"
assert (offenses[["n_person", "n_property", "n_drug", "n_other"]].sum(axis=1)
        == offenses["dispositions"]).all(), "offense types do not sum to total"
assert (offenses[count_cols].sum().values
        == total_row[count_cols].values[0]).all(), "county sums differ from TOTAL row"
print("All checks passed")

# We then convert the DataFrame to a CSV file, and exclude the index column. 

offenses.to_csv(f"pa_dispositions_{YEAR}.csv", index=False)
print(offenses.head())