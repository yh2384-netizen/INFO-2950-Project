"""
Appendix 18 only: Most Serious Alleged Offenses by Type (PA Juvenile Court Annual Report)

Output: one row per county with
    county, year, n_person, n_property, n_drug, n_other, dispositions
"TOTAL" in the report equals the county's total dispositions (it matches Appendix 13).
Note: these counts do not include disposition review / placement review hearings.
"""
import re
import pdfplumber
import pandas as pd

YEAR = 2019
PDF_PATH = f"PDFs/{YEAR}_Juvenile_Court_Annual_Report.pdf"
HEADER = "COUNTY PERSON PROPERTY DRUG OTHER TOTAL"   # column header printed on both pages

# 1. Find the pages. Appendix 18 is TWO pages: the first has the title, the second
#    only repeats the column header. Both carry the "Appendix 18" heading.
with pdfplumber.open(PDF_PATH) as pdf:
    pages = [(i, p.extract_text() or "") for i, p in enumerate(pdf.pages)]
table_pages = [(i, t) for i, t in pages
               if re.search(r"^Appendix 18\s*$", t, re.M) and HEADER in t]
print("Pages used:", [i + 1 for i, _ in table_pages])
assert len(table_pages) == 2, f"expected 2 Appendix 18 pages, found {len(table_pages)}"

# 2. Each data row is a county name followed by exactly 5 numbers (commas allowed):
#    "ADAMS 32 22 49 67 170"  ->  person, property, drug, other, total
#    The "% OF TOTAL" row has % signs, so it does not match and is skipped.
row_re = re.compile(r"^([A-Z][A-Z ]+?)\s+((?:[\d,]+\s+){4}[\d,]+)$")

rows = []
for _, text in table_pages:
    for line in text.splitlines():
        m = row_re.match(line.strip())
        if m and m.group(1) != "COUNTY":
            nums = [int(x.replace(",", "")) for x in m.group(2).split()]
            rows.append([m.group(1)] + nums)

offenses = pd.DataFrame(rows, columns=["county", "n_person", "n_property",
                                       "n_drug", "n_other", "dispositions"])

# 3. Pull out the report's TOTAL row so we can check our numbers against it
total_row = offenses[offenses["county"] == "TOTAL"]
offenses = offenses[offenses["county"] != "TOTAL"].reset_index(drop=True)
offenses.insert(1, "year", YEAR)

# 4. Checks: 67 counties, no duplicates, offense types add up to the total,
#    and the county columns add up to the report's statewide TOTAL row
count_cols = ["n_person", "n_property", "n_drug", "n_other", "dispositions"]
assert len(offenses) == 67, f"found {len(offenses)} counties"
assert offenses["county"].is_unique, "duplicate county"
assert (offenses[["n_person", "n_property", "n_drug", "n_other"]].sum(axis=1)
        == offenses["dispositions"]).all(), "offense types do not sum to total"
assert (offenses[count_cols].sum().values
        == total_row[count_cols].values[0]).all(), "county sums differ from TOTAL row"
print("All checks passed")

offenses.to_csv(f"pa_dispositions_{YEAR}.csv", index=False)
print(offenses.head())