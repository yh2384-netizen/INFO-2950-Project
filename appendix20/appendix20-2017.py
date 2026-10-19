"""
Appendix 20 only: Delinquency Dispositions by Age at Disposition
(PA Juvenile Court Annual Report)

Output: one row per county with
    county, year, dispositions, n_age10 ... n_age17, n_age18plus
Counts only. The report's own % columns are dropped so every share can be
recomputed the same way later (e.g. pct_age_16plus = (n_age16 + n_age17 + n_age18plus) / dispositions).
Note: these counts do not include disposition review / placement review hearings.
"""
import re
import pdfplumber
import pandas as pd

YEAR = 2017
PDF_PATH = f"PDFs/{YEAR}_Juvenile_Court_Annual_Report.pdf"

# 1. Find the pages. Appendix 20 is FOUR pages with the same layout idea as your
#    placements table: the ages are split into two halves, and each half is
#    printed over two pages (counties A-J, then L-Z).
#      ages 10-14  -> 2 pages        ages 15, 16, 17, 18 and over -> 2 pages
#    Only the second half has "18 AND OVER" in its header.
with pdfplumber.open(PDF_PATH) as pdf:
    pages = [(i, p.extract_text() or "") for i, p in enumerate(pdf.pages)]
table_pages = [(i, t) for i, t in pages if re.search(r"^Appendix 20\s*$", t, re.M)]
print("Pages used:", [i + 1 for i, _ in table_pages])
assert len(table_pages) == 4, f"expected 4 Appendix 20 pages, found {len(table_pages)}"

# 2. A data row looks like:  "ADAMS 170 1 0.6% 5 2.9% 3 1.8% ..."
#    county name, total dispositions, then (N, %) pairs. We keep only the N values.
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

first_half, second_half = [], []
for _, text in table_pages:
    (second_half if "18 AND OVER" in text else first_half).extend(parse(text))

cols_first = ["county", "dispositions", "n_age10", "n_age11", "n_age12", "n_age13", "n_age14"]
cols_second = ["county", "dispositions_check", "n_age15", "n_age16", "n_age17", "n_age18plus"]
a = pd.DataFrame(first_half, columns=cols_first)
b = pd.DataFrame(second_half, columns=cols_second)

# 3. Join the two halves on county; every county must appear in both
age = a.merge(b, on="county", how="outer", indicator=True)
assert (age["_merge"] == "both").all(), "a county is missing from one half"
assert (age["dispositions"] == age["dispositions_check"]).all(), "totals differ between halves"
age = age.drop(columns=["_merge", "dispositions_check"])

# 4. Pull out the report's statewide TOTAL row, then check our numbers against it
total_row = age[age["county"] == "TOTAL"]
age = age[age["county"] != "TOTAL"].sort_values("county").reset_index(drop=True)
age.insert(1, "year", YEAR)

age_cols = ["n_age10", "n_age11", "n_age12", "n_age13", "n_age14",
            "n_age15", "n_age16", "n_age17", "n_age18plus"]
count_cols = ["dispositions"] + age_cols
assert len(age) == 67, f"found {len(age)} counties"
assert age["county"].is_unique, "duplicate county"
assert (age[age_cols].sum(axis=1) == age["dispositions"]).all(), "ages do not sum to total"
assert (age[count_cols].sum().values == total_row[count_cols].values[0]).all(), \
    "county sums differ from TOTAL row"
print("All checks passed")

age.to_csv(f"pa_age_{YEAR}.csv", index=False)
print(age.head())