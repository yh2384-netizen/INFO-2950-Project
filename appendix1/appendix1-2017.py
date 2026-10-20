"""
PA Juvenile Court Annual Report 2017
Appendix 1: County Class and Population

This data set contains one row per county with Class, Total Population, and Juvenile Population 10-17 year. We create
a DataFrame and CSV with county, year, county_class, total_pop, juv_pop. 

The PA Juvenile Court Judge's Commission created Appendix 1 from the "Bridged-Race Population Estimates" from 
the Centers for Disease Control and Prevention. In 2017, when the "Juvenile Court Annual Report" was published, 
the 2017 "Bridged-Race Population Estimates" had been released, so the 2017 PA population estimates are from the 2017 
"Bridged-Race Population Estimates" report. 

"""

# Import the libraries we need for finding text patterns, reading PDF text, and building DataFrames

import re
import pdfplumber
import pandas as pd

# We create variables that are used in the code because the process of extracting the data is the same 
# for each Appendix 1 table in each year. Adding variables allows for simple adaptation of the code for
# each year. YEAR_PUBLISHED is the year the Juvenile Court Annual Report was published and represents the year 
# that the population is estimated for and YEAR_ESTIMATED represents the year that the population estimates 
# were published from the CDC.

YEAR_PUBLISHED = 2017
YEAR_ESTIMATED = 2017
PDF_PATH = f"PDFs/{YEAR_PUBLISHED}_Juvenile_Court_Annual_Report.pdf"
TITLE = "County Class and Population"

# We use a list comprehension to create a list of pairs of page numbers and associated text. We then use 
# another list comphrehension to find the pages that contain the table title "County Class and Population" and a 
# line that only states "Appendix 1." We used an assert to check that only the one page was selected, because
# we can see in the PDF that the data table is only one page long, and we wanted to ensure that we did not 
# accidentally select the Table of Contents.

with pdfplumber.open(PDF_PATH) as pdf:
    pages = [(i, p.extract_text() or "") for i, p in enumerate(pdf.pages)]
hits = [(i, t) for i, t in pages
        if TITLE in t and re.search(r"^Appendix 1\s*$", t, re.M)]
assert len(hits) == 1, f"expected 1 Appendix 1 page, found {len(hits)}"
page_no, text = hits[0]
print("Page used:", page_no + 1)

# We then take the page text, which is laid out in the name, class, total pop, and juvenile pop format with 3 
# counties per line, and use the re library to identify this text pattern. We use nested for loops to create the 
# rows for the DataFrame by separating each line, identifying the 3 counties and their associated data values 
# in each line, and then placing each county's information in a list and add that list to rows list. 

block_re = re.compile(r"([A-Z][A-Z ]*?)\s+(\d[A]?)\s+([\d,]+)\s+([\d,]+)")

rows = []
for line in text.splitlines():
    for name, cls, total_pop, juv_pop in block_re.findall(line):
        rows.append([name.strip(), cls,
                     int(total_pop.replace(",", "")),
                     int(juv_pop.replace(",", ""))])

# We then create a DataFrame with the list of rows and the column names. We add a year column for later joining
# purposes and sort the DataFrame alphabetically by county. 

pop = pd.DataFrame(rows, columns=["county", "county_class", "total_pop", "juv_pop"])
pop.insert(1, "year", YEAR_ESTIMATED)
pop = pop.sort_values("county").reset_index(drop=True)

# We then perform checks to make sure the data was extracted correctly. We check that that there are 67 total counties, 
# all counties are unique, the juvenile population value is smaller than the total population value for each county, 
# and all of the county classes are a valid county class. 

assert len(pop) == 67, f"found {len(pop)} counties"
assert pop["county"].is_unique, "duplicate county"
assert (pop["juv_pop"] < pop["total_pop"]).all()
assert pop["county_class"].isin(["1", "2", "2A", "3", "4", "5", "6", "7", "8"]).all()
print("All checks passed")

# We then convert the DataFrame to a CSV file, and exclude the index column. 

pop.to_csv(f"pa_population_{YEAR_ESTIMATED}.csv", index=False)
print(pop.head())