from datetime import datetime, timedelta
# import pytest


try:
    from src.utils import minifuncs as minif
except ModuleNotFoundError:
    from utils import minifuncs as minif


def test_ndays():
    # day difference function output
    fresult = minif.ndays()
    # today's date and day 3 months ago test
    today0 = datetime.now()
    month3 = today0 - timedelta(days=fresult)

    if today0.year != month3.year:
        assert today0.month == month3.month + 3 - 12
    else:
        assert today0.month == month3.month + 3
    assert today0.day == month3.day


if __name__ == '__main__':
    print('I only have API data ingestion, database and S3 related functions for now, none really testable.')
    # python3 -m pytest test/
    pass
