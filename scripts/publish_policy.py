"""Skip publication when a validated main candidate has been superseded."""

import sys


def should_publish(event, ref, candidate, head):
    return event == 'push' and ref == 'refs/heads/main' and candidate == head


if __name__ == '__main__':
    print(str(should_publish(*sys.argv[1:])).lower())
