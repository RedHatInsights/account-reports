#!/usr/bin/env python2

from datetime import datetime
import argparse
import json
import requests
import sys

NOW = datetime.now()
BASE_URL = "https://api.access.redhat.com/r/insights"

class InsightsError(Exception):
    pass


def get_creds(args):
    if args.creds_file:
        with open(args.creds_file) as fp:
            creds_line = fp.readline().strip()
            if ":" in creds_line:
                return tuple(creds_line.split(":", 1))
            else:
                raise InsightsError("Invalid credentials format ('user:pass')")
    elif args.username and args.password:
        return (args.username, args.password)
    else:
        raise InsightsError("Credentials not found")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--username")
    p.add_argument("--password")
    p.add_argument("--creds-file")
    p.add_argument("--account", help="Account number")
    p.add_argument("--tsv", action="store_true", help="Dump data to stdout as a tsv")
    p.add_argument("report", choices=reports.keys(), help="Type of report to generate")
    return p.parse_args()


def get(session, url):
    response = session.get(url)
    if response.status_code > 200:
        raise InsightsError("%s: %s" % (response.status_code, response.reason))
    else:
        return response.json()


def get_session(creds, account=None):
    session = requests.Session()
    session.auth = creds
    if account:
        session.params = {"account_number": account}
    return session


def fetch_reports(creds, account=None):
    session = get_session(creds, account)
    reports_url = BASE_URL + "/v2/reports"
    reports = get(session, reports_url)["resources"]

    # Add hostname to report data (gotta fetch systems)
    systems_url = BASE_URL + "/v3/systems"
    hostname_map = {r["system_id"]: r["hostname"] for r in get(session, systems_url)["resources"]}
    for r in reports:
        r["hostname"] = hostname_map[r["system_id"]]

    return reports
    
def fetch_registration(creds, account=None):
    session = get_session(creds, account)
    url = BASE_URL + "/v3/systems"
    systems = get(session, url)["resources"]
    systems.extend(get(session, url + "/unregistered"))
    return systems


def stale_test(d):
    if d.get("unregistered_at") is not None:
        return False
    dt = datetime.strptime(d["last_check_in"], "%Y-%m-%dT%H:%M:%S.%fZ")
    return (NOW - dt).days > 0


def fetch_stale(creds, account=None):
    systems = fetch_registration(creds, account)
    filtered = [s for s in systems if stale_test(s)]
    return sorted(filtered, key=lambda i: i["last_check_in"])


def report_tsv(systems, fields):
    print("\t".join(fields))
    for system in systems:
        print("\t".join(system[k] or "" for k in fields))


def report_console(systems, fields):
    data = [{k: s[k] or "" for k in fields} for s in systems]
    column_widths = [max([len(d[k]) for d in data] + [len(k)]) + 2 for k in fields]
    SEPARATOR = "+%s+" % "+".join("-" * w for w in column_widths)
    print(SEPARATOR)
    print("|%s|" % "|".join(h.center(w) for h, w in zip(fields, column_widths)))
    print(SEPARATOR)
    for d in data:
        print("|%s|" % "|".join((" " + d[k]).ljust(w) for k, w in zip(fields, column_widths)))
    print(SEPARATOR)


reports = {
    "registration": (fetch_registration, ("system_id", "hostname", "last_check_in", "created_at", "unregistered_at")),
    "reports": (fetch_reports, ("system_id", "hostname", "rule_id")),
    "stale": (fetch_stale, ("system_id", "hostname", "last_check_in"))
}

if __name__ == "__main__":
    args = parse_args()

    try:
        fetch, headers = reports[args.report]
        data = fetch(get_creds(args), args.account)
        if args.tsv:
            report_tsv(data, headers)
        else:
            report_console(data, headers)
    except InsightsError as e:
        print(e)
        sys.exit(1)
