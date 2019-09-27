from enum import Enum

class Environment(Enum):
    TESTING = 0,
    PRODUCTION = 1,


curr_environment = Environment.PRODUCTION


def get_mail_metadata_from_platform_name(platform_name):
    if curr_environment == Environment.TESTING:
        who_from = "New Loans <testing@p2pnotifications.live>"
        who_to = "testing@p2pnotifications.live"
        subject = "[TESTING] New Loan Available on Harmoney"

        return who_from, who_to, subject
    else:
        platform_name = str(platform_name).lower()
        who_from = who_to = "New Loans <" + platform_name + "@p2pnotifications.live>"
        subject = "New Loan Available on Harmoney"

        return who_from, who_to, subject
