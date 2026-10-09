"""A small, tolerant JSON5 reader for the tier config fragments.

It handles exactly what the fragments use and nothing more:
  - // line comments and /* block comments */
  - trailing commas in objects and arrays
  - unquoted object keys made of letters, digits, _ and $
  - double-quoted strings (comment markers inside strings are kept)
It does not handle single-quoted strings, hex numbers, Infinity or NaN. Anything
it cannot read raises ValueError, so a fragment that drifts outside this subset
fails loudly instead of being half-parsed. Standard library only.
"""

import json
import re

_IDENT = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")


def _strip_comments(text):
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    break
                if text[j] == "\n":
                    raise ValueError("unterminated string at offset %d" % i)
                j += 1
            else:
                raise ValueError("unterminated string at offset %d" % i)
            out.append(text[i : j + 1])
            i = j + 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j == -1 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            if j == -1:
                raise ValueError("unterminated block comment at offset %d" % i)
            out.append(" ")
            i = j + 2
        elif c == "'":
            raise ValueError("single-quoted strings are not supported (offset %d)" % i)
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _quote_keys_and_drop_trailing_commas(text):
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i : j + 1])
            i = j + 1
            continue
        if c == ",":
            k = i + 1
            while k < n and text[k].isspace():
                k += 1
            if k < n and text[k] in "}]":
                i += 1  # trailing comma: drop it
                continue
        m = _IDENT.match(text, i)
        if m:
            word = m.group(0)
            k = m.end()
            while k < n and text[k].isspace():
                k += 1
            if k < n and text[k] == ":":
                out.append('"%s"' % word)
            else:
                out.append(word)  # true / false / null; json.loads judges the rest
            i = m.end()
            continue
        out.append(c)
        i += 1
    return "".join(out)


def loads(text):
    return json.loads(_quote_keys_and_drop_trailing_commas(_strip_comments(text)))


def load(path):
    with open(path, encoding="utf-8") as fh:
        return loads(fh.read())
