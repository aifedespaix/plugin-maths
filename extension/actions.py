# -*- coding: utf-8 -*-
"""Table des actions (boutons de la sidebar, raccourcis) et leur exécution."""
import math_insert

# Ordre = ordre d'affichage dans la sidebar.
ACTION_IDS = [
    # Nombres & Opérations
    "times", "divide", "plus_minus", "leq", "geq", "neq", "approx", "pi",
    # Gabarits
    "fraction", "sqrt", "power", "subscript", "vector", "abs",
    # Géométrie / Trigonométrie
    "angle", "triangle", "parallel", "perpendicular", "degree", "sin", "cos", "tan",
    # Outils
    "guide", "align_equals",
]

# Code StarMath inséré par chaque action. <?> = champ vide à remplir.
FORMULAS = {
    "times": "times",
    "divide": "div",
    "plus_minus": "+-",
    "leq": "leslant",
    "geq": "geslant",
    "neq": "<>",
    "approx": "approx",
    "pi": "%pi",
    "fraction": "{<?>} over {<?>}",
    "sqrt": "sqrt {<?>}",
    "power": "{<?>} ^ {<?>}",
    "subscript": "{<?>} _ {<?>}",
    "vector": "vec {<?>}",
    "abs": "abs {<?>}",
    "angle": "widehat {<?>}",
    "triangle": "%DELTA {<?>}",
    "parallel": "{<?>} parallel {<?>}",
    "perpendicular": "{<?>} ortho {<?>}",
    "degree": '{<?>} "°"',
    "sin": "sin left ( {<?>} right )",
    "cos": "cos left ( {<?>} right )",
    "tan": "tan left ( {<?>} right )",
}

# Actions sans champ à remplir : pas de Tab & Go.
_NO_TAB_AND_GO = {"times", "divide", "plus_minus", "leq", "geq", "neq", "approx", "pi"}

# Textes des tooltips.
SHORTCUTS = {
    "times": "[ clic ]", "divide": "[ clic ]", "plus_minus": "[ +- ]",
    "leq": "[ <= ]", "geq": "[ >= ]", "neq": "[ != ]", "approx": "[ ~= ]",
    "pi": "[ clic ]",
    "fraction": "[ // ]", "sqrt": "[ sqrt ]", "power": "[ ^^ ]",
    "subscript": "[ __ ]", "vector": "[ vec ]", "abs": "[ clic ]",
    "angle": "[ clic ]", "triangle": "[ clic ]", "parallel": "[ clic ]",
    "perpendicular": "[ clic ]", "degree": "[ clic ]",
    "sin": "[ clic ]", "cos": "[ clic ]", "tan": "[ clic ]",
    "guide": "[ Ctrl+Alt+G ]", "align_equals": "[ Ctrl+Alt+E ]",
}


def run_action(doc, action_id):
    """Exécute une action sur un document Writer (jamais d'exception)."""
    try:
        if action_id == "guide":
            math_insert.set_guide(doc, not math_insert.is_guide_on(doc))
        elif action_id == "align_equals":
            math_insert.align_equals(doc)
        elif action_id in FORMULAS:
            math_insert.insert_math(doc, FORMULAS[action_id],
                                    tab_and_go=action_id not in _NO_TAB_AND_GO)
    except Exception:
        math_insert.log_exception("run_action(%s)" % action_id)


def _current_writer_doc(ctx):
    """Document Writer actif, ou None."""
    import uno  # local : le module reste importable hors LibreOffice
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = desktop.getCurrentComponent()
    if doc is not None and doc.supportsService("com.sun.star.text.TextDocument"):
        return doc
    return None


def dispatch(ctx, action_id):
    """Point d'entrée de la sidebar : agit sur le document Writer courant."""
    try:
        doc = _current_writer_doc(ctx)
        if doc is not None:
            run_action(doc, action_id)
    except Exception:
        math_insert.log_exception("dispatch(%s)" % action_id)
