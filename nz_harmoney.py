import datetime
import json

import requests
import scheduler
import cacheing
import creds_parser

harmoney_email = harmoney_pwd = ""

# ALG_VARS
period = 10.0  # Called every 10 seconds
seen_loan_ids = []

# CACHE STORAGE
rel_path = "./cache/nz_harmoney.txt"
service_name = "Harmoney"


def send_auth_req():
    sign_in_url = "https://app.harmoney.com/accounts/sign_in"
    sign_in_payload = "{\n  \"branch\": \"NZ\",\n  \"account\": {\n    \"email\": \"" + harmoney_email + "\",\n    \"password\": \"" + harmoney_pwd + "\"\n\t}\n}"
    sign_in_headers = {
        'cookie': "_harmoney_session_id=SXB5MWh3VTZZdVVHZXVoT0FxKzI1WHRwRE8yVnk4QkVDbDhMTEJoUGFlZFJCeDhOdWlCVHFzZ2VReU1SQVFHTFYzdU0rc2lvdG1OVFBHZnRieWZPUWtFRUMrM3pqVEg1N3dPWkRUSTNMMFlWZi9yL0tQcDUyMXEzbWl0Yk5BWTIyMTlzanpYRGk2S3h3bmtybFJuMGNFVEdvRWkzV0VwSy9rWk9WdEllOHZMYjVWZmlkbUtPbFBERkhnTFNqbWRqV21WZy95MlAvbUdUWHZTRHlzalNGalFRQjhyWlhtTmlZUFlPOVZFZ20vUm4rUnBGNHFYYzVYK2xoamZXMk5VV2g3NmlpdU85cTAyZnN0TFRNWU1FUmZYaHV5Y1NZdWZsazZYR3UzZVBSc1ZxdG5TR2gwVldMUU1jV3FkZ0pzNlJqNFNBd1c2UjFVaDIrbmJMd0xEQmxUdWw3MUhaamozVnBrVnF4eFhoQ2YxRE5wWjJzQm1GekY1Q0lIbWt1RktKZTJYcXo3bUtnV2tHOXJhNmF3a3N6MTc1ZHFCN0FSanJqQTgwb3RMWWNsVUlSWkZLaDBuM3A0M1dWOTNUajVTN2tIeUsxWmNQc0VoV3JnczgyRUg2U0NQUHA2NlVvcnV4ZjNWQkRKUTRDdStaYTY0dmhGTTFVcUxOdm9LekNKZ0VDcVZYb091aTRkaFdwaUpkZlRjTGV4UU5OaEwxS3UrL05XR2t6TSt1dVUwPS0tWmEyRW5pLzhYVXh5MWZ1aDM1Q2cvQT09--dc79b054f8453fcc20e22a6263d276ebb3a56790",
        'user-agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/72.0.3626.121 Safari/537.36",
        'referer': "https://www.harmoney.co.nz/sign-in",
        'origin': "https://www.harmoney.co.nz",
        'content-type': "application/json",
        'accept': "application/json"
    }
    return requests.request("POST", sign_in_url, data=sign_in_payload, headers=sign_in_headers)


def send_loan_query(cookie):
    # GET LOANS
    get_loans_url = "https://app.harmoney.com/api/v1/investor/marketplace/loans"
    get_loans_querystring = {"limit": "100", "offset": "0"}
    headers = {
        'pragma': "no-cache",
        'host': "app.harmoney.com",
        'dnt': "1",
        'connection': "keep-alive",
        'cache-control': "no-cache",
        'accept-encoding': "gzip, deflate, br",
        'accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        'user-agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/72.0.3626.121 Safari/537.36",
        'content-type': "'application/x-www-form-urlencoded'"
    }
    return requests.request("GET", get_loans_url, cookies=cookie, headers=headers, params=get_loans_querystring)


def build_email_body(loan_details):
    email_body = "<!DOCTYPE html><html>" \
                 "<p>Hello,</p>" \
                 "<p>A new loan has just been listed, please sign in and review the loan if you're interested in " \
                 "investing.</p>" \
                 "<p>Go to https://www.harmoney.co.nz to log-in and view the new loan</p>"

    email_body += "<br><p><b>Loan Details:</b></p>"

    for loan_info in loan_details:
        email_body += \
            "<p>Loan Grade: <b>" + loan_info['grade'] + "</b></p>" \
                                                        "<p>Interest Rate: <b>" + str(
                loan_info['interest_rate']) + "% </b></p>" \
                                              "<p>Loan Amount :<b> $" + str(loan_info['loan_amount']) + "</b></p>" \
                                                                                                        "<p>Percentage Funded: <b>" + str(
                loan_info['percentage_funded']) + "%</b></p>" \
                                                  "<p>Term Length: <b>" + str(loan_info['term_length']) + "</b></p>" \
                                                                                                          "<p>Purpose: <b>" + \
            loan_info['purpose'] + "</b></p>"

    email_body += "<br><p>Regards,</p>"
    email_body += "<p>Chris Connolly</p>"
    email_body += "</html>"

    return email_body


def send_email(loan_details):
    email_body = build_email_body(loan_details)
    requests.post(
        "https://api.mailgun.net/v3/p2pnotifications.live/messages",
        auth=("api", "1a2813ec74c4f9982f080a41b4c7d19c-985b58f4-5ebf0053"),
        data={
            "from": "New Loans <harmoneynotifications@p2pnotifications.live>",
            "to": ["testing@p2pnotifications.live"],
            "subject": "New Loan Available on Harmoney",
            "html": email_body
        }
    )


# If the ID of a stored loan doesn't exist in a response,
# we can assume its been filled and can remove it.
def remove_old_loans(response):
    global seen_loan_ids
    loans_after_removal = []

    for stored_loan_id in seen_loan_ids:
        in_response = False
        for loan_from_req in response['items']:
            if stored_loan_id == loan_from_req['id']:
                in_response = True
                break

        if in_response:
            loans_after_removal.append(stored_loan_id)

    seen_loan_ids = loans_after_removal


# TASK TO RETRIEVE NEW LOANS RUN EVERY MINUTE
def get_loans():
    response = send_auth_req()
    c = response.cookies  # RETRIEVE COOKIE INSIDE RESPONSE

    # USE COOKIE RESPONSE IN NEW REQUEST AS TOKEN
    response = send_loan_query(c)
    json_resp = json.loads(response.text)

    return json_resp


def get_new_loans(response):
    global seen_loan_ids
    # Have we seen it before?
    new_loan_avail = False
    new_loan_details = []
    for loan in response['items']:
        if loan['id'] not in seen_loan_ids:
            seen_loan_ids.append(loan['id'])
            loan_info = {
                'grade': loan['grade'],
                'interest_rate': loan['interest_rate'],
                'loan_amount': loan['amount'],
                'term_length': str(loan['term']) + " months",
                'purpose': loan['loan_purpose'],
                'percentage_funded': round(float(loan['amount_funded']) / float(loan['amount']) * 100, 2)
            }
            new_loan_details.append(loan_info)
            new_loan_avail = True

    return new_loan_avail, new_loan_details


def job():
    print("Running", service_name, "Job. Current DateTime:", datetime.datetime.today())

    response = get_loans()
    loan_available = response['total_count'] != 0
    if loan_available:
        new_loan_avail, new_loan_details = get_new_loans(response)

        if new_loan_avail:
            print("Sending", service_name, "email at", datetime.datetime.today())
            send_email(new_loan_details)

    # Remove old loans
    remove_old_loans(response)
    cacheing.update_cache(rel_path, seen_loan_ids)


def init():
    print("Initialising", service_name, "Script")
    global seen_loan_ids
    seen_loan_ids = cacheing.init_cache(rel_path)

    # Load credentials into memory
    global harmoney_email, harmoney_pwd
    harmoney_email, harmoney_pwd = creds_parser.get_credentials_by(service_name)
    print("Finished Initialising", service_name, "Script")

    # Schedule tasks
    scheduler.schedule_tasks(period, job)


def send_test_dict_email():
    f = open('./samples/nz_harmoney.txt')
    response = eval(f.read().strip())
    new_loan_avail, new_loan_details = get_new_loans(response)
    send_email(new_loan_details)
    assert new_loan_avail is True and new_loan_details != []


send_test_dict_email()
