# -*- coding: utf-8 -*-
"""Modèles de document (squelettes à remplir) pour Writer.

``insert_template(doc, template_id)`` insère au curseur de vue un squelette
structuré et aéré : titres courts (styles « Titre 3 »), champs vides « … » à
remplir, lignes d'équation prêtes pour « Étape suivante » (elles contiennent
déjà un « = »). Une seule étape d'annulation (Ctrl+Z), aucun dialogue modal.

Imports ``uno`` protégés : le module reste importable hors LibreOffice.
"""
import sys
import traceback

try:  # pragma: no cover - dépend de LibreOffice
    import uno
except ImportError:
    uno = None

PARAGRAPH_BREAK = 0     # com.sun.star.text.ControlCharacter.PARAGRAPH_BREAK
BLANK = "…"             # champ vide à remplir

H1, H2, BODY = "H1", "H2", "BODY"   # rôles de style (résolus selon le document)
EQ = "EQ"                          # ligne d'équation (corps de texte)

TEMPLATES = [
    {"id": "tpl_equation_steps", "title": "Résoudre une équation",
     "description": "Équation, étapes de résolution, solution et vérification."},
    {"id": "tpl_probleme", "title": "Problème rédigé",
     "description": "Données, inconnue, calcul et conclusion en phrase."},
    {"id": "tpl_geometrie", "title": "Démonstration de géométrie",
     "description": "Énoncé, figure, propriété utilisée, démonstration, conclusion."},
    {"id": "tpl_fonction", "title": "Tableau de valeurs",
     "description": "Tableau x | f(x) à compléter."},
    {"id": "tpl_calcul_litteral", "title": "Calcul littéral",
     "description": "Développer et factoriser avec lignes d'équation."},
    {"id": "tpl_propriete", "title": "Propriété à retenir",
     "description": "Propriété, exemple, à retenir."},
]
BY_ID = {t["id"]: t for t in TEMPLATES}

# Contenu : liste de (rôle, texte) ; ("TABLE", lignes) pour un tableau ;
# ("FOCUS", None) marque l'endroit où placer le curseur à la fin.
_LINES = {
    "tpl_equation_steps": [
        (H1, "Résoudre une équation"),
        (H2, "Équation"), (EQ, "… = …"),
        (H2, "Étapes"), (EQ, "… = …"),
        (H2, "Solution"), (BODY, "x = …"),
        (H2, "Vérification"), (EQ, "… = …"),
        (BODY, "On remplace x par … : le résultat est … donc la solution est juste."),
    ],
    "tpl_probleme": [
        (H1, "Problème"),
        (H2, "Données"), (BODY, "…"),
        (H2, "Inconnue"), (BODY, "On cherche …"),
        (H2, "Calcul"), (EQ, "… = …"),
        (H2, "Conclusion"), (BODY, "Donc …"),
    ],
    "tpl_geometrie": [
        (H1, "Démonstration"),
        (H2, "Énoncé"), (BODY, "…"),
        (H2, "Figure"), (BODY, "(Insère ou dessine la figure ici.)"), (BODY, ""),
        (H2, "Propriété utilisée"), (BODY, "Si …, alors …"),
        (H2, "Démonstration"), (BODY, "On sait que …"), (EQ, "… = …"),
        (H2, "Conclusion"), (BODY, "Donc …"),
    ],
    "tpl_fonction": [
        (H1, "Tableau de valeurs"),
        (H2, "Fonction"), (EQ, "f(x) = …"),
        (H2, "Tableau"),
        ("TABLE", [["x", "…", "…", "…", "…", "…"], ["f(x)", "…", "…", "…", "…", "…"]]),
        (H2, "Calcul d'une valeur"), (EQ, "f(…) = … = …"),
    ],
    "tpl_calcul_litteral": [
        (H1, "Calcul littéral"),
        (H2, "Développer"), (EQ, "A = … = …"),
        (H2, "Factoriser"), (EQ, "B = … = …"),
        (H2, "Réduire"), (EQ, "C = … = …"),
    ],
    "tpl_propriete": [
        (H1, "Propriété"),
        (H2, "Propriété"), (BODY, "…"),
        (H2, "Exemple"), (EQ, "… = …"),
        (H2, "À retenir"), (BODY, "…"),
    ],
}

_STYLE_CANDIDATES = {
    H1: ("Heading 2", "Heading 1", "Title"),
    H2: ("Heading 3", "Heading 2", "Heading 4"),
    BODY: ("Text body", "Text Body", "Body Text", "Default Paragraph Style", "Standard"),
    EQ: ("Text body", "Text Body", "Body Text", "Default Paragraph Style", "Standard"),
}


def log_exception(where):
    try:
        sys.stderr.write("[plugin-maths] erreur dans %s\n%s\n" % (where, traceback.format_exc()))
    except Exception:
        pass


def _resolve_styles(doc):
    """Associe chaque rôle à un nom de style de paragraphe existant (ou None)."""
    names = None
    try:
        names = doc.getStyleFamilies().getByName("ParagraphStyles")
    except Exception:
        pass
    out = {}
    for role, cands in _STYLE_CANDIDATES.items():
        out[role] = None
        for n in cands:
            try:
                if names is None or names.hasByName(n):
                    out[role] = n
                    break
            except Exception:
                continue
    return out


def _set_style(cursor, style):
    if not style:
        return
    try:
        cursor.ParaStyleName = style
    except Exception:
        pass


def _view_cursor(doc):
    return doc.getCurrentController().getViewCursor()


def build_plan(template_id):
    """Retourne le contenu du modèle (liste de tuples) ou None. Logique pure."""
    lines = _LINES.get(template_id)
    return list(lines) if lines is not None else None


def _insert_table(doc, text, cursor, rows):
    table = doc.createInstance("com.sun.star.text.TextTable")
    n_rows, n_cols = len(rows), len(rows[0])
    table.initialize(n_rows, n_cols)
    text.insertTextContent(cursor, table, False)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = table.getCellByName("%s%d" % (chr(ord("A") + c), r + 1))
            cell.setString(val)
            try:
                cell.getText().createTextCursor().ParaAdjust = 3  # CENTER
            except Exception:
                pass


def _write_plan(doc, plan):
    text = doc.getText()
    styles = _resolve_styles(doc)
    vc = _view_cursor(doc)
    cursor = text.createTextCursorByRange(vc.getStart())
    # La zone d'insertion doit être un paragraphe vide : sinon on passe à la ligne.
    probe = text.createTextCursorByRange(cursor)
    probe.gotoStartOfParagraph(False)
    probe.gotoEndOfParagraph(True)
    if probe.getString():
        text.insertControlCharacter(cursor, PARAGRAPH_BREAK, False)
    focus = None
    for role, content in plan:
        if role == "TABLE":
            _set_style(cursor, styles[BODY])
            _insert_table(doc, text, cursor, content)
            continue
        _set_style(cursor, styles.get(role))
        text.insertString(cursor, content, False)
        if focus is None and role == EQ:
            focus = text.createTextCursorByRange(cursor.getStart())
        text.insertControlCharacter(cursor, PARAGRAPH_BREAK, False)
    # Dernier paragraphe vide, en corps de texte, prêt à la frappe.
    _set_style(cursor, styles[BODY])
    if focus is not None:
        try:
            vc.gotoRange(focus.getStart(), False)
            focus.goLeft(0, False)
        except Exception:
            pass


def insert_template(doc, template_id):
    """Insère le modèle ``template_id`` au curseur. Ne lève jamais d'exception.

    Retourne True si le modèle a été inséré, False sinon.
    """
    plan = build_plan(template_id)
    if plan is None or doc is None:
        return False
    undo = None
    try:
        try:
            undo = doc.getUndoManager()
            undo.enterUndoContext("Insérer un modèle : %s" % BY_ID[template_id]["title"])
        except Exception:
            undo = None
        try:
            _write_plan(doc, plan)
            return True
        finally:
            if undo is not None:
                try:
                    undo.leaveUndoContext()
                except Exception:
                    pass
    except Exception:
        log_exception("insert_template(%s)" % template_id)
        return False
