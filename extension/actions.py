# -*- coding: utf-8 -*-
"""Exécution des actions du catalogue (sidebar, raccourcis clavier).

Les données (ids, formules, raccourcis) viennent de ``catalog`` et ``config`` ;
ce module ne contient aucune formule en dur. Les modules frères optionnels
(templates, verify, settings) sont importés paresseusement.
"""
import sys
import traceback

import catalog

try:
    import math_insert
except Exception:  # pragma: no cover
    math_insert = None
try:
    import config
except Exception:  # pragma: no cover
    config = None

ACTION_IDS = [e["id"] for e in catalog.CATALOG]
# Compat : action_id -> StarMath (templates uniquement).
FORMULAS = {e["id"]: e["formula"] for e in catalog.CATALOG if e["formula"]}
# action_id -> "[ // ]" / "[ clic ]" ; mis à jour en place si la config change.
SHORTCUTS = {}


def _refresh_shortcuts():
    for e in catalog.CATALOG:
        s = config.shortcut_text(e["id"]) if config else (
            e["trigger"]["value"] if e["trigger"] else "")
        SHORTCUTS[e["id"]] = "[ %s ]" % (s if s else "clic")


try:
    _refresh_shortcuts()
    if config:
        config.subscribe(_refresh_shortcuts)
except Exception:  # pragma: no cover
    pass


def _log(where):
    try:
        if math_insert is not None and hasattr(math_insert, "log_exception"):
            math_insert.log_exception(where)
        else:
            sys.stderr.write("[plugin-maths] %s\n%s\n" % (where, traceback.format_exc()))
    except Exception:
        pass


def _sibling(name):
    """Import paresseux d'un module frère ; None s'il est absent/cassé."""
    try:
        return __import__(name)
    except Exception:
        _log("import %s" % name)
        return None


def _enabled(action_id):
    return config.is_enabled(action_id) if config else True


# --------------------------------------------------------------- insertions
def _insert_symbol(doc, text):
    """Insère du texte brut au curseur de vue (remplace la sélection), en un undo."""
    mi_insert = getattr(math_insert, "insert_text", None) if math_insert else None
    if mi_insert:
        mi_insert(doc, text)
        return
    controller = doc.getCurrentController()
    cursor = controller.getViewCursor()
    undo = doc.getUndoManager()
    undo.enterUndoContext("Insertion")
    try:
        cursor.setString(text)   # remplace la sélection éventuelle
        cursor.collapseToEnd()
    finally:
        undo.leaveUndoContext()


def _selected_text(doc):
    try:
        sel = doc.getCurrentController().getSelection()
        txt = sel.getByIndex(0).getString() if sel.getCount() else ""
        return txt or ""
    except Exception:
        return ""


def _verify(doc, params):
    verify = _sibling("verify")
    if verify is None:
        return {"text": "Vérification indisponible", "ok": None}
    params = params or {}
    text = _selected_text(doc)
    try:
        if hasattr(verify, "extract_equation"):
            extracted = verify.extract_equation(doc.getCurrentController().getSelection())
            if isinstance(extracted, str) and extracted.strip():
                text = extracted
    except Exception:
        _log("verify.extract_equation")
    var = (params.get("ent_verify_var") or "x").strip() or "x"
    return verify.check(text, var, params.get("ent_verify_value") or "")


def run_action(doc, action_id, params=None, ctx=None):
    """Exécute une action sur un document Writer. Jamais d'exception.

    Retourne None ou, pour ``verify``, {"text": str, "ok": bool|None}.
    Pousse les insertions (symboles, gabarits, modèles) dans les récents.
    """
    try:
        e = catalog.BY_ID.get(action_id)
        if e is None:
            return None
        kind = e["kind"]
        if action_id == "open_settings":
            settings = _sibling("settings")
            if settings is not None:
                if ctx is None:
                    import uno
                    ctx = uno.getComponentContext()
                settings.open_settings(ctx)
            return None
        if kind != "tool" and not _enabled(action_id):
            return None
        if kind == "verify":
            return _verify(doc, params)
        if kind == "tool":
            fn = {"guide": lambda: math_insert.set_guide(doc, not math_insert.is_guide_on(doc)),
                  "align_equals": lambda: math_insert.align_equals(doc),
                  "equation_step": lambda: math_insert.equation_step(doc)}.get(action_id)
            if fn:
                fn()
            return None
        if kind == "symbol":
            _insert_symbol(doc, e["text"])
        elif kind == "template":
            math_insert.insert_math(doc, e["formula"], tab_and_go="<?>" in e["formula"])
        elif kind == "model":
            templates = _sibling("templates")
            if templates is None:
                return None
            templates.insert_template(doc, action_id)
        if config:
            config.push_recent(action_id)
    except Exception:
        _log("run_action(%s)" % action_id)
    return None


def _current_writer_doc(ctx):
    """Document Writer actif, ou None."""
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    doc = desktop.getCurrentComponent()
    if doc is not None and doc.supportsService("com.sun.star.text.TextDocument"):
        return doc
    return None


def dispatch(ctx, action_id, params=None):
    """Point d'entrée de la sidebar : agit sur le document Writer courant."""
    try:
        e = catalog.BY_ID.get(action_id)
        if e is None:
            return None
        if action_id == "open_settings":
            return run_action(None, action_id, params, ctx)
        if e["kind"] != "tool" and not _enabled(action_id):
            return None
        doc = _current_writer_doc(ctx)
        if doc is None:
            if e["kind"] == "verify":
                return {"text": "Ouvre un document Writer", "ok": None}
            return None
        res = run_action(doc, action_id, params, ctx)
        if e["kind"] != "verify" and math_insert is not None:
            math_insert.focus_active_frame(doc)   # le curseur revient dans le texte
        return res
    except Exception:
        _log("dispatch(%s)" % action_id)
        return None
