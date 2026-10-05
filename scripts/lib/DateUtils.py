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


_ORDINAL_WORDS = {
    'erst': 1, 'zweit': 2, 'dritt': 3, 'viert': 4, 'fünft': 5, 'sechst': 6, 'siebt': 7,
    'acht': 8, 'neunt': 9, 'zehnt': 10, 'elft': 11, 'zwölft': 12, 'dreizehnt': 13,
    'vierzehnt': 14, 'fünfzehnt': 15, 'sechzehnt': 16, 'siebzehnt': 17, 'achtzehnt': 18,
    'neunzehnt': 19, 'zwanzigst': 20, 'einundzwanzigst': 21,
}
_ORDINAL_RE = '|'.join(sorted(_ORDINAL_WORDS, key=len, reverse=True))

_CENTURY_RE = r'(?<!\d)(\d{1,2})\.?\s*(?:jh\b\.?|jahrhundert\w*)'
_HALF_RE = r'(?<!\d)([12])\.\s*h(?:\.|älfte)|\b(erste|zweite)\s+hälfte'
_BCE_RE = r'v\.\s*chr\b\.?|\bbce?\b'
_CE_RE = r'n\.\s*chr\b\.?|\bce\b|\ba\.\s*d\.'
_APPROX_RE = r'\b(?:um|ca|circa|etwa|gegen)\b\.?'
_GROUP_SEPARATOR_RE = r'\s+(?:oder|or|und|and)\b:?\s*|\s+u\.\s*'


def _clean_date_text(raw):
    """
    Normalise punctuation and strip editorial annotations. Returns (text, notes).
    """
    text = re.sub(r'[\u2012-\u2015\u2212]', '-', (raw or '').strip()) # replace various dash characters with a standard hyphen
    text = re.sub(r'\s+', ' ', text) # replace multiple whitespace characters with a single space

    notes = re.findall(r'\{([^}]*)\}', text) # extract notes enclosed in curly braces
    text = re.sub(r'\{[^}]*\}', ' ', text) # remove notes enclosed in curly braces
    text = re.sub(r'\(\s*\?\s*\)', ' ? ', text) # replace "(?)" with " ? "
    notes += re.findall(r'\(([^)]*)\)', text) # extract notes enclosed in parentheses
    text = re.sub(r'\([^)]*\)', ' ', text) # remove notes enclosed in parentheses

    # A trailing [..] is a correction note (e.g. "1730 [eigtl. 1729]") unless it is the only date.
    trailing = re.search(r'\s\[([^\]]*)\]\s*$', text) 
    if trailing and re.search(r'\d{3,4}', text[:trailing.start()]):
        notes.append(trailing.group(1))
        text = text[:trailing.start()]
    text = text.replace('[', '').replace(']', '')

    text = re.sub(
        rf'\b({_ORDINAL_RE})(?:e[nmrs]?)?(?=\s+(?:jh\b|jahrhundert))',
        lambda m: f"{_ORDINAL_WORDS[m.group(1).lower()]}.",
        text, flags=re.IGNORECASE,
    ) # e.g., "drittes Jahrhundert" -> "3. Jh."
    text = re.sub(r'\bzwischen\s+(.+?)\s+und\s+', r'\1 - ', text, flags=re.IGNORECASE) # replace "zwischen X und Y" with "X - Y"
    # "1.-2. Jh." -> "1. Jh. - 2. Jh."
    text = re.sub(r'(?<!\d)(\d{1,2})\.\s*-\s*(?=\d{1,2}\.\s*(?:jh\b|jahrhundert))', r'\1. Jh. - ', text, flags=re.IGNORECASE) # expand century ranges like "1.-2. Jh." to "1. Jh. - 2. Jh."
    text = re.sub(r'\s+', ' ', text).strip()
    return text, [n.strip() for n in notes if n.strip()]


def _shift_year(year, delta):
    """Shift a year in the historical (no year zero) convention."""
    shifted = year + delta
    return shifted if shifted != 0 else delta


def _parse_endpoint(text, bce, prev_year, allow_short):
    """
    Parse a single date expression into a (lower, upper) pair of years.
    Returns (lower, upper, kind, anchor_year) or None.
    """
    s = text.strip()
    sign = -1 if bce else 1
    lower = upper = kind = None

    m = re.search(_CENTURY_RE, s, re.IGNORECASE)
    if m and int(m.group(1)) > 0:
        # CE centuries as "hundreds" (3rd c. = 200-299); BCE counted back from c*100 (4th c. BCE = 400-301 BCE).
        c = int(m.group(1))
        start, end = ((-c * 100, -((c - 1) * 100 + 1)) if bce else (max((c - 1) * 100, 1), c * 100 - 1))
        half = re.search(_HALF_RE, s, re.IGNORECASE)
        if half:
            if half.group(1) == '1' or (half.group(2) or '').lower() == 'erste':
                end = start + 49
            else:
                start = start + 50
        lower, upper, kind = start, end, 'century'
    if kind is None:
        m = re.search(r'(?<!\d)(\d{3})0er\b', s) # e.g., "1980er"
        if m:
            decade = int(m.group(1)) * 10
            start, end = ((-(decade + 9), -decade) if bce else (decade, decade + 9))
            lower, upper, kind = start, end, 'decade'
    if kind is None:
        m = re.search(r'(?<!\d)(\d{2})XX\b|(?<!\d)(\d{3})X\b', s) # e.g., "19XX" or "198X"
        if m:
            digits = m.group(1) or m.group(2)
            pad = 4 - len(digits)
            start, end = int(digits + '0' * pad), int(digits + '9' * pad)
            if bce:
                start, end = -end, -start
            lower, upper, kind = start, end, 'range'
    if kind is None:
        for m in re.finditer(r'(?<![\d.])(\d{1,4})(?!\d)', s):
            token = m.group(1)
            if len(token) <= 2:
                if s[m.end():m.end() + 1] == '.':
                    continue  # ordinal number, not a year
                if not bce and prev_year is not None and prev_year >= 1000:
                    # Abbreviated end year, e.g. "1788-93" or "1502/03".
                    year = int(str(prev_year)[:4 - len(token)] + token.zfill(len(token)))
                elif allow_short:
                    year = int(token)
                else:
                    continue
            else:
                year = int(token)
            lower = upper = sign * year
            kind = 'year'
            break

    if kind is None:
        return None
    anchor = abs(upper) if kind == 'year' else prev_year

    if re.search(r'\b(?:vor|ante|before)\b', s, re.IGNORECASE):
        lower, upper = None, _shift_year(lower, -1)
    elif re.search(r'\b(?:nach|post|after)\b', s, re.IGNORECASE):
        lower, upper = _shift_year(upper, 1), None
    return lower, upper, kind, anchor


def _parse_alternative(text, bce, prev_year, allow_short):
    """
    Parse one alternative, which may be a range "A - B". Returns (lower, upper, kinds, prev_year) or None.
    """
    parts = re.split(r'\s*-\s*', text.strip())
    start = _parse_endpoint(parts[0], bce, prev_year, allow_short) if parts[0] else None
    if start is not None:
        prev_year = start[3]
    if len(parts) == 1:
        if start is None:
            return None
        return start[0], start[1], {start[2]}, prev_year

    end = _parse_endpoint(parts[-1], bce, prev_year, allow_short) if parts[-1] else None
    if end is not None:
        prev_year = end[3]
    if start is None and end is None:
        return None
    if start is None:
        return None, end[1], {end[2]}, prev_year
    if end is None:
        # "1978-" is an open-ended range; otherwise ignore the unparseable end.
        return start[0], (None if not parts[-1] else start[1]), {start[2]}, prev_year

    lower, upper = start[0], end[1]
    if lower is not None and upper is not None and lower > upper:
        lower, upper = (end[0] if end[0] is not None else lower), (start[1] if start[1] is not None else upper)
    return lower, upper, {start[2], end[2]}, prev_year


def _edtf_point(year):
    # 1 BCE = 0000, 400 BCE = -0399.
    if year < 0:
        year += 1
    return f"-{abs(year):04d}" if year < 0 else f"{year:04d}"


def _to_edtf(alternatives):
    """
    Serialise parsed alternatives as an EDTF string (single date, interval or one-of set).
    """
    in_set = len(alternatives) > 1
    if in_set:
        # EDTF only allows ".." on the first (earlier) or last (later) set member.
        alternatives = sorted(alternatives, key=lambda a: (
            a[0] is not None, a[1] is None, a[0] if a[0] is not None else 0))
    parts = []
    for lower, upper, approximate, uncertain in alternatives:
        qualifier = '%' if (approximate and uncertain) else '~' if approximate else '?' if uncertain else ''
        if lower is not None and lower == upper:
            parts.append(_edtf_point(lower) + qualifier)
        elif in_set:
            # Set ranges ("a..b") do not take qualifiers; the qualifier string still records them.
            parts.append(('' if lower is None else _edtf_point(lower)) + '..' + ('' if upper is None else _edtf_point(upper)))
        else:
            start = '..' if lower is None else _edtf_point(lower) + qualifier
            end = '..' if upper is None else _edtf_point(upper) + qualifier
            parts.append(f"{start}/{end}")
    return f"[{','.join(parts)}]" if in_set else parts[0]


def normalize_object_date(raw_date):
    """
    Normalize free-text dates into gYear bounds (historical convention, no year zero)
    and an EDTF expression (ISO 8601 astronomical years).
    The original value must always be preserved by the caller.
    """
    original = raw_date or ''
    text, notes = _clean_date_text(original)

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
        'note': '; '.join(notes)
    }

    if not text:
        result['parse_status'] = 'unknown'
        result['note'] = result['note'] or 'empty'
        return result

    if re.fullmatch(r'o\.?\s*j\.?|ohne jahr', text, re.IGNORECASE):
        result['parse_status'] = 'unknown'
        result['precision'] = 'unknown'
        result['note'] = 'no date marker'
        return result

    alternatives = []  # (lower, upper, approximate, uncertain)
    kinds = set()

    iso = re.fullmatch(r'(-?\d{4})(?:-\d{2}(?:-\d{2})?)?', text)
    if iso and int(iso.group(1)) != 0:
        # ISO/TEI @when value (XSD 1.0: -0469 = 469 BCE); only the year is used.
        year = int(iso.group(1))
        alternatives.append((year, year, False, False))
        kinds.add('year')
    else:
        groups = [g for g in re.split(_GROUP_SEPARATOR_RE, text, flags=re.IGNORECASE) if g.strip()]
        eras = [
            True if re.search(_BCE_RE, g, re.IGNORECASE) else False if re.search(_CE_RE, g, re.IGNORECASE) else None
            for g in groups
        ]
        plain_number = bool(re.fullmatch(r'\d{1,4}', text))
        for i, group in enumerate(groups):
            # An unmarked group inherits the era of the next marked one ("348/347 v.Chr.").
            era = eras[i] if eras[i] is not None else next((e for e in eras[i + 1:] if e is not None), None)
            approximate = bool(re.search(_APPROX_RE, group, re.IGNORECASE))
            uncertain = '?' in group
            body = re.sub(f'{_BCE_RE}|{_CE_RE}|{_APPROX_RE}', ' ', group, flags=re.IGNORECASE).replace('?', ' ')
            prev_year = None
            for alternative in body.split('/'):
                parsed = _parse_alternative(alternative, era is True, prev_year, era is not None or plain_number)
                if parsed is None:
                    continue
                lower, upper, alt_kinds, prev_year = parsed
                alternatives.append((lower, upper, approximate, uncertain))
                kinds |= alt_kinds

    # "nach 1278/vor 1284" describes one bounded interval, not two alternatives.
    if len(alternatives) == 2:
        (a_lo, a_hi, a_ap, a_un), (b_lo, b_hi, b_ap, b_un) = alternatives
        if a_hi is None and b_lo is None and a_lo is not None and b_hi is not None and a_lo <= b_hi:
            alternatives = [(a_lo, b_hi, a_ap or b_ap, a_un or b_un)]

    unique = []
    for alternative in alternatives:
        if alternative not in unique:
            unique.append(alternative)
    alternatives = unique

    if not alternatives:
        result['parse_status'] = 'unknown'
        result['precision'] = 'unknown'
        result['note'] = (result['note'] + '; ' if result['note'] else '') + 'no year token found'
        return result

    lowers = [a[0] for a in alternatives]
    uppers = [a[1] for a in alternatives]
    open_interval = any(p is None for p in lowers + uppers)
    lower_year = None if any(p is None for p in lowers) else min(lowers)
    upper_year = None if any(p is None for p in uppers) else max(uppers)

    if open_interval:
        precision = 'open'
    elif 'century' in kinds:
        precision = 'century'
    elif len(alternatives) == 1 and lowers[0] == uppers[0]:
        precision = 'year'
    else:
        precision = 'range'

    result.update({
        'edtf': _to_edtf(alternatives),
        'lower': None if lower_year is None else _format_year(lower_year),
        'upper': None if upper_year is None else _format_year(upper_year),
        'precision': precision,
        'approximate': any(a[2] for a in alternatives),
        'uncertain': any(a[3] for a in alternatives),
        'bce': any(p is not None and p < 0 for p in lowers + uppers),
        'disjunction': len(alternatives) > 1,
        'open_interval': open_interval,
        'parse_status': 'partial' if open_interval else 'ok',
    })
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