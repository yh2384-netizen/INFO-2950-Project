"""
Table 1: County and Statewide Recidivism Rates: Juveniles Closed 2007-2020
(Pennsylvania Juvenile Justice Recidivism Report, JCJC, March 2025)

Output: pa_recidivism_table1_long.csv
    one row per county and cohort (67 counties x 8 cohorts = 536 rows):
    county, cohort, n_closed, recid_rate
"""
import re
import pdfplumber
import pandas as pd

# Write the exact file name as it appears in your PDFs folder (check with: ls PDFs)
PDF_PATH = "PDFs/The_Pennsylvania_Juvenile_Justice_Recidivism_Report_-_Juveniles_Closed_2007-2020.pdf"
TITLE = "Table 1: County and Statewide Recidivism Rates: Juveniles Closed 2007-2020"
COHORTS = ["2007-2010", "2011-2014", "2015", "2016", "2017", "2018", "2019", "2020"]

# 1. Find the table pages (title appears on each of the 6 pages: PDF pages 22-27)
with pdfplumber.open(PDF_PATH) as pdf:
    table_pages = [p for p in pdf.pages if TITLE in (p.extract_text() or "")]
    print("Pages used:", [p.page_number for p in table_pages])
    assert len(table_pages) == 6, f"expected 6 table pages, found {len(table_pages)}"

    # 2. Footnote markers (e.g. Bedford's "1" + footnote "12" printed as "112") are tiny
    #    superscripts. Body text is 9-12 pt and the footnote numbers are 6-7 pt, so we
    #    drop every character smaller than 8 pt before extracting text. This replaces
    #    the hand-fix for Bedford and also cleans "N/A14" / "N/A15" for Forest.
    lines = []
    for p in table_pages:
        clean = p.filter(lambda obj: obj["object_type"] != "char" or obj["size"] >= 8)
        lines += [l.strip() for l in (clean.extract_text() or "").splitlines() if l.strip()]

# 3. Each county takes 3 lines in the PDF:
#       885 680 115 116 118 140 101 97        <- # juveniles closed (8 cohorts)
#       Adams                                 <- county name
#       24% 19% 19% 23% 22% 19% 18% 19%       <- % recidivism (8 cohorts)
count_re = re.compile(r"^(?:[\d,]+\s+){7}[\d,]+$")
name_re  = re.compile(r"^([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)?):?$")     # handles "McKean" and "Total:"
pct_re   = re.compile(r"(\d+(?:\.\d+)?%|N/A)")

rows = []
for k in range(1, len(lines) - 1):
    m = name_re.match(lines[k])
    if m and count_re.match(lines[k - 1]):
        counts = lines[k - 1].split()
        pcts = pct_re.findall(lines[k + 1])
        assert len(pcts) == 8, (lines[k - 1], lines[k], lines[k + 1])
        rows.append([m.group(1)] + counts + pcts)

wide = pd.DataFrame(rows, columns=["county"]
                    + [f"n_{c}" for c in COHORTS]
                    + [f"rate_{c}" for c in COHORTS])

# 4. Convert text to numbers: "6,192" -> 6192, "24%" -> 0.24, "N/A" -> missing
for c in COHORTS:
    wide[f"n_{c}"] = wide[f"n_{c}"].str.replace(",", "").astype(int)
    wide[f"rate_{c}"] = wide[f"rate_{c}"].map(
        lambda x: None if x == "N/A" else float(x.rstrip("%")) / 100)

# 5. Separate the statewide Total row, then uppercase county names so they
#    match the annual-report tables (ADAMS, MCKEAN, ...)
total = wide[wide["county"] == "Total"].iloc[0]
wide = wide[wide["county"] != "Total"].reset_index(drop=True)
wide["county"] = wide["county"].str.upper()

# 6. Checks
assert len(wide) == 67, f"found {len(wide)} counties"
assert wide["county"].is_unique, "duplicate county"
for c in COHORTS:
    county_sum = wide[f"n_{c}"].sum()
    # the report's own county counts are off by 1 from its Total row for 2015 and 2016,
    # so allow a difference of 1 instead of requiring an exact match
    assert abs(county_sum - total[f"n_{c}"]) <= 1, (c, county_sum, total[f"n_{c}"])
    weighted = (wide[f"n_{c}"] * wide[f"rate_{c}"].fillna(0)).sum() / county_sum
    # county rates are rounded to whole percents, so the weighted average only matches approximately
    assert abs(weighted - total[f"rate_{c}"]) < 0.01, (c, weighted, total[f"rate_{c}"])
    print(f"{c}: counties sum to {county_sum} (report: {total[f'n_{c}']}), "
          f"weighted rate {weighted:.3f} (report: {total[f'rate_{c}']:.3f})")
print("All checks passed")

# 7. Reshape to long format: one row per county and cohort (easiest to merge with the annual-report tables)
long = wide.melt(id_vars="county", var_name="var", value_name="value")
long[["measure", "cohort"]] = long["var"].str.split("_", n=1, expand=True)
long = (long.pivot_table(index=["county", "cohort"], columns="measure",
                         values="value", aggfunc="first")
        .reset_index()
        .rename(columns={"n": "n_closed", "rate": "recid_rate"}))
long["n_closed"] = long["n_closed"].astype(int)
long.to_csv("pa_recidivism.csv", index=False)
print(long.head(10))