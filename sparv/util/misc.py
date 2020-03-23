"""Misc util functions."""


def _safe_join(sep, elems):
    """Join a list of strings (elems), using (sep) as separator.

    All occurrences of (sep) in (elems) are removed.
    """
    return sep.join(elem.replace(sep, "") for elem in elems)


def strtobool(value):
    """Convert possible string to boolean."""
    if isinstance(value, str):
        value = (value.lower() == "true")
    return value


def split(value):
    """If 'value' is a string, split and return a list, otherwise return as is."""
    if isinstance(value, str):
        value = value.split()
    return value


def single_true(iterable):
    """Return True if one and only one element in iterable evaluates to True."""
    i = iter(iterable)
    return any(i) and not any(i)


def cwbset(values, delimiter="|", affix="|", sort=False, maxlength=4095, encoding="UTF-8"):
    """Take an iterable object and return a set in the format used by Corpus Workbench."""
    values = list(values)
    if sort:
        values.sort()
    if maxlength:
        length = 1  # Including the last affix
        for i, value in enumerate(values):
            length += len(value.encode(encoding)) + 1
            if length > maxlength:
                values = values[:i]
                break
    return affix if not values else affix + delimiter.join(values) + affix


def truncateset(string, maxlength=4095, delimiter="|", affix="|", encoding="UTF-8"):
    """Truncate a Corpus Workbench set to a maximum length."""
    if len(string) <= maxlength or string == "|":
        return string
    else:
        length = 1  # Including the last affix
        values = string[1:-1].split("|")
        for i, value in enumerate(values):
            length += len(value.encode(encoding)) + 1
            if length > maxlength:
                return cwbset(values[:i], delimiter, affix)


def remove_control_characters(text):
    """Remove control characters from text."""
    return text.translate(dict((ord(c), None) for c in [chr(i) for i in list(range(9)) + list(range(11, 13)) + list(range(14, 32)) + [127]]))
