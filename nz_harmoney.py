import datetime
import json

import argparse
import requests
import schedule
import threading

# CLI PARSING
parser = argparse.ArgumentParser(description='Provide credentials to connect to Harmoney')
parser.add_argument('--harmoney_email', help='The email address you use to login to Harmoney')
parser.add_argument('--harmoney_pwd', help='The password you use to login to Harmoney')
args = parser.parse_args()

args.harmoney_email = str(args.harmoney_email)
args.harmoney_pwd = str(args.harmoney_pwd)

# ALG_VARS
period = 20.0  # Called every 20 seconds
seen_loan_ids = []
threads = []

# CACHE STORAGE
rel_path = "./cache/nz_harmoney.txt"


def send_auth_req():
    sign_in_url = "https://app.harmoney.com/accounts/sign_in"
    sign_in_payload = "{\n  \"branch\": \"NZ\",\n  \"account\": {\n    \"email\": \"" + args.harmoney_email + "\",\n    \"password\": \"" + args.harmoney_pwd + "\"\n\t}\n}"
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


def send_email():
    requests.post(
        "https://api.mailgun.net/v3/p2pnotifications.live/messages",
        auth=("api", "1a2813ec74c4f9982f080a41b4c7d19c-985b58f4-5ebf0053"),
        data={
            "from": "Harmoney - New Loan Notifier <harmoney@p2pnotifications.live>",
            "to": ["testing@p2pnotifications.live"],
            "subject": "New Loan on Harmoney",
            "text": "Go to https://www.harmoney.co.nz/lender/portal/invest/marketplace/browse, there are new loans "
                    "available."
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


def check_for_new_loans(response):
    global seen_loan_ids
    # Have we seen it before?
    loan_not_seen_before = False
    for loan in response['items']:
        if loan['id'] not in seen_loan_ids:
            print("New Loan Available - Sending Email")
            seen_loan_ids.append(loan['id'])
            loan_not_seen_before = True

    return loan_not_seen_before


def job():
    print('Running Job. Current DateTime:', datetime.datetime.today())

    response = get_loans()
    num_loans = response['total_count']

    # Loan Available
    if num_loans != 0:
        loan_not_seen_before = check_for_new_loans(response)

        if loan_not_seen_before:
            send_email()

    # Remove old loans
    remove_old_loans(response)
    update_cache()


# Create on separate thread so clock timed process not altered
def run_job_in_thread(job_to_run):
    job_thread = threading.Thread(target=job_to_run)
    job_thread.setDaemon(True)  # exit when main program exits, regardless of state
    job_thread.start()


def schedule_tasks():
    schedule.every(period).seconds.do(run_job_in_thread, job)


def execute_tasks():
    while True:
        schedule.run_pending()


def update_cache():
    f = open(rel_path, 'w+')
    for i in range(len(seen_loan_ids)):
        if i + 1 == len(seen_loan_ids):
            f.write(str(seen_loan_ids[i]))
        else:
            f.write(str(seen_loan_ids[i]) + ",")

    f.close()
    pass


# Create file if loan cache doesn't exist
def load_from_cache():
    f = open(rel_path, 'a+')
    f.seek(0)

    loan_ids = []
    if f.read() != '':
        f.seek(0)
        for loan_id in f.read().split(','):
            loan_ids.append(int(loan_id))

    f.close()
    return loan_ids


def init_cache():
    print("Loading Cache")
    global seen_loan_ids
    seen_loan_ids = load_from_cache()
    print("Done.")


def main():
    init_cache()

    print('Starting Script')
    schedule_tasks()
    execute_tasks()


main()
