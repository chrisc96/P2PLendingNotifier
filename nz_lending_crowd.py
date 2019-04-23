import argparse
import datetime
import json
import threading

import requests
import schedule

# CLI Parsing
parser = argparse.ArgumentParser(description='Provide credentials to connect to LendingCrowd')
parser.add_argument('--lc_email', help='The email address you use to login to LendingCrowd')
parser.add_argument('--lc_password', help='The password you use to login to LendingCrowd')
args = parser.parse_args()

args.lc_email = str(args.lc_email)
args.lc_password = str(args.lc_password)

# ALG_VARS
seen_loan_ids = []
period = 5.0  # every 5 seconds
threads = []

# CACHE STORAGE
rel_path = "./cache/nz_lending_crowd.txt"


def send_auth_req():
    sign_in_url = "https://lendingcrowd.co.nz/user/signin"
    sign_in_payload = "{\n\t\"userName\":\"" + args.lc_email + "\",\n\t\"password\":\"" + args.lc_password + "\"," \
                                                                                                             "\n\t\"recaptchaResponseToken\":\"_lc\"\n} "
    sign_in_headers = {
        'cookie': "Lc=s6Mt93N0n8t875ge3mRk3gAs5HSBhdJbavtjB1bvC3uxvc5rAoYm5yuRdkPewd5Tmia4PwQi0VCPKEwe47paGz"
                  "-gYgl3mrwVbdk0cXX2YvFlZbfL1jeVK3fOeQjiMM0DyDjpjKkHRb--Be1BC_1XIQC5okA1;",
        'accept-encoding': "gzip, deflate, br",
        'accept-language': "en-GB,en-US;q=0.9,en;q=0.8'",
        'dnt': "1",
        'referer': "https://lendingcrowd.co.nz/user/signinform",
        'cache-control': "no-cache",
        'accept': "application/json, text/plain, */*",
        'x-lc-app': "true",
        'user-agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/73.0.3683.86 Safari/537.36",
        'pragma': "no-cache",
        'connection': "keep-alive",
        'origin': "https://lendingcrowd.co.nz",
        'x-lc-rvt': "B45844B2-C2FC-4E56-B879-327327440711",
        'content-type': "application/json"
    }
    return requests.request("POST", sign_in_url, data=sign_in_payload, headers=sign_in_headers)


def send_loan_query(cookies):
    # GET LOANS
    global auth_cookie_val

    get_loans_url = "https://lendingcrowd.co.nz/investment/readloanlistings"
    get_loans_querystring = {"investmentAccountId": "11866", "page": "1", "pageSize": "25"}

    for cookie in cookies:
        if cookie.name == "LcAuth":
            auth_cookie_val = cookie.value
            break

    cookie_val = "Lc=PUFjH_fnuZrEFBMkv-l04VkDsPZWEtpvN5h_Qjy_F8EytVQT-OZwaQ3g-cfBVGU2WWT7" \
                 "-HssSbkoKTYFCehynCnnevpT7kvfIEHrfIj3Cvx9ai0rPDXBQVldriyJp8KyOFwmdOJlACdNDE2CK8fge_g1qcc1; " \
                 "ga=GA1.3.693003326.1555112991; _gid=GA1.3.39202581.1555112991; LcAuth=" + auth_cookie_val + ";"

    headers = {
        'cookie': cookie_val,
        'connection': "keep-alive",
        'referer': "https://lendingcrowd.co.nz/investment/myinvestments",
        'cache-control': "no-cache",
        'accept': "application/json, text/plain, */*",
        'x-lc-app': "true",
        'user-agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/73.0.3683.86 Safari/537.36",
        'accept-language': "en-GB,en-US;q=0.9,en;q=0.8",
        'accept-encoding': "gzip, deflate, br",
        'dnt': "1",
        'x-lc-rvt': "B45844B2-C2FC-4E56-B879-327327440711",
        'pragma': "no-cache"
    }
    return requests.request("GET", get_loans_url, headers=headers, params=get_loans_querystring)


def send_email():
    requests.post(
        "https://api.mailgun.net/v3/p2pnotifications.live/messages",
        auth=("api", "1a2813ec74c4f9982f080a41b4c7d19c-985b58f4-5ebf0053"),
        data={
            "from": "Lending Crowd - New Loan Notifier <lendingcrowd@p2pnotifications.live>",
            "to": ["lendingcrowd@p2pnotifications.live"],
            "subject": "New Loan Available on Lending Crowd",
            "text": "Go to https://lendingcrowd.co.nz, there are new loans available"
        }
    )


# TASK TO RETRIEVE NEW LOANS RUN EVERY MINUTE
def get_loans():
    response = send_auth_req()
    c = response.cookies  # RETRIEVE COOKIES INSIDE RESPONSE

    # USE COOKIE RESPONSE IN NEW REQUEST AS TOKEN
    response = send_loan_query(c)
    json_resp = json.loads(response.text)

    return json_resp


def check_for_new_loans(response):
    global seen_loan_ids

    # Have we seen it before?
    loan_not_seen_before = False
    for loan in response['obj']['list']:
        if loan['id'] not in seen_loan_ids:
            seen_loan_ids.append(loan['id'])
            loan_not_seen_before = True

    return loan_not_seen_before


# If the ID of a stored loan doesn't exist in a response,
# we can assume its been filled and can remove it.
def remove_old_loans(response):
    global seen_loan_ids
    loans_after_removal = []

    for stored_loan_id in seen_loan_ids:
        in_response = False
        for loan_from_req in response['obj']['list']:
            if stored_loan_id == loan_from_req['id']:
                in_response = True
                break

        if in_response:
            loans_after_removal.append(stored_loan_id)

    seen_loan_ids = loans_after_removal


def job():
    print('Running Job. Current DateTime:', datetime.datetime.today())

    response = get_loans()
    num_loans = response['obj']['totalRecordCount']

    if num_loans != 0:
        loan_not_seen_before = check_for_new_loans(response)

        if loan_not_seen_before:
            print("Sending Email at", datetime.datetime.today())
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
    print(seen_loan_ids)
    print("Done.")


def main():
    init_cache()

    print('Starting Script')
    schedule_tasks()
    execute_tasks()


main()
