import re
from datetime import date

def extract_filename_date(filename: str):
    """
    Extract date from filename in format: *_YYYYMMDD.ext or *_YYYY-MM-DD.ext

    Parameters
    ----------
    filename : str
        The filename to extract date from

    Returns
    -------
    date or None
        The extracted date object, or None if no valid date found
    """
    # Pattern to match _YYYYMMDD or _YYYY-MM-DD before file extension
    # Handles both formats: _20210901.txt and _2021-09-01.txt
    pattern = r'_(\d{4})-?(\d{2})-?(\d{2})\.\w+$'

    match = re.search(pattern, filename)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))

        try:
            return date(year, month, day)
        except ValueError:
            # Invalid date (e.g., Feb 30)
            return None

    return None