import datetime
import json

import requests
import os

import cacheing
import creds_parser
import scheduler
import environment

lc_email = lc_password = ""

# ALG_VARS
period = 60.0  # Called every 60 seconds to reduce load
seen_loan_ids = []

# CACHE STORAGE
rel_path = "./cache/nz_lending_crowd.txt"
service_name = "LendingCrowd"


def send_auth_req():
    sign_in_url = "https://lendingcrowd.co.nz/user/signin"
    sign_in_payload = "{\n\t\"userName\":\"" + lc_email + "\",\n\t\"password\":\"" + lc_password + "\"," \
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
    who_from, who_to, subject, = environment.get_mail_metadata_from_platform_name(service_name)

    requests.post(
        "https://api.mailgun.net/v3/p2pnotifications.live/messages",
        auth=("api", os.getenv("MG_API_KEY")),
        data={
            "from": who_from,
            "to": who_to,
            "subject": subject,
            "text": "Go to https://lendingcrowd.co.nz, there are new loans available"
        }
    )


# TASK TO RETRIEVE NEW LOANS RUN EVERY MINUTE
def get_loans():
    response = send_auth_req()

    lc_down = response.status_code == 404
    if lc_down:
        exit(0)

    # USE COOKIE RESPONSE IN NEW REQUEST AS TOKEN
    c = response.cookies  # RETRIEVE COOKIES INSIDE RESPONSE
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
    print("Running", service_name, "Job. Current DateTime:", datetime.datetime.today())

    response = get_loans()
    num_loans = response['obj']['totalRecordCount']

    if num_loans != 0:
        loan_not_seen_before = check_for_new_loans(response)
        print(loan_not_seen_before)
        if loan_not_seen_before:
            print("Sending", service_name, "email at", datetime.datetime.today())
            print(response)
            send_email()

    # Remove old loans
    remove_old_loans(response)
    cacheing.update_cache(rel_path, seen_loan_ids)


def init():
    print("Initialising", service_name, "Script")
    global seen_loan_ids
    seen_loan_ids = cacheing.init_cache(rel_path)

    # Load credentials into memory
    global lc_email, lc_password
    lc_email, lc_password = creds_parser.get_credentials_by(service_name)
    print("Finished Initialising", service_name, "Script")

    # Schedule tasks
    scheduler.schedule_tasks(period, job)
