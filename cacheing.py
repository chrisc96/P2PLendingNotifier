def update_cache(rel_path, seen_loan_ids):
    f = open(rel_path, 'w+')
    for i in range(len(seen_loan_ids)):
        if i + 1 == len(seen_loan_ids):
            f.write(str(seen_loan_ids[i]))
        else:
            f.write(str(seen_loan_ids[i]) + ",")

    f.close()


# Create file if loan cache doesn't exist
def load_from_cache(rel_path):
    f = open(rel_path, 'a+')
    f.seek(0)

    loan_ids = []
    if f.read() != '':
        f.seek(0)
        for loan_id in f.read().split(','):
            loan_ids.append(int(loan_id))

    f.close()
    return loan_ids


def init_cache(rel_path):
    return load_from_cache(rel_path)
