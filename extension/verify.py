# -*- coding: utf-8 -*-
"""Vérification d'une équation pour une valeur donnée (ex. x = 3).

Évaluateur SÛR : le texte est converti en expression Python puis analysé avec
``ast.parse`` ; seuls des nœuds explicitement autorisés sont évalués (nombres,
+ - * / **, parenthèses, sqrt(), pi, la variable choisie). Jamais ``eval`` ni
``exec``. Les calculs utilisent ``fractions.Fraction`` tant que c'est possible
(comparaison exacte), sinon des flottants avec une tolérance de 1e-9.

Le module est pur Python (aucun import ``uno`` obligatoire).
"""
import ast
import math
import re
from fractions import Fraction

MAX_LEN = 300          # longueur maximale du texte analysé
MAX_EXP = 64           # exposant entier maximal (évite les calculs géants)
MAX_DIGITS = 400       # taille maximale d'un entier/numérateur
TOL = 1e-9

_SUPERSCRIPTS = {"²": "^2", "³": "^3", "¹": "^1", "⁴": "^4"}
_REPLACE = {
    "×": "*", "·": "*", "⋅": "*", "∙": "*", "÷": "/", ":": "/", "−": "-", "–": "-",
    "—": "-", "‑": "-", " ": " ", " ": " ", " ": " ",
    "[": "(", "]": ")", "{": "(", "}": ")", "π": " pi ", "√": " sqrt ",
}
_EQ_CHARS = ("=",)
_FUNCS = {"sqrt", "racine"}
_CONSTS = {"pi": math.pi}


class VerifyError(Exception):
    """Erreur de lecture/calcul, avec un message déjà lisible par l'élève."""


# --------------------------------------------------------------------------
# Normalisation et tokenisation
# --------------------------------------------------------------------------
def _normalize(text):
    s = text
    for k, v in _SUPERSCRIPTS.items():
        s = s.replace(k, v)
    for k, v in _REPLACE.items():
        s = s.replace(k, v)
    # virgule décimale : 3,5 -> 3.5 (une virgule entre deux chiffres)
    s = re.sub(r"(?<=\d),(?=\d)", ".", s)
    return s


_TOKEN_RE = re.compile(
    r"\s*(?:(?P<num>\d+(?:\.\d+)?|\.\d+)|(?P<name>[A-Za-zÀ-ÿ]+)|(?P<op>\*\*|[-+*/^()]))")


def _tokenize(s, var):
    """Découpe en jetons (type, valeur). Types : num, var, const, func, op."""
    toks = []
    pos = 0
    s = s.rstrip()
    while pos < len(s):
        m = _TOKEN_RE.match(s, pos)
        if not m or m.end() == pos:
            bad = s[pos:].strip()[:1] or "?"
            raise VerifyError("Caractère non reconnu : « %s »" % bad)
        pos = m.end()
        if m.group("num") is not None:
            toks.append(("num", m.group("num")))
        elif m.group("name") is not None:
            toks.extend(_split_name(m.group("name"), var))
        else:
            op = m.group("op")
            toks.append(("op", "**" if op == "^" else op))
    return toks


def _split_name(name, var):
    """« xy » -> x * y ; « pi », « sqrt » reconnus ; « 2x » géré par le appelant."""
    low = name.lower()
    out = []
    i = 0
    while i < len(name):
        rest = low[i:]
        if rest.startswith("sqrt"):
            out.append(("func", "sqrt")); i += 4
        elif rest.startswith("racine"):
            out.append(("func", "sqrt")); i += 6
        elif rest.startswith("pi") and var.lower() != "p":
            out.append(("const", "pi")); i += 2
        else:
            out.append(("var", name[i])); i += 1
    return out


def _insert_implicit(toks):
    """Insère les * implicites : 2x, 3(x+1), x(x-1), (a)(b), 2pi, 2sqrt(3)."""
    out = []
    for i, t in enumerate(toks):
        if out:
            p = out[-1]
            left = p[0] in ("num", "var", "const") or p == ("op", ")")
            right = t[0] in ("var", "const", "func") or t == ("op", "(") or (
                t[0] == "num" and (p == ("op", ")") or p[0] in ("var", "const")))
            if left and right:
                out.append(("op", "*"))
        out.append(t)
    return out


def _wrap_bare_sqrt(toks):
    """« √3 » ou « sqrt 3 » (sans parenthèses) -> sqrt(3)."""
    out = []
    i = 0
    while i < len(toks):
        t = toks[i]
        out.append(t)
        if t == ("func", "sqrt") and i + 1 < len(toks) and toks[i + 1] != ("op", "("):
            nxt = toks[i + 1]
            if nxt[0] in ("num", "var", "const"):
                out.extend([("op", "("), nxt, ("op", ")")])
                i += 2
                continue
            raise VerifyError("Racine carrée : il manque des parenthèses")
        i += 1
    return out


def _to_python(text, var):
    toks = _tokenize(_normalize(text), var)
    toks = _wrap_bare_sqrt(toks)
    toks = _insert_implicit(toks)
    parts = []
    for typ, val in toks:
        if typ == "num":
            parts.append(val)
        elif typ == "var":
            parts.append("_v_" + ("%d" % ord(val)))
        elif typ == "const":
            parts.append("_c_pi")
        elif typ == "func":
            parts.append("_f_sqrt")
        else:
            parts.append(val)
    return " ".join(parts)


# --------------------------------------------------------------------------
# Évaluation sûre sur l'AST
# --------------------------------------------------------------------------
def _frac(text):
    return Fraction(text)  # "3.5" -> 7/2 exact


def _as_float(x):
    return float(x)


def _check_size(x):
    if isinstance(x, Fraction):
        if x.numerator.bit_length() > MAX_DIGITS * 3 or x.denominator.bit_length() > MAX_DIGITS * 3:
            raise VerifyError("Nombre trop grand")
    elif isinstance(x, float):
        if math.isinf(x) or math.isnan(x):
            raise VerifyError("Nombre trop grand")
    return x


def _sqrt(x):
    if x < 0:
        raise VerifyError("Racine carrée d'un nombre négatif")
    if isinstance(x, Fraction):
        n, d = x.numerator, x.denominator
        rn, rd = math.isqrt(n), math.isqrt(d)
        if rn * rn == n and rd * rd == d:
            return Fraction(rn, rd)
    return math.sqrt(float(x))


def _pow(a, b):
    if isinstance(b, Fraction) and b.denominator == 1:
        e = b.numerator
        if abs(e) > MAX_EXP:
            raise VerifyError("Exposant trop grand")
        if isinstance(a, Fraction):
            if a == 0 and e < 0:
                raise VerifyError("Division par zéro")
            if abs(a.numerator) > 10 ** 30 and abs(e) > 8:
                raise VerifyError("Nombre trop grand")
            return a ** e
        try:
            return a ** e
        except (ZeroDivisionError, OverflowError):
            raise VerifyError("Calcul impossible")
    # exposant non entier
    fa, fb = float(a), float(b)
    if fa < 0:
        raise VerifyError("Puissance non entière d'un nombre négatif")
    if fa == 0 and fb < 0:
        raise VerifyError("Division par zéro")
    try:
        r = fa ** fb
    except (OverflowError, ZeroDivisionError):
        raise VerifyError("Calcul impossible")
    return r


def _eval(node, env):
    if isinstance(node, ast.Expression):
        return _eval(node.body, env)
    if isinstance(node, ast.Constant):
        v = node.value
        if type(v) is int:
            return Fraction(v)
        if type(v) is float:
            # décimaux : repasser par le texte pour rester exact (3.5 -> 7/2)
            return Fraction(repr(v))
        raise VerifyError("Expression non autorisée")
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise VerifyError("Variable inconnue : %s" % _pretty_name(node.id))
    if isinstance(node, ast.UnaryOp):
        v = _eval(node.operand, env)
        if isinstance(node.op, ast.USub):
            return -v
        if isinstance(node.op, ast.UAdd):
            return v
        raise VerifyError("Expression non autorisée")
    if isinstance(node, ast.BinOp):
        a = _eval(node.left, env)
        b = _eval(node.right, env)
        op = node.op
        if isinstance(op, ast.Add):
            r = a + b
        elif isinstance(op, ast.Sub):
            r = a - b
        elif isinstance(op, ast.Mult):
            r = a * b
        elif isinstance(op, ast.Div):
            if b == 0:
                raise VerifyError("Division par zéro")
            r = a / b
        elif isinstance(op, ast.Pow):
            r = _pow(a, b)
        else:
            raise VerifyError("Expression non autorisée")
        return _check_size(r)
    if isinstance(node, ast.Call):
        if (isinstance(node.func, ast.Name) and node.func.id == "_f_sqrt"
                and len(node.args) == 1 and not node.keywords):
            return _check_size(_sqrt(_eval(node.args[0], env)))
        raise VerifyError("Fonction non autorisée")
    raise VerifyError("Expression non autorisée")


def _pretty_name(ident):
    m = re.match(r"_v_(\d+)$", ident)
    return chr(int(m.group(1))) if m else ident


def evaluate(text, var="x", value=None):
    """Évalue ``text`` (expression sans « = ») avec ``var`` = ``value``.

    Retourne un Fraction ou un float. Lève VerifyError avec un message lisible.
    """
    text = (text or "").strip()
    if not text:
        raise VerifyError("Expression vide")
    if len(text) > MAX_LEN:
        raise VerifyError("Expression trop longue")
    var = (var or "x").strip() or "x"
    if len(var) != 1 or not var.isalpha():
        raise VerifyError("La variable doit être une seule lettre")
    py = _to_python(text, var)
    try:
        tree = ast.parse(py, mode="eval")
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        raise VerifyError("Je n'ai pas compris l'expression")
    env = {"_c_pi": math.pi}
    # π en flottant : le résultat devient approché, comparé avec tolérance
    if value is not None:
        env["_v_%d" % ord(var)] = value
    try:
        return _eval(tree, env)
    except RecursionError:
        raise VerifyError("Expression trop compliquée")
    except (ArithmeticError, ValueError, TypeError):
        raise VerifyError("Calcul impossible")


# --------------------------------------------------------------------------
# Formatage et comparaison
# --------------------------------------------------------------------------
def _fmt(x):
    if isinstance(x, Fraction):
        if x.denominator == 1:
            return str(x.numerator).replace("-", "−")
        s = "%d/%d" % (abs(x.numerator), x.denominator)
        if x.numerator < 0:
            s = "−" + s
        dec = float(x)
        return "%s (≈ %s)" % (s, _fmt_float(dec)) if not _is_short_decimal(x) else _fmt_float(dec)
    return "≈ " + _fmt_float(float(x))


def _is_short_decimal(x):
    d = x.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    return d == 1 and len(str(float(x))) <= 12


def _fmt_float(f):
    s = ("%.6f" % f).rstrip("0").rstrip(".")
    if s in ("", "-0"):
        s = "0"
    return s.replace(".", ",").replace("-", "−")


def _equal(a, b):
    if isinstance(a, Fraction) and isinstance(b, Fraction):
        return a == b
    fa, fb = float(a), float(b)
    return math.isclose(fa, fb, rel_tol=TOL, abs_tol=TOL)


def _parse_value(value, var):
    v = (value or "").strip()
    if not v:
        return None
    # accepte « x = 3 » ou « 3 »
    if "=" in v:
        left, _, right = v.partition("=")
        if left.strip() == var:
            v = right.strip()
    return evaluate(v, var, None)


def check(selected_text, var="x", value=""):
    """Vérifie « gauche = droite » pour ``var`` = ``value``.

    Retourne ``{"text": str, "ok": True | False | None}`` (None = pas un verdict).
    Ne lève jamais d'exception.
    """
    try:
        return _check(selected_text, var, value)
    except VerifyError as e:
        return {"text": str(e), "ok": None}
    except Exception:  # sécurité ultime : jamais d'exception vers l'UI
        return {"text": "Je n'ai pas compris l'expression", "ok": None}


def _check(selected_text, var, value):
    text = (selected_text or "").replace("\r", " ").replace("\n", " ").replace("\t", " ").strip()
    if "≠" in text or text.count("=") == 0 or any(
            part.strip() == "" for part in text.split("=")):
        return {"text": "Sélectionne une équation (avec un =)", "ok": None}
    if not (value or "").strip():
        return {"text": "Entre une valeur", "ok": None}
    var = (var or "x").strip() or "x"
    val = _parse_value(value, var)
    parts = text.split("=")
    vals = [evaluate(p, var, val) for p in parts]
    for a, b in zip(vals, vals[1:]):
        if not _equal(a, b):
            return {"text": "✗ Faux : %s ≠ %s" % (_fmt(a), _fmt(b)), "ok": False}
    return {"text": "✓ Juste : %s = %s" % (_fmt(vals[0]), _fmt(vals[-1])), "ok": True}


# --------------------------------------------------------------------------
# Extraction depuis la sélection Writer (best effort)
# --------------------------------------------------------------------------
_SM_WORDS = {"times": "*", "cdot": "*", "div": "/", "neg": "-", "left": "", "right": "",
             "%pi": "pi", "over": "/"}


def starmath_to_expr(code):
    """Convertit un code StarMath simple (over, sqrt, ^, accolades) en expression."""
    s = code or ""
    s = s.replace("<?>", " ")
    s = s.replace('"', "").replace("`", " ").replace("~", " ")
    s = re.sub(r"%pi\b", "pi", s)
    s = re.sub(r"\bnroot\b", "nroot", s)
    s = s.replace("{", "(").replace("}", ")")
    for w in ("times", "cdot", "div", "neg", "left", "right", "over"):
        s = re.sub(r"\b%s\b" % w, " %s " % _SM_WORDS[w], s)
    s = re.sub(r"\bsqrt\b", " sqrt ", s)
    return re.sub(r"\s+", " ", s).strip()


def _formula_code(obj):
    try:
        emb = obj.Model
        return emb.Formula
    except Exception:
        return None


def extract_equation(doc_selection):
    """Retourne le texte de la sélection (str) en convertissant les formules.

    ``doc_selection`` : chaîne, ou sélection du contrôleur Writer (XIndexAccess
    de plages), ou plage de texte. Best effort : jamais d'exception. Les objets
    formule *sélectionnés seuls* sont lus directement ; ceux situés dans une
    plage de texte sont retrouvés par énumération des portions (selon la
    version de LibreOffice, ces portions ne donnent pas toujours accès au code).
    """
    try:
        return _extract(doc_selection)
    except Exception:
        return ""


def _extract(sel):
    if sel is None:
        return ""
    if isinstance(sel, str):
        return sel
    code = _formula_code(sel)
    if code is not None:
        return starmath_to_expr(code)
    if hasattr(sel, "getCount") and hasattr(sel, "getByIndex"):
        return " ".join(t for t in (_extract(sel.getByIndex(i)) for i in range(sel.getCount())) if t)
    if hasattr(sel, "createEnumeration"):
        pieces = []
        paras = sel.createEnumeration()
        while paras.hasMoreElements():
            para = paras.nextElement()
            if not hasattr(para, "createEnumeration"):
                continue
            portions = para.createEnumeration()
            while portions.hasMoreElements():
                p = portions.nextElement()
                kind = getattr(p, "TextPortionType", "Text")
                if kind == "Text":
                    pieces.append(p.getString())
                else:
                    c = None
                    for attr in ("TextContent", "Frame", "TextFrame"):
                        try:
                            c = _formula_code(getattr(p, attr))
                        except Exception:
                            c = None
                        if c is not None:
                            break
                    if c is not None:
                        pieces.append(starmath_to_expr(c))
        return "".join(pieces)
    if hasattr(sel, "getString"):
        return sel.getString()
    return ""
