"""
Appendix 1 only: County Class and Population (PA Juvenile Court Annual Report)

Output: one row per county with
    county, year, county_class, total_pop, juv_pop (ages 10-17)
Same style as the placements / recidivism cells in the Phase 2 notebook.
"""

import re
import pdfplumber
import pandas as pd

YEAR_PUBLISHED = 2019
YEAR_ESTIMATED = 2018
PDF_PATH = f"PDFs/{YEAR_PUBLISHED}_Juvenile_Court_Annual_Report.pdf"
TITLE = "County Class and Population"

# 1. Find the page. Appendix 1 is a single page, identified by its title text.
#    (We also require the "Appendix 1" heading so we don't match a table of contents.)
with pdfplumber.open(PDF_PATH) as pdf:
    pages = [(i, p.extract_text() or "") for i, p in enumerate(pdf.pages)]
hits = [(i, t) for i, t in pages
        if TITLE in t and re.search(r"^Appendix 1\s*$", t, re.M)]
assert len(hits) == 1, f"expected 1 Appendix 1 page, found {len(hits)}"
page_no, text = hits[0]
print("Page used:", page_no + 1)

# 2. Each text line holds THREE counties side by side, e.g.
#    "PHILADELPHIA 1 1,584,138 141,485 MONROE 4 169,507 17,082 JEFFERSON 6 43,641 4,185"
#    A county block = NAME  CLASS  TOTAL_POP  JUVENILE_POP
#    CLASS is a digit, sometimes followed by A (e.g. "2A").
block_re = re.compile(r"([A-Z][A-Z ]*?)\s+(\d[A]?)\s+([\d,]+)\s+([\d,]+)")

rows = []
for line in text.splitlines():
    for name, cls, total_pop, juv_pop in block_re.findall(line):
        rows.append([name.strip(), cls,
                     int(total_pop.replace(",", "")),
                     int(juv_pop.replace(",", ""))])

pop = pd.DataFrame(rows, columns=["county", "county_class", "total_pop", "juv_pop"])
pop.insert(1, "year", YEAR_ESTIMATED)
pop = pop.sort_values("county").reset_index(drop=True)   # the page lists counties by class, not A-Z

# 3. Checks: 67 counties, no duplicates, sensible values
assert len(pop) == 67, f"found {len(pop)} counties"
assert pop["county"].is_unique, "duplicate county"
assert (pop["juv_pop"] < pop["total_pop"]).all()
assert pop["county_class"].isin(["1", "2", "2A", "3", "4", "5", "6", "7", "8"]).all()
print("All checks passed")

pop.to_csv(f"pa_population_{YEAR_ESTIMATED}.csv", index=False)
print(pop.head())