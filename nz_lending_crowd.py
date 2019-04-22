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
loans_ids = []
req_execution_times = []
timeout = 30.0  # Sixty seconds
threads = []


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
            "text": "Go to https://lendingcrowd.co.nz/investment/loanlistings#lc-wrapper, there are new loans available"
        }
    )


# TASK THAT REMOVES LOANS FROM TODAY (WE ASSUME LOANS WILL BE FILLED IN 1 DAY)
def clean_loans():
    loans_ids = []


# TASK TO RETRIEVE NEW LOANS RUN EVERY MINUTE
def job():
    print('Running Job. Current DateTime:', datetime.datetime.today())

    response = send_auth_req()
    c = response.cookies  # RETRIEVE COOKIES INSIDE RESPONSE

    # USE COOKIE RESPONSE IN NEW REQUEST AS TOKEN
    response = send_loan_query(c)
    json_resp = json.loads(response.text)

    num_loans = json_resp['obj']['totalRecordCount']

    if num_loans != 0:
        new_loan_available = False
        for loan in json_resp['obj']['list']:
            print("Found Loan: " + loan)
            # if loan['id'] not in loans_ids:
            #     print("New Loan Available - Sending Email")
            #     loans_ids.append(loan['id'])
            #     new_loan_available = True

        # if new_loan_available:
        #     send_email()


# Create on separate thread so clock timed process not altered
def run_job_in_thread(job_to_run):
    job_thread = threading.Thread(target=job_to_run)
    job_thread.setDaemon(True)  # exit when main program exits, regardless of state
    job_thread.start()


def schedule_tasks():
    schedule.every(20).seconds.do(run_job_in_thread, job)
    schedule.every().day.at('18:00').do(clean_loans)


def execute_tasks():
    while True:
        schedule.run_pending()


def main():
    print('Starting Script')
    job()
    schedule_tasks()
    execute_tasks()


main()
