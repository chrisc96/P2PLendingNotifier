from enum import Enum


class Environment(Enum):
    TESTING = 0,
    PRODUCTION = 1,


curr_environment = Environment.TESTING


def get_mail_metadata_from_platform_name(platform_name):
    if curr_environment == Environment.TESTING:
        return "New Loans <testing@p2pnotifications.live>", \
               "testing@p2pnotifications.live", \
               "[TESTING] New Loan Available on Harmoney"
    else:
        platform_name = str(platform_name).lower()
        who_from = who_to = platform_name + "@p2pnotifications.live"
        subject = "New Loan Available on Harmoney"

        return who_from, who_to, subject
