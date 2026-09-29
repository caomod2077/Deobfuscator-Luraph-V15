import re

KEYWORDS = {"and","break","do","else","elseif","end","false","for","function","if","in",
            "local","nil","not","or","repeat","return","then","true","until","while","continue"}

_num = re.compile(r"0[xX][0-9a-fA-F_]+|0[bB][01_]+|(?:\d[\d_]*\.?[\d_]*|\.\d[\d_]*)(?:[eE][+-]?\d+)?")
_name = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_ops = ["...", "..=", "==", "~=", "<=", ">=", "//=", "//", "..", "::", "->", "+=", "-=", "*=", "/=", "%=", "^=",
        "+", "-", "*", "/", "%", "^", "#", "<", ">", "=", "(", ")", "{", "}", "[", "]", ";", ":", ",", ".", "&", "|", "?"]

def tokenize(src):
    """Yield (kind, text) tuples. kind in name/kw/num/str/op/comment."""
    i, n = 0, len(src)
    out = []
    while i < n:
        c = src[i]
        if c in " \t\r\n":
            i += 1
            continue
        if src.startswith("--", i):
            m = re.match(r"--\[(=*)\[", src[i:])
            if m:
                close = "]" + m.group(1) + "]"
                j = src.find(close, i + m.end())
                j = n if j < 0 else j + len(close)
            else:
                j = src.find("\n", i)
                j = n if j < 0 else j
            out.append(("comment", src[i:j]))
            i = j
            continue
        if c == "[":
            m = re.match(r"\[(=*)\[", src[i:i + 64])
            if m:
                close = "]" + m.group(1) + "]"
                j = src.find(close, i + m.end())
                j = n if j < 0 else j + len(close)
                out.append(("str", src[i:j]))
                i = j
                continue
        if c in "\"'`":
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == "\\":
                    j += 1
                j += 1
            out.append(("str", src[i:j + 1]))
            i = j + 1
            continue
        if c.isdigit() or (c == "." and i + 1 < n and src[i + 1].isdigit()):
            m = _num.match(src, i)
            out.append(("num", m.group(0)))
            i = m.end()
            continue
        m = _name.match(src, i)
        if m:
            w = m.group(0)
            out.append(("kw" if w in KEYWORDS else "name", w))
            i = m.end()
            continue
        for op in _ops:
            if src.startswith(op, i):
                out.append(("op", op))
                i += len(op)
                break
        else:
            raise SyntaxError("bad char %r at %d" % (c, i))
    return out

def pretty(tokens, max_str=120):
    """Re-indent a token stream into readable Luau (one statement per line)."""
    lines, cur, depth = [], [], 0
    paren = 0
    func_stack = []      
    want_func = False

    def flush():
        if cur:
            lines.append("  " * depth + " ".join(cur))
            cur.clear()

    prev, prev_kind = None, None
    for kind, t in tokens:
        if kind == "comment":
            continue
        if kind == "str" and len(t) > max_str:
            t = t[:max_str] + "...<%d chars>" % len(t) + t[0]
        if kind == "kw" and t in ("end", "else", "elseif", "until"):
            flush()
            depth = max(0, depth - 1)
        glue = cur and (t in (".", ":", ",", ")", "]", ";") or prev in (".", ":", "(", "[", "{", "#")
                        or (t in ("(", "[") and prev_kind in ("name", "str") or (t in ("(", "[") and prev in (")", "]"))))
        if glue:
            cur[-1] += t
        else:
            cur.append(t)
        if kind == "op" and t in "([{":
            paren += 1
            if t == "(" and want_func:
                func_stack.append(paren)
                want_func = False
        elif kind == "op" and t in ")]}":
            if t == ")" and func_stack and func_stack[-1] == paren:
                func_stack.pop()
                paren -= 1
                flush(); depth += 1
                prev, prev_kind = t, kind
                continue
            paren -= 1
        if kind == "kw" and t == "function":
            want_func = True
        if kind == "kw" and t in ("then", "do", "else", "repeat"):
            flush(); depth += 1
        if kind == "op" and t == ";":
            flush()
        if kind == "kw" and t == "end":
            pass
        prev, prev_kind = t, kind
    flush()
    return "\n".join(lines)

if __name__ == "__main__":
    import os
    import sys
    in_path = os.path.realpath(sys.argv[1])
    if not os.path.isfile(in_path):
        sys.exit("lexer.py: no such file: %s" % sys.argv[1])
    s = open(in_path, encoding="latin-1").read()
    sys.stdout.write(pretty(tokenize(s), int(sys.argv[2]) if len(sys.argv) > 2 else 120))
