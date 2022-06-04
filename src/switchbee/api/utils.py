from datetime import datetime


def timestamp_now() -> int:
    """Returns the current timestamp."""
    return int(datetime.now().timestamp() * 1000)
