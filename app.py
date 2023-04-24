from flask import Flask, render_template
import requests
import json
from collections import defaultdict
from datetime import datetime

app = Flask(__name__, static_url_path='/static')

# Paste the API-key you have received as the value for "x-api-key"
headers = {
    "Content-Type": "application/json",
    "Accept": "application/hal+json",
    "x-api-key": "860393E332148661C34F8579297ACB000E15F770AC4BD945D5FD745867F590061CAE9599A99075210572"
}


base_url_deal = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/deal/"
base_url_company = "https://api-test.lime-crm.com/api-test/api/v1/limeobject/company/"
params = "?max-closeddate=2022-12-31T00:00:00&min-closeddate=2022-01-01T00:00:00"
params2 = "?max-closeddate=2022-01-01T00:00:00"

# Function for REST API call to get data from Lime


def get_api_data(headers, url):
    # First call to get first data page from the API
    response = requests.get(url=url,
                            headers=headers,
                            data=None,
                            verify=False)

    # Convert response string into json data and get embedded limeobjects
    json_data = json.loads(response.text)
    limeobjects = json_data.get("_embedded").get("limeobjects")

    # Note, se mer om pagination/next i api dokumentionen
    # Check for more data pages and get thoose too
    nextpage = json_data.get("_links").get("next")
    while nextpage is not None:
        url = nextpage["href"]
        response = requests.get(url=url,
                                headers=headers,
                                data=None,
                                verify=False)

        json_data = json.loads(response.text)
        limeobjects += json_data.get("_embedded").get("limeobjects")
        nextpage = json_data.get("_links").get("next")

    return limeobjects


def getClosedResponseDeals(response_deals):
    for deal in response_deals:
        if deal["dealstatus"]["text"] != "4. Avtal":
            response_deals.remove(deal)
    return response_deals


def getAverageValue(response_deals):
    total_value = 0.0
    for deal in response_deals:
        total_value += deal["value"]

    return round(total_value/len(response_deals))


def getDealsInfo(response_deals):
    # Initialize months dictionary with all months and set their values to 0
    # Format {'jan': {'numOfDeals': 0, 'totalDealValue': 0}}
    months = {datetime(2000, m, 1).strftime("%b").lower(): {
        "numOfDeals": 0, "totalDealValue": 0} for m in range(1, 13)}

    for deal in response_deals:
        dt = datetime.fromisoformat(deal["closeddate"])
        month_name = dt.strftime("%b").lower()
        months[month_name]["numOfDeals"] += 1
        months[month_name]["totalDealValue"] += round(deal["value"])

    return [{month: data} for month, data in months.items()]


def getCustomerInfo(closed_response_deals, response_companies):

    companies = defaultdict(int)

    # Sum up the total value of for each companys deals
    for deal in closed_response_deals:
        companies[deal["company"]] += round(deal["value"])

    # Replace old_key with company name, for instance the key "1010" => "Culinar AB (Demo)"
    for deal in closed_response_deals:
        for company in response_companies:
            if company["_id"] == deal["company"] and deal["company"] in companies:
                old_key_value = companies.pop(deal["company"])
                companies.update({company["name"]: old_key_value})

    return [{company_name: deals_value} for company_name, deals_value in companies.items()]


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/deals')
def deals():

    # API call to get deals
    response_deals = get_api_data(headers=headers, url=base_url_deal + params)
    # API call to get companies
    response_companies = get_api_data(headers=headers, url=base_url_company)

    closed_response_deals = getClosedResponseDeals(response_deals)
    average_value = getAverageValue(closed_response_deals)
    deals_year_list = getDealsInfo(closed_response_deals)
    deals_per_customer_list = getCustomerInfo(
        closed_response_deals, response_companies)

    if len(response_deals) > 0:
        return render_template('deals.html', average_value=average_value, deals_year_list=deals_year_list, deals_per_customer_list=deals_per_customer_list)
    else:
        msg = 'No deals found'
        return render_template('deals.html', msg=msg)


@ app.route('/company')
def company():
    response_deals_2022 = get_api_data(
        headers=headers, url=base_url_deal + params)
    closed_response_deals = getClosedResponseDeals(response_deals_2022)
    response_companies = get_api_data(headers=headers, url=base_url_company)
    response_deals_without_2022 = get_api_data(
        headers=headers, url=base_url_deal + params2)

    # Sets are commonly used for tasks such as removing duplicates from a list
    unique_keys = set()
    companies_status = []

    # Create a list of all the companies with the stucture [{"Lundalogic AB" : "inactive"}, ...]
    # without adding duplicates
    for company in response_companies:
        if company["name"] not in unique_keys:
            unique_keys.add(company["name"])
            companies_status.append({company["name"]: "inactive"})

    deals_per_customer_list = getCustomerInfo(
        closed_response_deals, response_companies)

    # Set all values to "customer"
    for customer_deal in deals_per_customer_list:
        for key in customer_deal:
            customer_deal[key] = "customer"

    if len(response_companies) > 0:
        return render_template('company.html', deals_per_customer_list=deals_per_customer_list, companies_status=companies_status)
    else:
        msg = 'No deals found'
        return render_template('company.html', msg=msg)


# DEBUGGING
"""
If you want to debug your app, one of the ways you can do that is to use:
import pdb; pdb.set_trace()
Add that line of code anywhere, and it will act as a breakpoint and halt
your application
"""

if __name__ == '__main__':
    app.secret_key = 'somethingsecret'
    app.run(debug=True)
