#!/usr/bin/env python

"""
Use scholarly to query Google Scholar for citations for given paper titles.
"""

import os
import argparse
from scholarly import scholarly




def main():
    parser = argparse.ArgumentParser("query the Google Scholar API")
    parser.add_argument("--input_csv",help="CSV file containing paper titles")

    args = parser.parse_args()



if __name__ == "__main__":
    main()
