import time
import bugsnag
import os

from dotenv import load_dotenv

import scheduler
from nz_harmoney import init as harmoney_init

services = [harmoney_init]


def init_bugsnag():
    # Exception Handling
    bugsnag.configure(
        api_key=os.getenv("BS_API_KEY"),
    )


# Create each notification system in a new thread
def init_notification_services():
    for service in services:
        scheduler.run_job_in_thread(service())
        time.sleep(2)


def execute_notification_services():
    scheduler.execute_tasks()


def run():
    load_dotenv()
    init_bugsnag()
    init_notification_services()
    execute_notification_services()


run()
