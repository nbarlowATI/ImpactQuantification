#!/usr/bin/env python

"""
Use scholarly to query Google Scholar for citations for given paper titles.
"""

import os
import argparse
import re

import time

import pandas as pd
import numpy as np

from scholarly import scholarly

def make_dataframe_from_input(input_csv):
    if not os.path.exists(input_csv):
        raise RuntimeError("Unable to find file {}".format(input_csv))
    df  = pd.read_csv(input_csv)
    return df


def find_surnames(authors):
    """
    Make assumption that all authors are given as surname and initials,
    so any uppercase followed by one-or-more lowercase letters is a surname.
    """
    surname_list = []
    surname_regex = "([A-Z\u00C0-\u00DE][a-z\u00DF-\u00FF\u0107]+)+"
    if isinstance(authors, str):
        surname_list = re.findall(surname_regex, authors)
        return surname_list
    elif isinstance(authors, list) or isinstance(authors, tuple):
        for author in authors:
            surname_list += re.findall(surname_regex, author)
    return surname_list

def match_surnames(list_1, list_2):
    """"
    Return True if at least one author surname matches.
    Otherwise return False
    """
    for name in list_1:
        if name in list_2:
            return True
    return False


def process_row(row_num, input_row):
    # copy the input row to the output
    output_record = {}
    for k in input_row.keys():
        output_record[k] = input_row[k]
    current_time = time.strftime("%y-%m-%d")
    new_citations_key = "Citations {}".format(current_time)
    output_record[new_citations_key] = np.nan
    paper_title = input_row["Publication title"]
    print("Processing row {}: {}".format(row_num, paper_title))

    paper_authors = input_row["Author(s)"]
    if not isinstance(paper_authors, str):
        print("unable to parse paper authors: {}".format(paper_authors))
        return output_record
    author_surnames = find_surnames(paper_authors)
    search_query = scholarly.search_pubs(paper_title)
    try:
        result = next(search_query)
    except:
        print("Error performing search query for {}".format(paper_title))
        return output_record
    if not result:
        print("Empty result for {}".format(paper_title))
        return output_record
    author_surnames_from_search = find_surnames(result.bib["author"])
    authors_match = match_surnames(author_surnames, author_surnames_from_search)
    if authors_match:
        cites = result.bib["cites"]
        print("Found matching paper with {} citations".format(cites) )
        output_record[new_citations_key] = cites
    else:
        print("Author lists didn't match: {} {}".format(author_surnames, author_surnames_from_search))
    return output_record




def main():

    parser = argparse.ArgumentParser(description="query the Google Scholar API")
    parser.add_argument("--input_csv",help="CSV file containing paper titles",required=True)
    parser.add_argument("--output_csv",help="output file",default="scholarly_output.csv")
    args = parser.parse_args()


    input_df = make_dataframe_from_input(args.input_csv)
    results = []
    for i in range(len(input_df)):
#    for i in range(30,40):
        row = input_df.loc[i]
        result = process_row(i, row)
        results.append(result)
        time.sleep(2)
    # put the results into an output DataFrame
    output_df = pd.DataFrame.from_records(results)
    output_df.to_csv(args.output_csv)
    print("Wrote output to {}".format(args.output_csv))
    print("Finished")


if __name__ == "__main__":
    main()
