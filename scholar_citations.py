#!/usr/bin/env python

"""
Query Google Scholar for citations for given paper titles, and use BeautifulSoup to parse
the results.
Expects a CSV file input with headings "Author(s)", "Publication title".
"""

import os
import argparse
import re

import time

import pandas as pd
import numpy as np
import requests
from urllib.parse import urlencode
from bs4 import BeautifulSoup

surname_regex = re.compile("([A-Z\u00C0-\u00DE][a-z\u00DF-\u00FF\u0107]+)+")


def get_proxy_url(url):
    payload = {'api_key': SCRAPER_API_KEY, 'url': url, 'country_code': 'us'}
    proxy_url = 'http://api.scraperapi.com/?' + urlencode(payload)
    return proxy_url

def perform_query(paper_title, use_proxy=False):
    url = "https://scholar.google.com/scholar?" + urlencode({"hl": "en", "q": paper_title})
    if use_proxy:
        url = get_proxy_url(url)
    print(f"Querying {url}")
    try:
        r = requests.get(url)
        print(f"Got status code {r.status_code}")
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, "html.parser")
            print("Parsed OK")
            return soup
    except:
        print(f"Trouble getting {url}")
    return None

def parse_query_result(soup):
    outputs = []
    search_results = soup.find_all("div", attrs={"class":"gs_ri"})
    for sr in search_results:
        try:
            authors = sr.find("div", attrs={"class": "gs_a"}).text
            authors = authors.split("\xa0")[0]
            authors = find_surnames(authors)
        except:
            authors = []
        cite_link = sr.find(href=re.compile("scholar\?cites"))
        if cite_link:
            cite_txt = cite_link.text
            citations = int(re.search("Cited by ([\d]+)", cite_txt).groups()[0])
            print(f"Cited by {citations}")
        else:
            citations = 0
        outputs.append({"authors": authors, "citations": citations})
    return outputs


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

    if isinstance(authors, str):
        surname_list = surname_regex.findall(authors)
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


def scholarly_query(paper_title, paper_authors):
    """
    use the scholarly package to query google scholar.
    """
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
    author_surnames_from_search = find_surnames(result['bib']["author"])
    authors_match = match_surnames(author_surnames, author_surnames_from_search)
    if authors_match:
        cites = result["num_citations"]
        print("Found matching paper with {} citations".format(cites) )
        return cites
    else:
        print("Author lists didn't match: {} {}".format(author_surnames, author_surnames_from_search))
        return -1


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
    cites = -1
    paper_authors = input_row["Author(s)"]
    if not isinstance(paper_authors, str):
        print("unable to parse paper authors: {}".format(paper_authors))
        author_surnames = []
    else:
        author_surnames = find_surnames(paper_authors)
    query_result = perform_query(paper_title)
    if query_result != None:
        results = parse_query_result(query_result)
        for result in results:
            if match_surnames(result["authors"], author_surnames) or len(author_surnames)==0:
                cites = result["citations"]
                break

    output_record[new_citations_key] = cites

    return output_record




def main():

    parser = argparse.ArgumentParser(description="query the Google Scholar API")
    parser.add_argument("--input_csv",help="CSV file containing paper titles",required=True)
    parser.add_argument("--output_csv",help="output file",default="scholarly_output.csv")
    parser.add_argument("--start_row", help="first row")
    parser.add_argument("--end_row", help="last row")
    args = parser.parse_args()
    input_df = make_dataframe_from_input(args.input_csv)
    start_row = int(args.start_row) if args.start_row else 0
    end_row = int(args.end_row) if args.end_row else len(input_df)-1
    for j in range(start_row, end_row, 10):
        results = []
        for i in range(j*10, (j+1)*10):
            row = input_df.loc[i]
            result = process_row(i, row)
            results.append(result)
            time.sleep(15)
        # put the results into an output DataFrame
        output_df = pd.DataFrame.from_records(results)
        output_filename = args.output_csv+f"_{j*10}-{(j+1)*10}.csv"
        output_df.to_csv(output_filename)
        print("Wrote output to {}".format(output_filename))
    print("Finished")


if __name__ == "__main__":
    main()
