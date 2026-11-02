# -*- coding: utf-8 -*-
"""Catalogue des actions : source de vérité (boutons, raccourcis, presets).

Aucune dépendance à uno : ce module est du pur Python.

Chaque entrée de ``CATALOG`` est un dict :
    id       identifiant (widget ``btn_<id>`` de la sidebar)
    label    texte court du bouton
    title    phrase d'infobulle ("Insérer une fraction")
    group    clé de ``GROUPS``
    kind     "symbol" | "template" | "tool" | "model" | "verify"
    formula  code StarMath (kind="template") ou None ; ``<?>`` = champ vide
    text     caractère Unicode inséré (kind="symbol") ou None
    trigger  raccourci par défaut : {"type":"seq","value":"//"},
             {"type":"combo","value":"Ctrl+Alt+G"} ou None
    word     True : une séquence en lettres ne se déclenche pas juste après
             une lettre (évite que "avec" déclenche "vec")
    presets  presets où l'action est activée par défaut

Choix des séquences nouvelles : les mots français courants (sys, int, sum,
lim, mat... début de "système", "intervalle", "limite", "matin") se
déclencheraient en pleine frappe, donc les gabarits avancés utilisent le
préfixe "\\" (\\sys, \\int, \\sum, \\lim, \\mat, \\sci), jamais tapé dans un
texte normal. Aucune séquence n'est préfixe d'une autre (testé).
"""

GROUPS = [
    ("tools", "Outils"),
    ("nombres", "Nombres & Opérations"),
    ("gabarits", "Gabarits"),
    ("geometrie", "Géométrie / Trigonométrie"),
    ("ensembles", "Ensembles & Fonctions"),
    ("modeles", "Modèles"),
    ("verif", "Vérifier"),
]

PRESET_NAMES = ["simple", "standard", "complet"]

_SIMPLE = {
    "times", "divide", "plus_minus", "leq", "geq", "neq", "approx", "pi",
    "fraction", "sqrt", "power", "subscript", "vector", "angle", "triangle",
    "degree", "guide", "align_equals", "equation_step", "open_settings",
    "verify", "tpl_equation_steps", "tpl_probleme",
}
_STANDARD_EXTRA = {
    "abs", "parallel", "perpendicular", "sin", "cos", "tan", "interval",
    "sci_notation", "set_in", "set_union", "set_inter", "set_R", "set_N",
    "set_Z", "tpl_geometrie", "tpl_fonction", "tpl_calcul_litteral",
    "tpl_propriete", "system",
}
_STANDARD = _SIMPLE | _STANDARD_EXTRA


def _presets_for(action_id):
    res = ["complet"]
    if action_id in _STANDARD:
        res.insert(0, "standard")
    if action_id in _SIMPLE:
        res.insert(0, "simple")
    return res


def _seq(value):
    return {"type": "seq", "value": value}


def _combo(value):
    return {"type": "combo", "value": value}


def _e(id, label, title, group, kind, formula=None, text=None,
       trigger=None, word=False):
    return {
        "id": id, "label": label, "title": title, "group": group,
        "kind": kind, "formula": formula, "text": text,
        "trigger": trigger, "word": word, "presets": _presets_for(id),
    }


CATALOG = [
    # --- Outils
    _e("guide", "Guidage visuel", "Afficher ou masquer le guidage visuel",
       "tools", "tool", trigger=_combo("Ctrl+Alt+G")),
    _e("align_equals", "Aligner les =", "Aligner les signes égal",
       "tools", "tool", trigger=_combo("Ctrl+Alt+E")),
    _e("equation_step", "Ligne suivante", "Passer à l'étape suivante du calcul",
       "tools", "tool", trigger=_combo("Ctrl+Alt+Return")),
    _e("open_settings", "⚙ Réglages", "Ouvrir les réglages",
       "tools", "tool"),
    # --- Nombres & Opérations
    _e("times", "×", "Insérer le signe multiplié", "nombres", "symbol",
       text="×"),
    _e("divide", "÷", "Insérer le signe divisé", "nombres", "symbol",
       text="÷"),
    _e("plus_minus", "±", "Insérer plus ou moins", "nombres", "symbol",
       text="±", trigger=_seq("+-")),
    _e("leq", "≤", "Insérer inférieur ou égal", "nombres", "symbol",
       text="≤", trigger=_seq("<=")),
    _e("geq", "≥", "Insérer supérieur ou égal", "nombres", "symbol",
       text="≥", trigger=_seq(">=")),
    _e("neq", "≠", "Insérer différent de", "nombres", "symbol",
       text="≠", trigger=_seq("!=")),
    _e("approx", "≈", "Insérer environ égal", "nombres", "symbol",
       text="≈", trigger=_seq("~=")),
    _e("pi", "π", "Insérer pi", "nombres", "symbol", text="π"),
    # --- Gabarits
    _e("fraction", "a/b", "Insérer une fraction", "gabarits", "template",
       formula="{<?>} over {<?>}", trigger=_seq("//")),
    _e("sqrt", "√", "Insérer une racine carrée", "gabarits", "template",
       formula="sqrt {<?>}", trigger=_seq("sqrt"), word=True),
    _e("power", "xⁿ", "Insérer une puissance", "gabarits", "template",
       formula="{<?>} ^ {<?>}", trigger=_seq("^^")),
    _e("subscript", "xₙ", "Insérer un indice", "gabarits", "template",
       formula="{<?>} _ {<?>}", trigger=_seq("__")),
    _e("vector", "→v", "Insérer un vecteur", "gabarits", "template",
       formula="vec {<?>}", trigger=_seq("vec"), word=True),
    _e("abs", "|x|", "Insérer une valeur absolue", "gabarits", "template",
       formula="abs {<?>}"),
    _e("system", "Système", "Insérer un système d'équations", "gabarits",
       "template",
       formula="left lbrace stack { {<?>} # {<?>} } right none",
       trigger=_seq("\\sys")),
    _e("integral", "∫", "Insérer une intégrale", "gabarits", "template",
       formula="int from {<?>} to {<?>} {<?>}", trigger=_seq("\\int")),
    _e("sum", "Σ", "Insérer une somme", "gabarits", "template",
       formula="sum from {<?>} to {<?>} {<?>}", trigger=_seq("\\sum")),
    _e("limit", "lim", "Insérer une limite", "gabarits", "template",
       formula="lim from {{<?>} toward {<?>}} {<?>}", trigger=_seq("\\lim")),
    _e("matrix", "Matrice", "Insérer une matrice 2×2", "gabarits",
       "template",
       formula="left ( matrix { <?> # <?> ## <?> # <?> } right )",
       trigger=_seq("\\mat")),
    _e("sci_notation", "a×10ⁿ", "Insérer une écriture scientifique",
       "gabarits", "template", formula="{<?>} times 10 ^ {<?>}",
       trigger=_seq("\\sci")),
    _e("interval", "[a ; b]", "Insérer un intervalle", "gabarits", "template",
       formula='left [ {<?>} ";" {<?>} right ]'),
    # --- Géométrie / Trigonométrie
    _e("angle", "Â", "Insérer un angle", "geometrie", "template",
       formula="widehat {<?>}"),
    _e("triangle", "Δ", "Insérer un triangle", "geometrie", "template",
       formula="%DELTA {<?>}"),
    _e("parallel", "∥", "Insérer des droites parallèles", "geometrie",
       "template", formula="{<?>} parallel {<?>}"),
    _e("perpendicular", "⊥", "Insérer des droites perpendiculaires",
       "geometrie", "template", formula="{<?>} ortho {<?>}"),
    _e("degree", "°", "Insérer le symbole degré", "geometrie", "symbol",
       text="°"),
    _e("sin", "sin", "Insérer un sinus", "geometrie", "template",
       formula="sin left ( {<?>} right )"),
    _e("cos", "cos", "Insérer un cosinus", "geometrie", "template",
       formula="cos left ( {<?>} right )"),
    _e("tan", "tan", "Insérer une tangente", "geometrie", "template",
       formula="tan left ( {<?>} right )"),
    # --- Ensembles & Fonctions
    _e("set_in", "∈", "Insérer appartient à", "ensembles", "symbol",
       text="∈"),
    _e("set_union", "∪", "Insérer union", "ensembles", "symbol",
       text="∪"),
    _e("set_inter", "∩", "Insérer intersection", "ensembles", "symbol",
       text="∩"),
    _e("set_R", "ℝ", "Insérer l'ensemble des réels", "ensembles",
       "symbol", text="ℝ"),
    _e("set_N", "ℕ", "Insérer l'ensemble des entiers naturels",
       "ensembles", "symbol", text="ℕ"),
    _e("set_Z", "ℤ", "Insérer l'ensemble des entiers relatifs",
       "ensembles", "symbol", text="ℤ"),
    # --- Modèles
    _e("tpl_equation_steps", "Résoudre une équation",
       "Modèle : résoudre une équation", "modeles", "model"),
    _e("tpl_probleme", "Problème", "Modèle : résoudre un problème",
       "modeles", "model"),
    _e("tpl_geometrie", "Géométrie", "Modèle : démonstration de géométrie",
       "modeles", "model"),
    _e("tpl_fonction", "Fonction", "Modèle : tableau de valeurs",
       "modeles", "model"),
    _e("tpl_calcul_litteral", "Calcul littéral",
       "Modèle : développer et factoriser", "modeles", "model"),
    _e("tpl_propriete", "Propriété", "Modèle : propriété, exemple, à retenir",
       "modeles", "model"),
    # --- Vérifier
    _e("verify", "Vérifier", "Vérifier l'égalité avec la valeur donnée",
       "verif", "verify"),
]

BY_ID = {e["id"]: e for e in CATALOG}
GROUP_LABELS = dict(GROUPS)


def ids_for_preset(name):
    """Ids activés par défaut dans un preset (repli si le .json manque)."""
    return [e["id"] for e in CATALOG if name in e["presets"]]
