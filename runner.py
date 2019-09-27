import time
import os

from dotenv import load_dotenv

import scheduler
import global_vars
import nz_harmoney as nz_harmoney

services = [nz_harmoney]


# Create each notification system in a new thread
def init_notification_services():
    for service in services:
        scheduler.run_job_in_thread(service.init())
        time.sleep(2)


def execute_notification_services():
    scheduler.execute_tasks()


def run():
    load_dotenv()
    global_vars.init_bugsnag()
    # services[0].send_test_dict_email()
    init_notification_services()
    execute_notification_services()


run()
