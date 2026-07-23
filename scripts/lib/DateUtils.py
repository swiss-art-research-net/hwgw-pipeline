import time
import re
try:
    from edtf import parse_edtf  # type: ignore[import-not-found]
except ImportError:
    parse_edtf = None

def convertEDTFdate(date):
    """
    Convert an edtf date string to a dictionary with lower and upper date values.
    """
    if parse_edtf is None:
        raise ImportError("Missing dependency: edtf")

    try:
        d = parse_edtf(downgradeEDTF(date))
    except:
        raise ValueError('Invalid date', date)
    
    if 'Interval' in str(type(d)):
        if type(d.lower) is list:
            lower = d.lower[0].lower_strict()
        else:
            lower = d.lower.lower_strict()
        if type(d.upper) is list:
            upper = d.upper[0].upper_strict()
        else:
            upper = d.upper.upper_strict()
    else:
        if type(d) is list:
            lower = d[0].lower_strict()
            upper = d[0].upper_strict()
        else:
            lower = d.lower_strict()
            upper = d.upper_strict()
    return {
        'lower': time.strftime("%Y-%m-%d", lower),
        'upper': time.strftime("%Y-%m-%d", upper)
    }


def _format_year(year):
    """
    Format a year as xsd:gYear lexical form.
    Uses signed 4+ digit year, e.g. 1500, -0084.
    """
    year = int(year)
    if year < 0:
        return f"-{abs(year):04d}"
    return f"{year:04d}"


def _normalize_text(raw):
    txt = (raw or '').strip()
    txt = txt.replace('—', '-').replace('–', '-')
    txt = re.sub(r'\s+', ' ', txt)
    return txt


def _extract_century_range(text):
    lower_text = text.lower()
    century_match = re.search(r'(\d{1,2})\.?\s*(jahrhundert|jh\.)', lower_text)
    if not century_match:
        return None

    century = int(century_match.group(1))
    bce = bool(re.search(r'v\.?\s*chr\.?', lower_text))
    first_half = bool(re.search(r'1\.\s*h\.', lower_text))
    second_half = bool(re.search(r'2\.\s*h\.', lower_text))

    if bce:
        start = -century * 100
        end = -(century - 1) * 100 - 1
    else:
        start = (century - 1) * 100
        end = century * 100 - 1

    if first_half:
        end = start + 49
    elif second_half:
        start = start + 50

    return start, end, bce


def normalize_object_date(raw_date):
    """
    Normalize free-text object dates into structured bounds and lightweight EDTF.
    The original value must always be preserved by the caller.
    """
    original = raw_date or ''
    text = _normalize_text(original)

    result = {
        'original': original,
        'normalized_text': text,
        'edtf': None,
        'lower': None,
        'upper': None,
        'precision': None,
        'approximate': False,
        'uncertain': False,
        'bce': False,
        'disjunction': False,
        'open_interval': False,
        'parse_status': 'fail',
        'note': ''
    }

    if not text:
        result['parse_status'] = 'unknown'
        result['note'] = 'empty'
        return result

    if text.lower() in {'o.j.', 'ohne jahr'}:
        result['parse_status'] = 'unknown'
        result['precision'] = 'unknown'
        result['note'] = 'no date marker'
        return result

    # Strip editorial notes like {HW: 1513} but keep note info.
    brace_notes = re.findall(r'\{([^}]*)\}', text)
    if brace_notes:
        text = re.sub(r'\{[^}]*\}', '', text).strip()
        text = re.sub(r'\s+', ' ', text)
        result['normalized_text'] = text
        result['note'] = '; '.join(brace_notes)

    lower_text = text.lower()
    result['approximate'] = bool(re.search(r'\bum\b|\bca\.?\b|\bcirca\b', lower_text))
    result['uncertain'] = '?' in text
    result['bce'] = bool(re.search(r'v\.?\s*chr\.?', lower_text))
    result['disjunction'] = ('/' in text) or bool(re.search(r'\border\b|\boder\b|\bu\.', lower_text))

    # Remove uncertainty marks and approximation words for numeric extraction.
    cleaned = re.sub(r'\(\?\)|\?', '', text)
    cleaned = re.sub(r'\bum\b|\bca\.?\b|\bcirca\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Century expressions first.
    century_range = _extract_century_range(cleaned)
    if century_range is not None:
        year_start, year_end, _ = century_range
        result['precision'] = 'century'
        result['lower'] = _format_year(min(year_start, year_end))
        result['upper'] = _format_year(max(year_start, year_end))
        result['parse_status'] = 'ok'
        result['edtf'] = f"{min(year_start, year_end):04d}/{max(year_start, year_end):04d}"
        return result

    before_match = re.search(r'\bvor\s+(\d{3,4})\b', cleaned.lower())
    after_match = re.search(r'\bnach\s+(\d{3,4})\b', cleaned.lower())

    # Preserve explicitly signed numeric years from attributes like when="-0106".
    signed_years = [int(y) for y in re.findall(r'(?<!\d)-\d{1,4}(?!\d)', cleaned)]

    # Extract unsigned long years, but do not treat the digits of a signed year
    # as a separate positive token.
    unsigned_long_years = []
    for match in re.finditer(r'\b(\d{3,4})\b', cleaned):
        if match.start() > 0 and cleaned[match.start() - 1] == '-':
            # Treat as a signed year only when '-' is not a range separator
            # between digits (e.g. keep 1511 in "1508-1511").
            if match.start() == 1 or not cleaned[match.start() - 2].isdigit():
                continue
        unsigned_long_years.append(int(match.group(1)))

    years = signed_years + unsigned_long_years

    if before_match:
        y = int(before_match.group(1))
        result['open_interval'] = True
        result['upper'] = _format_year(y - 1)
        result['precision'] = 'open'
        result['edtf'] = f"../{y - 1:04d}"
        result['parse_status'] = 'partial'
        return result

    if after_match:
        y = int(after_match.group(1))
        result['open_interval'] = True
        result['lower'] = _format_year(y + 1)
        result['precision'] = 'open'
        result['edtf'] = f"{y + 1:04d}/.."
        result['parse_status'] = 'partial'
        return result

    if not years:
        # Some historical dates are recorded with 1-2 digits (e.g., "39", "17/18 n.Chr.").
        has_explicit_ce = bool(re.search(r'n\.?\s*chr\.?|a\.?\s*d\.?', lower_text))
        is_plain_short_year = bool(re.fullmatch(r'\d{1,2}', cleaned))
        if result['bce'] or has_explicit_ce or is_plain_short_year:
            years = [int(y) for y in re.findall(r'\b(\d{1,2})\b', cleaned)]

    if not years:
        result['parse_status'] = 'unknown'
        result['precision'] = 'unknown'
        result['note'] = (result['note'] + '; ' if result['note'] else '') + 'no year token found'
        return result

    if any(y < 0 for y in years):
        result['bce'] = True

    # If BCE is marked textually (e.g., "v.Chr.") and years are unsigned,
    # apply BCE sign once.
    if result['bce'] and all(y >= 0 for y in years):
        years = [-abs(y) for y in years]

    year_start = min(years)
    year_end = max(years)

    lower_year = min(year_start, year_end)
    upper_year = max(year_start, year_end)
    result['lower'] = _format_year(lower_year)
    result['upper'] = _format_year(upper_year)

    if lower_year == upper_year:
        result['precision'] = 'year'
        edtf_value = f"{lower_year:04d}"
    else:
        result['precision'] = 'range'
        edtf_value = f"{lower_year:04d}/{upper_year:04d}"

    if result['approximate'] and '/' not in edtf_value:
        edtf_value += '~'
    elif result['uncertain'] and '/' not in edtf_value:
        edtf_value += '?'

    result['edtf'] = edtf_value
    result['parse_status'] = 'ok'
    return result


def parse_date_with_fallback(raw_date):
    """
    Parse a free-text date using local normalization first and return EDTF when possible.
    """
    normalized = normalize_object_date(raw_date)
    return normalized.get('edtf')
    
def downgradeEDTF(date):
    """
    Convert a edtf date string to the previous version supported by the python edtf package
    """
    edtfDate = date.replace('X','u')
    if edtfDate[-1:] == '/':
        edtfDate += 'uuuu-uu'
    if edtfDate[0] == '/':
        edtfDate = 'uuuu-uu' + edtfDate
    return edtfDate