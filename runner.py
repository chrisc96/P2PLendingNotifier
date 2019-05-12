from nz_harmoney import init as harmoney_init
from nz_lending_crowd import init as lending_crowd_init

from dotenv import load_dotenv
import scheduler
import bugsnag
import os
import time

services = [harmoney_init]


def init_bugsnag():
    # Exception Handling
    bugsnag.configure(
        api_key="94ce4de185d75d1385a4b3eaace1996c",
        project_root="./",
        notify_release_stages=["production"],
        release_stage=os.getenv("RELEASE_STAGE") or "production"
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
