import bugsnag

rel_path = "./credentials.txt"


def get_credentials_by(service_name):
    with open(rel_path) as f:
        lines = [line.strip() for line in f.readlines()]
        for line in lines:
            data = line.split(' ')
            if data[0] == service_name:
                return data[1], data[2]

        bugsnag.notify(Exception("Credentials for service name were not found!"))

    f.close()
