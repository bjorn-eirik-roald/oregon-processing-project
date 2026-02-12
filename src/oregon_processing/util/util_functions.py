import re
from datetime import date

def extract_filename_date(filename: str):
    """
    Extract date from filename in format: *_YYYY_MM_DD.ext

    Parameters
    ----------
    filename : str
        The filename to extract date from

    Returns
    -------
    date or None
        The extracted date object, or None if no valid date found
    """
    # Pattern to match _YYYY_MM_DD before file extension
    pattern = r'_(\d{4})_(\d{2})_(\d{2})\.\w+$'

    match = re.search(pattern, filename)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))

        try:
            return date(year, month, day)
        except ValueError:
            raise ValueError(f"Date components extracted from filename are not valid: {year}-{month}-{day}")
    else:
        raise ValueError(f"Filename does not contain a valid date in the expected format: {filename}")