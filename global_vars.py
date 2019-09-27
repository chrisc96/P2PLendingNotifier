import bugsnag
import os
import environment

# Exception Handling
def init_bugsnag():
    global bugsnag_conf
    bugsnag_conf = bugsnag.configure(
        api_key=os.getenv("BS_API_KEY"),
    )
    
    if environment.curr_environment == environment.Environment.TESTING:
        bugsnag_conf.configure(release_stage = "development")
    else:
        bugsnag_conf.configure(release_stage = "production")
