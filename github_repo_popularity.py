#!/usr/bin/env python

"""
Usage:
python github_repo_popularity.py --repo <repo_name> --owner <owner>

"""

import os
import time
import argparse
import requests
from requests.auth import HTTPBasicAuth
import json
import getpass
import uuid
import re
import datetime

GITHUB_REGEX = re.compile("http(s)?://github.com/[-\w]+/[-\w\.]+$")

BASE_URI = "https://api.github.com"


def get_oauth_token():
    """
    generate an OAuth token that can be used to authenticate other requests.
    """
    u = input("Enter your github username: ")
    p = getpass.getpass()
    auth_uri = "{}/authorizations".format(BASE_URI)
    r = requests.post(auth_uri,
                      auth=HTTPBasicAuth(username=u,password=p),
                      json={"scopes": ["repo"],
                            "note": "token for getting repo info: uid: {}".format(uuid.uuid1())}
                      )
    response = json.loads(r.content.decode("utf-8"))
    if r.status_code != 201:
        message = response["message"]
        raise RuntimeError("Unable to get OAuth token: {}".format(message))
    return response["token"]


def get_traffic(owner, repo, token):
    """
    get views and clones for the past 14 days.
    Requires authentication - user must provide a PAT.
    """

    headers = {
        "Authorization": "Bearer {}".format(token),
        "X-GitHub-Api-Version": "2022-11-28"
    }
    return_dict = {"views": ["n/a"], "clones": ["n/a"]}
    for resource in return_dict.keys():
        uri = "{}/repos/{}/{}/traffic/{}".format(BASE_URI,
                                                 owner,
                                                 repo,
                                                 resource)
        r = requests.get(uri, headers=headers)
        if r.status_code != 200:
            print("Problem getting URL {}".format(uri))
            return return_dict
        j = r.json()
        count = j['count']
        print("Count of {} in past 14 days: {}".format(resource, count))
        return_dict[resource] = [count]
    return return_dict


def get_stars_watchers_forks(owner, repo, token=None):
    """
    print some basic repository information - number of stars, number of forks,
    number of watchers.
    """
    repo_url = "{}/repos/{}/{}".format(BASE_URI, owner, repo)
    if token:
        headers = {"Authorization": "token {}".format(token)}
        r = requests.get(repo_url, headers=headers)
    else:
        r = requests.get(repo_url)
    if r.status_code != 200:
        raise RuntimeError("Problem getting URL {}".format(repo_url))
    j = r.json()
    num_stars = j["stargazers_count"]
    num_forks = j["forks_count"]
    num_watchers = j["watchers_count"]
    print("Number of stars: {}".format(num_stars))
    print("Number of forks: {}".format(num_forks))
    print("Number of watchers: {}".format(num_watchers))
    return {"stars": [num_stars],
            "forks": [num_forks],
            "watchers": [num_watchers]}


def write_output_csv(filename, results):
    """
    write the results to a csv file.
    Assume they are in the format {"header": [val, ...], ... }
    """
    today_date = datetime.datetime.today().isoformat().split("T")[0]
    outputdir = os.path.dirname(filename)
    if len(outputdir) > 0 and not os.path.exists(outputdir):
        os.makedirs(outputdir, exist_ok = True)
    if os.path.exists(filename):
        mode = "a"
        write_headers = False
    else:
        mode = "w"
        write_headers = True
    headers = list(results.keys())
    with open(filename, mode) as outfile:
        if write_headers:
            header_line = "date,"
            for header in headers:
                header_line += header+","
                # remove trailing comma and add newline
            header_line = header_line[:-1] + "\n"
            outfile.write(header_line)
        # now loop through all rows.
        for irow in range(len(results[headers[0]])):
            row = today_date+","
            for header in headers:
                row += str(results[header][irow]) +","
            row = row[:-1] + "\n"
            outfile.write(row)


def fill_row(owner, repo, traffic=False, PAT=None):
    """
    Fill data for a single row of the output table
    """
    results = {"repo" : ["{}/{}".format(owner, repo)]}
    results.update(get_stars_watchers_forks(owner, repo, PAT))
    if traffic:
        results.update(get_traffic(owner, repo, PAT))
    return results


def process_input_file(input_filename, traffic, PAT):
    """
    Loop through all lines of an input text file, one URL per line
    """
    results = {}
    infile = open(input_filename)
    for line in infile.readlines():
        time.sleep(2)
        if not GITHUB_REGEX.search(line.strip()):
            raise RuntimeError("Not a Github URL! {}".format(line.strip()))
        owner, repo = line.strip().split("/")[-2:]
        print("Looking at {}/{}".format(owner, repo))
        try:
            this_row = fill_row(owner, repo, traffic, PAT)
            for k, v in this_row.items():
                if not k in results.keys():
                    results[k] = []
                results[k] += v
        except(RuntimeError):
            print("Problem filling row for {}/{}".format(owner, repo))
            continue
    return results


def sanity_check(args):
    """
    make sure we have a consistent set of arguments,
    and give a helpful error message if not.
    """
    if (args.repo or args.owner) and not (args.repo and args.owner):
        raise RuntimeError("Need to set both or neither of --repo and --owner")
    if (args.repo and args.input_filename) or not (args.repo or args.input_filename):
        raise RuntimeError("Need to set EITHER --repo and --owner OR --input_filename")
    if args.PAT and not args.traffic:
        print("No need to specify PAT if not requesting traffic info")



def main():
    parser = argparse.ArgumentParser(description="Get info from github API")
    parser.add_argument("--repo",help="repository name")
    parser.add_argument("--owner",help="repository owner")
    parser.add_argument("--traffic",help="get clones, views for past 14 days (requires authentication", action='store_true')
    parser.add_argument("--PAT",help="If the user has one, input a Personal Access Token (with 'repo' scope)")
    parser.add_argument("--input_filename",help="Name of input file")
    parser.add_argument("--output_filename",help="Name of output csv file")
    args = parser.parse_args()
    sanity_check(args)
    results = {}
    if args.owner and args.repo:
        results.update(fill_row(args.owner, args.repo, args.traffic, args.PAT))
    elif args.input_filename:
        ## loop over all lines in an input line, one URL per line
        results.update(process_input_file(args.input_filename, args.traffic, args.PAT))

    if args.output_filename:
        write_output_csv(args.output_filename, results)


if __name__ == "__main__":
    main()
