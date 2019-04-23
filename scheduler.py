import schedule
import threading


# Create on separate thread so clock timed process not altered
def run_job_in_thread(job_to_run):
    job_thread = threading.Thread(target=job_to_run)
    job_thread.setDaemon(True)
    job_thread.start()


def schedule_tasks(period, job):
    schedule.every(period).seconds.do(run_job_in_thread, job)


def execute_tasks():
    while True:
        schedule.run_pending()
