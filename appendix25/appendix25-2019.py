"""
Appendix 25 only: Delinquency Dispositions by Race and Ethnicity (PA Juvenile Court Annual Report)

Output: one row per county with
    county, year, n_white, n_black, n_hispanic, n_other, n_unknown, dispositions
(White and Black are non-Hispanic, as in the report.)
"TOTAL" in the report equals the county's total dispositions.
Note: these counts do not include disposition review / placement review hearings.
"""
import re
import pdfplumber
import pandas as pd

YEAR = 2019
PDF_PATH = f"PDFs/{YEAR}_Juvenile_Court_Annual_Report.pdf"
HEADER = "COUNTY TOTAL DISPOSITIONS WHITE NON-HISPANIC BLACK NON-HISPANIC HISPANIC OTHER UNKNOWN"  # both pages

# 1. Find the pages. Appendix 25 is TWO pages, both with the "Appendix 25" heading and the header line.
with pdfplumber.open(PDF_PATH) as pdf:
    pages = [(i, p.extract_text() or "") for i, p in enumerate(pdf.pages)]
table_pages = [(i, t) for i, t in pages
               if re.search(r"^Appendix 25\s*$", t, re.M) and HEADER in t]
print("Pages used:", [i + 1 for i, _ in table_pages])
assert len(table_pages) == 2, f"expected 2 Appendix 25 pages, found {len(table_pages)}"

# 2. Each data row is a county name followed by exactly 6 numbers (commas allowed):
#    "ADAMS 170 116 20 32 2 0"  ->  total, white, black, hispanic, other, unknown
#    The "% OF TOTAL" row has % signs, so it does not match and is skipped.
row_re = re.compile(r"^([A-Z][A-Z ]+?)\s+((?:[\d,]+\s+){5}[\d,]+)$")

rows = []
for _, text in table_pages:
    for line in text.splitlines():
        m = row_re.match(line.strip())
        if m and m.group(1) != "COUNTY":
            nums = [int(x.replace(",", "")) for x in m.group(2).split()]
            rows.append([m.group(1)] + nums)

race = pd.DataFrame(rows, columns=["county", "dispositions", "n_white", "n_black",
                                   "n_hispanic", "n_other", "n_unknown"])

# 3. Pull out the report's TOTAL row so we can check our numbers against it
total_row = race[race["county"] == "TOTAL"]
race = race[race["county"] != "TOTAL"].reset_index(drop=True)
cat_cols = ["n_white", "n_black", "n_hispanic", "n_other", "n_unknown"]
race = race[["county"] + cat_cols + ["dispositions"]]
race.insert(1, "year", YEAR)

# 4. Checks: 67 counties, no duplicates, categories add up to the total,
#    and the county columns add up to the report's statewide TOTAL row
count_cols = cat_cols + ["dispositions"]
assert len(race) == 67, f"found {len(race)} counties"
assert race["county"].is_unique, "duplicate county"
assert (race[cat_cols].sum(axis=1) == race["dispositions"]).all(), "categories do not sum to total"
assert (race[count_cols].sum().values
        == total_row[count_cols].values[0]).all(), "county sums differ from TOTAL row"
print("All checks passed")

race.to_csv(f"pa_race_ethnicity_{YEAR}.csv", index=False)
print(race.head())