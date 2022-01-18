# A2L2XDF

Uses the excellent `pyA2L` library to generate an XDF using data from an A2L. See included CSV format for examples.

Only tested on a small subset of A2Ls which use AXIS_PTS_REF - the concepts, however, should be fairly universal.

A few notes:

* Open the A2L and re-save it using UTF-8. Many A2Ls are in LATIN-1 or worse ASCII with wrong characters. Saving it as UTF-8 solves a lot of pain.
* PyA2L has issues with "// " strings in descriptions. Search for "//=" and replace with "=".
* PyA2L has a few other weird parse issues you may need to fix manually.

# PDX2CSV

* Unzip a PDX file to a directory.
* Run "python3 pdx2csv.py <directory>"
* Checkout dtcs.csv and diag.csv for DTCs and $22 identifiers respectively.

Tested on PDX from several vendors. 
