"""
Appendix 21 only: Delinquency Dispositions by School Status (PA Juvenile Court Annual Report)

Output: one row per county with
    county, year, n_in_school, n_out_of_school, n_not_reported, dispositions
"TOTAL" in the report equals the county's total dispositions.
Note: these counts do not include disposition review / placement review hearings.
"""
import re
import pdfplumber
import pandas as pd

YEAR = 2017
PDF_PATH = f"PDFs/{YEAR}_Juvenile_Court_Annual_Report.pdf"
HEADER = "COUNTY TOTAL DISPOSITIONS IN SCHOOL OUT OF SCHOOL NOT REPORTED"   # printed on both pages

# 1. Find the pages. Appendix 21 is TWO pages, both with the "Appendix 21" heading and the header line.
with pdfplumber.open(PDF_PATH) as pdf:
    pages = [(i, p.extract_text() or "") for i, p in enumerate(pdf.pages)]
table_pages = [(i, t) for i, t in pages
               if re.search(r"^Appendix 21\s*$", t, re.M) and HEADER in t]
print("Pages used:", [i + 1 for i, _ in table_pages])
assert len(table_pages) == 2, f"expected 2 Appendix 21 pages, found {len(table_pages)}"

# 2. Each data row is a county name followed by exactly 4 numbers (commas allowed):
#    "ADAMS 170 151 16 3"  ->  total, in school, out of school, not reported
#    The "% OF TOTAL" row has % signs, so it does not match and is skipped.
row_re = re.compile(r"^([A-Z][A-Z ]+?)\s+((?:[\d,]+\s+){3}[\d,]+)$")

rows = []
for _, text in table_pages:
    for line in text.splitlines():
        m = row_re.match(line.strip())
        if m and m.group(1) != "COUNTY":
            nums = [int(x.replace(",", "")) for x in m.group(2).split()]
            rows.append([m.group(1)] + nums)

school = pd.DataFrame(rows, columns=["county", "dispositions", "n_in_school",
                                     "n_out_of_school", "n_not_reported"])

# 3. Pull out the report's TOTAL row so we can check our numbers against it
total_row = school[school["county"] == "TOTAL"]
school = school[school["county"] != "TOTAL"].reset_index(drop=True)
school = school[["county", "n_in_school", "n_out_of_school", "n_not_reported", "dispositions"]]
school.insert(1, "year", YEAR)

# 4. Checks: 67 counties, no duplicates, categories add up to the total,
#    and the county columns add up to the report's statewide TOTAL row
count_cols = ["n_in_school", "n_out_of_school", "n_not_reported", "dispositions"]
assert len(school) == 67, f"found {len(school)} counties"
assert school["county"].is_unique, "duplicate county"
assert (school[["n_in_school", "n_out_of_school", "n_not_reported"]].sum(axis=1)
        == school["dispositions"]).all(), "categories do not sum to total"
assert (school[count_cols].sum().values
        == total_row[count_cols].values[0]).all(), "county sums differ from TOTAL row"
print("All checks passed")

school.to_csv(f"pa_school_status_{YEAR}.csv", index=False)
print(school.head())