from collections import namedtuple
import re


Regex = namedtuple("Regex", "pattern flags")


# Has to be the first non-empty line, ignoring comments
doctype_re = Regex(r"^\s*(<\!--.*-->\s*)*<\!doctype html", re.IGNORECASE | re.MULTILINE)
