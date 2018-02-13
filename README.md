# Insights Account Reports

## NOTE: This script is not supported in any official capacity.

This script gives Red Hat customers the ability to view information about their systems registered to Insights.  Currently there are only a couple of reports:

- **registration**: List registration status of all systems (for all time) in an account
- **reports**: Listing of all the current "rule hits" for every system in the account

## Installation

```
pip install -r requirements.txt
```

## Running

Example:

```
./insights_account_reports.py --username "" --password "" registration
```

Or you can use a file to store your credentials:

```
./insights_account_reports.py --creds-file userpass.txt reports
```
