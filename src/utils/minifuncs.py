from datetime import datetime


def ndays(nmonth=3):
    """
        Function to calculate the number days between today and the same day n months ago.
        Args:
            nmonth: number of months ago to calculate the day differences
        Returns:
            integer indicating the number of days
    """
    today0 = datetime.now()
    year3, month3 = (today0.year, today0.month - nmonth) if today0.month - nmonth >= 1 \
        else (today0.year - 1, today0.month - nmonth + 12)
    date3 = datetime(year3, month3, today0.day)
    ndays = (today0 - date3).days

    return ndays
