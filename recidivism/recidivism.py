"""
The Pennsylvania Juvenile Justice Recidivism Report: Juveniles Closed 2007-2020
Table 1: County and Statewide Recidivism Rates: Juveniles Closed 2007-2020

This data set contains one row per county broken into two sections - # of Juvenile's Closed and % Recidivism
with columns for Pre-JJES 2007-2010, 2011-2014, 2015, 2016, 2017, 2018, 2019, and 2020. We create a DataFrame and 
CSV with county, cohort, n_closed, recid_rate.

"""

# Import the libraries we need for finding text patterns, reading PDF text, and building DataFrames

import re
import pdfplumber
import pandas as pd

# We write variables to condense the path, title, and to make clear the different cohorts of years. 

PDF_PATH = "PDFs/The_Pennsylvania_Juvenile_Justice_Recidivism_Report_-_Juveniles_Closed_2007-2020.pdf"
TITLE = "Table 1: County and Statewide Recidivism Rates: Juveniles Closed 2007-2020"
COHORTS = ["2007-2010", "2011-2014", "2015", "2016", "2017", "2018", "2019", "2020"]

# We use a list comprehension to find the pages that contain the table title - "Table 1: County and Statewide 
# Recidivism Rates: Juveniles Closed 2007-2020." We used an assert to check that six pages were selected, because 
# we can see in the PDF that the data table spans over six pages, and we wanted to ensure that we selected the 
# appropriate number of pages. 

with pdfplumber.open(PDF_PATH) as pdf:
    table_pages = [p for p in pdf.pages if TITLE in (p.extract_text() or "")]
    print("Pages used:", [p.page_number for p in table_pages])
    assert len(table_pages) == 6, f"expected 6 table pages, found {len(table_pages)}"

# There are some odd cases, where values have a superscript marker that connects to a footnote to explain the 
# possibility of data irregularities. We remove objects that are characters with a small font size to deal with 
# these superscripts. 

    lines = []
    for p in table_pages:
        clean = p.filter(lambda obj: obj["object_type"] != "char" or obj["size"] >= 8)
        lines += [l.strip() for l in (clean.extract_text() or "").splitlines() if l.strip()]

# We then take the page text and use the re library to identify the text pattern. Each county uses three consecutive 
# lines, where one is the counts, one is the county name, and one is the rates. The bottom line of the PDF is "Total." 
# We use a for loop to create the rows for the DataFrame by identifying rows with a county name, identifying if the row
# above is a counts row, and then taking the county name, counts, and rates information and then adding it in the row
# list. We also remove the : from the Total row. 

count_re = re.compile(r"^(?:[\d,]+\s+){7}[\d,]+$")
name_re  = re.compile(r"^([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)?):?$")    
pct_re   = re.compile(r"(\d+(?:\.\d+)?%|N/A)")

rows = []
for k in range(1, len(lines) - 1):
    m = name_re.match(lines[k])
    if m and count_re.match(lines[k - 1]):
        counts = lines[k - 1].split()
        pcts = pct_re.findall(lines[k + 1])
        assert len(pcts) == 8, (lines[k - 1], lines[k], lines[k + 1])
        rows.append([m.group(1)] + counts + pcts)

# We then build a wide data frame, where each county is a row and there is a column for each cohort's rate and each 
# cohort's count. 

wide = pd.DataFrame(rows, columns=["county"]
                    + [f"n_{c}" for c in COHORTS]
                    + [f"rate_{c}" for c in COHORTS])

# We then convert the text to numbers, and make the N/A values into missing values so that it isn't mistaken for a 0%
# rate. 

for c in COHORTS:
    wide[f"n_{c}"] = wide[f"n_{c}"].str.replace(",", "").astype(int)
    wide[f"rate_{c}"] = wide[f"rate_{c}"].map(
        lambda x: None if x == "N/A" else float(x.rstrip("%")) / 100)

# We then removed the Total row from the DataFrame for later validation purposes, and uppercase the county names so
# that they match the Annual Report tables. 

total = wide[wide["county"] == "Total"].iloc[0]
wide = wide[wide["county"] != "Total"].reset_index(drop=True)
wide["county"] = wide["county"].str.upper()

# We then validated the number of county rows, that there were no duplicate counties, that each county's cohort counts
# correctly compare to the Total row, and check that the weighted average of the rates in within one percentage point
# of the statewide recidivism rate. 

assert len(wide) == 67, f"found {len(wide)} counties"
assert wide["county"].is_unique, "duplicate county"
for c in COHORTS:
    county_sum = wide[f"n_{c}"].sum()
    # The report's own county counts are off by 1 from its Total row for 2015 and 2016,
    # so we allowed a difference of 1 instead of requiring an exact match
    assert abs(county_sum - total[f"n_{c}"]) <= 1, (c, county_sum, total[f"n_{c}"])
    weighted = (wide[f"n_{c}"] * wide[f"rate_{c}"].fillna(0)).sum() / county_sum
    assert abs(weighted - total[f"rate_{c}"]) < 0.01, (c, weighted, total[f"rate_{c}"])
    print(f"{c}: counties sum to {county_sum} (report: {total[f'n_{c}']}), "
          f"weighted rate {weighted:.3f} (report: {total[f'rate_{c}']:.3f})")
print("All checks passed")

# We reshaped the DataFrame from wide to long, so that the cohorts become part of the rows (one row per county and 
# cohort) because this is the style that the Annual Reports are in, so it will be better for eventual merging. 

long = wide.melt(id_vars="county", var_name="var", value_name="value")
long[["measure", "cohort"]] = long["var"].str.split("_", n=1, expand=True)
long = (long.pivot_table(index=["county", "cohort"], columns="measure",
                         values="value", aggfunc="first")
        .reset_index()
        .rename(columns={"n": "n_closed", "rate": "recid_rate"}))
long["n_closed"] = long["n_closed"].astype(int)
long.to_csv("pa_recidivism.csv", index=False)
print(long.head(10))