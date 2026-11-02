# -*- coding: utf-8 -*-
"""Bloc formule du panneau (WYSIWYG): description des gabarits, sans uno.

Cliquer sur un gabarit (fraction, racine...) ouvre dans le panneau un bloc qui
ressemble a la formule finale (numerateur au-dessus, denominateur dessous...).
L'utilisateur remplit les cases puis valide: ``build`` produit le code StarMath
a partir du gabarit du catalogue en remplacant les ``<?>`` par les valeurs.
"""
import catalog

# Formes: "frac" (empile, trait de fraction), "inline" (jetons texte/champ sur
# une ligne), "rows" (une ligne legendee par champ), "grid2" (champs 2 x 2).
# jeton ("t", texte) = symbole fixe ; ("f", i) = champ numero i.
SPECS = {
    "fraction": {"shape": "frac"},
    "sqrt": {"shape": "inline", "tokens": [("t", "√"), ("f", 0)]},
    "power": {"shape": "inline", "tokens": [("f", 0), ("t", "^"), ("f", 1)]},
    "subscript": {"shape": "inline", "tokens": [("f", 0), ("t", "_"), ("f", 1)]},
    "vector": {"shape": "inline", "tokens": [("t", "→"), ("f", 0)]},
    "abs": {"shape": "inline", "tokens": [("t", "|"), ("f", 0), ("t", "|")]},
    "sci_notation": {"shape": "inline",
                     "tokens": [("f", 0), ("t", "×10^"), ("f", 1)]},
    "interval": {"shape": "inline",
                 "tokens": [("t", "["), ("f", 0), ("t", ";"), ("f", 1), ("t", "]")]},
    "angle": {"shape": "inline", "tokens": [("t", "∠"), ("f", 0)]},
    "triangle": {"shape": "inline", "tokens": [("t", "Δ"), ("f", 0)]},
    "parallel": {"shape": "inline", "tokens": [("f", 0), ("t", "∥"), ("f", 1)]},
    "perpendicular": {"shape": "inline", "tokens": [("f", 0), ("t", "⊥"), ("f", 1)]},
    "sin": {"shape": "inline", "tokens": [("t", "sin ("), ("f", 0), ("t", ")")]},
    "cos": {"shape": "inline", "tokens": [("t", "cos ("), ("f", 0), ("t", ")")]},
    "tan": {"shape": "inline", "tokens": [("t", "tan ("), ("f", 0), ("t", ")")]},
    "system": {"shape": "rows", "captions": ["Équation 1", "Équation 2"]},
    "integral": {"shape": "rows",
                 "captions": ["Borne basse", "Borne haute", "Fonction"]},
    "sum": {"shape": "rows", "captions": ["De (début)", "À (fin)", "Terme"]},
    "limit": {"shape": "rows",
              "captions": ["Variable", "Tend vers", "Expression"]},
    "matrix": {"shape": "grid2"},
}

MAX_FIELDS = 4


def field_count(action_id):
    e = catalog.BY_ID.get(action_id)
    if e is None or not e.get("formula"):
        return 0
    return e["formula"].count("<?>")


def spec_for(action_id):
    """Description du bloc pour ``action_id`` (ou None: insertion directe)."""
    sp = SPECS.get(action_id)
    n = field_count(action_id)
    if sp is None or not 1 <= n <= MAX_FIELDS:
        return None
    out = dict(sp)
    out["id"] = action_id
    out["fields"] = n
    out["title"] = catalog.BY_ID[action_id]["title"]
    out.setdefault("tokens", [])
    out.setdefault("captions", [])
    return out


def normalize(text):
    """Saisie de l'eleve -> fragment StarMath (operateurs ASCII usuels)."""
    t = (text or "").strip()
    t = t.replace("*", " times ").replace("<=", " <= ").replace(">=", " >= ")
    return " ".join(t.split())


def build(action_id, values):
    """Code StarMath: remplace chaque ``<?>`` par la valeur du champ (vide = reste ``<?>``)."""
    formula = catalog.BY_ID[action_id]["formula"]
    out = []
    parts = formula.split("<?>")
    for i, part in enumerate(parts):
        out.append(part)
        if i < len(parts) - 1:
            v = normalize(values[i] if i < len(values) else "")
            out.append(v if v else "<?>")
    return "".join(out)
