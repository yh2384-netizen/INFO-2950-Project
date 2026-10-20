"""
PA Juvenile Court Annual Report 2017
Appendix 20: Delinquency Dispositions by Age at Disposition

This data set contains one row per county with COUNTY, TOTAL DISPOSITIONS, 10 (N and %), 11 (N and %), ...
17 (N and %), 18 AND OVER (N and %). We create a DataFrame and CSV with county, year, dispositions, n_age10, 
n_age11, ... n_age17, n_age18plus. 

The dispositions do not include dispositions resulting from review / placement review.
"""

# Import the libraries we need for finding text patterns, reading PDF text, and building DataFrames

import re
import pdfplumber
import pandas as pd

# We create variables that are used in the code because the process of extracting the data is the same 
# for each Appendix 20 table in each year. Adding variables allows for simple adaptation of the code for
# each year. YEAR is the year the Juvenile Court Annual Report was published and represents the year 
# that the dispositions data is from. 

YEAR = 2017
PDF_PATH = f"PDFs/{YEAR}_Juvenile_Court_Annual_Report.pdf"

# We use a list comprehension to create a list of pairs of page numbers and associated text. We then use 
# another list comprehension to find the pages that contain a line that only states "Appendix 20." We didn't use
# header this time because the header differed between pages. We used an assert to check that four pages were 
# selected, because we can see in the PDF that the data table spans over four pages, and we wanted to ensure that we 
# correctly filtered the Table of Contents.

with pdfplumber.open(PDF_PATH) as pdf:
    pages = [(i, p.extract_text() or "") for i, p in enumerate(pdf.pages)]
table_pages = [(i, t) for i, t in pages if re.search(r"^Appendix 20\s*$", t, re.M)]
print("Pages used:", [i + 1 for i, _ in table_pages])
assert len(table_pages) == 4, f"expected 4 Appendix 20 pages, found {len(table_pages)}"

# We then take the page text, which is laid out with a name and associated values (name, number of dispositions, then 
# count percent pairs for each age group) with one county per line. The data is split over the our pages, with the 67 
# counties,dispositions, and age groups 10-14 on two pages, and the 67 counties, number of dispositions, and age groups 
# 15-18+ on the other two. Each type of page has a TOTAL row at the bottom of the two pages of that type. We use the 
# parse function to create the rows for the DataFrame from each page. 

# We drop the % values and convert the remaining count values to integers. 

row_re = re.compile(r"^([A-Z][A-Z ]+?)\s+([\d,]+)\s+((?:[\d,]+\s+[\d.]+%\s*)+)$")

def parse(text):
    rows = []
    for line in text.splitlines():
        m = row_re.match(line.strip())
        if m:
            total = int(m.group(2).replace(",", ""))
            tokens = m.group(3).split()
            ns = [int(x.replace(",", "")) for x in tokens[0::2]]   # every other token = N
            rows.append([m.group(1), total] + ns)
    return rows

# We then split the rows into the two page types they came from, identifying the separate types by checking to see
# if the text contains "18 AND OVER."

first_half, second_half = [], []
for _, text in table_pages:
    (second_half if "18 AND OVER" in text else first_half).extend(parse(text))

# We then create a DataFrame for each of the two page types, one for county, total, and age groups 10-14, and another
# for county, total, and age groups 15-18+. This is to help us handle the two instances of the total column. 

cols_first = ["county", "dispositions", "n_age10", "n_age11", "n_age12", "n_age13", "n_age14"]
cols_second = ["county", "dispositions_check", "n_age15", "n_age16", "n_age17", "n_age18plus"]
a = pd.DataFrame(first_half, columns=cols_first)
b = pd.DataFrame(second_half, columns=cols_second)

# We then merge the two DataFrames and validate that every county was found in each of the two DataFrames, and that
# the total values from each are equivalent.  

age = a.merge(b, on="county", how="outer", indicator=True)
assert (age["_merge"] == "both").all(), "a county is missing from one half"
assert (age["dispositions"] == age["dispositions_check"]).all(), "totals differ between halves"
age = age.drop(columns=["_merge", "dispositions_check"])

# We then separated the TOTAL row from the bottom of the PDF for validation purposes, sorted the rows alphabetically 
# by county, and added a year column for later joining purposes. 

total_row = age[age["county"] == "TOTAL"]
age = age[age["county"] != "TOTAL"].sort_values("county").reset_index(drop=True)
age.insert(1, "year", YEAR)

# We then validated the number of county rows, that there were no duplicate counties, that each county's dispositions
# by age sums to the total disposition value for that county, and that all the counties summed to the total values 
# for the state. 

age_cols = ["n_age10", "n_age11", "n_age12", "n_age13", "n_age14",
            "n_age15", "n_age16", "n_age17", "n_age18plus"]
count_cols = ["dispositions"] + age_cols
assert len(age) == 67, f"found {len(age)} counties"
assert age["county"].is_unique, "duplicate county"
assert (age[age_cols].sum(axis=1) == age["dispositions"]).all(), "ages do not sum to total"
assert (age[count_cols].sum().values == total_row[count_cols].values[0]).all(), \
    "county sums differ from TOTAL row"
print("All checks passed")

# We then convert the DataFrame to a CSV file, and exclude the index column.

age.to_csv(f"pa_age_{YEAR}.csv", index=False)
print(age.head())