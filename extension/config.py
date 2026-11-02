# -*- coding: utf-8 -*-
"""Configuration utilisateur (presets + réglages perso). Pur Python.

Résolution : défauts < preset (presets/<nom>.json) < réglages utilisateur
("overrides" du fichier JSON utilisateur). Une config absente ou corrompue
donne les défauts, jamais d'exception.

Fichier utilisateur : ``$(user)/plugin-maths.json`` du profil LibreOffice
(``uno`` optionnel), repli %APPDATA%/plugin-maths/config.json ou
~/.config/plugin-maths/config.json. La variable d'environnement
PLUGIN_MATHS_CONFIG force un chemin (tests).
"""
import copy
import json
import os
import re
import sys
import threading

try:
    import catalog
except ImportError:  # pragma: no cover
    from . import catalog

DEFAULT_PRESET = "standard"
RECENT_MAX = 6
THEMES = ("clair", "doux", "contraste")
DEFAULT_UI = {"scale": 1.0, "theme": "clair", "button_height": 44,
              "guide_color": "#FFF3C4"}
_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

_lock = threading.RLock()
_state = None          # dict utilisateur chargé
_subscribers = []
_ctx = None
_preset_cache = {}


def _log(where):
    try:
        import traceback
        sys.stderr.write("[plugin-maths] %s\n%s\n" % (where, traceback.format_exc()))
    except Exception:
        pass


def set_context(ctx):
    """Optionnel : contexte UNO pour retrouver le dossier du profil."""
    global _ctx
    _ctx = ctx


# --------------------------------------------------------------- chemins
def _presets_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets")


def user_path():
    env = os.environ.get("PLUGIN_MATHS_CONFIG")
    if env:
        return env
    try:
        import uno
        ctx = _ctx or uno.getComponentContext()
        subst = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.util.PathSubstitution", ctx)
        url = subst.substituteVariables("$(user)", True)
        if url:
            return os.path.join(uno.fileUrlToSystemPath(url), "plugin-maths.json")
    except Exception:
        pass
    appdata = os.environ.get("APPDATA")
    if appdata:
        return os.path.join(appdata, "plugin-maths", "config.json")
    return os.path.join(os.path.expanduser("~"), ".config", "plugin-maths", "config.json")


# --------------------------------------------------------------- presets
def preset_names():
    names = []
    try:
        for f in sorted(os.listdir(_presets_dir())):
            if f.endswith(".json"):
                names.append(f[:-5])
    except OSError:
        pass
    if not names:
        names = list(catalog.PRESET_NAMES)
    ordered = [n for n in catalog.PRESET_NAMES if n in names]
    return ordered + [n for n in names if n not in ordered]


def preset_info(name):
    """{label, description, enabled:[ids], ui:{...}} (toujours valide)."""
    if name in _preset_cache:
        return copy.deepcopy(_preset_cache[name])
    raw = {}
    try:
        with open(os.path.join(_presets_dir(), "%s.json" % name), encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            raw = {}
    except Exception:
        raw = {}
    enabled = raw.get("enabled")
    if enabled == "all":
        ids = [e["id"] for e in catalog.CATALOG]
    elif isinstance(enabled, list):
        ids = [i for i in enabled if isinstance(i, str) and i in catalog.BY_ID]
    else:
        ids = catalog.ids_for_preset(name)
    ui = raw.get("ui") if isinstance(raw.get("ui"), dict) else {}
    info = {"label": str(raw.get("label") or name),
            "description": str(raw.get("description") or ""),
            "enabled": ids, "ui": _clean_ui(ui)}
    _preset_cache[name] = info
    return copy.deepcopy(info)


# --------------------------------------------------------------- nettoyage
def _clean_ui(ui):
    out = {}
    try:
        if "scale" in ui:
            out["scale"] = min(2.5, max(0.5, float(ui["scale"])))
        if "button_height" in ui:
            out["button_height"] = int(min(96, max(24, float(ui["button_height"]))))
        if ui.get("theme") in THEMES:
            out["theme"] = ui["theme"]
        gc = ui.get("guide_color")
        if isinstance(gc, str) and _COLOR_RE.match(gc):
            out["guide_color"] = gc.upper()
    except (TypeError, ValueError):
        pass
    return out


def _clean_trigger(t):
    if isinstance(t, dict) and t.get("type") in ("seq", "combo"):
        v = t.get("value")
        if isinstance(v, str) and v.strip():
            return {"type": t["type"], "value": v.strip() if t["type"] == "combo" else v}
    return None


def _empty_state():
    return {"preset": DEFAULT_PRESET,
            "overrides": {"enabled": {}, "shortcuts": {}, "ui": {}},
            "recent": [], "guide": False}


def _clean_state(raw):
    st = _empty_state()
    if not isinstance(raw, dict):
        return st
    if isinstance(raw.get("preset"), str) and raw["preset"] in preset_names():
        st["preset"] = raw["preset"]
    ov = raw.get("overrides") if isinstance(raw.get("overrides"), dict) else {}
    en = ov.get("enabled") if isinstance(ov.get("enabled"), dict) else {}
    st["overrides"]["enabled"] = {k: v for k, v in en.items()
                                  if k in catalog.BY_ID and isinstance(v, bool)}
    sc = ov.get("shortcuts") if isinstance(ov.get("shortcuts"), dict) else {}
    for k, v in sc.items():
        if k in catalog.BY_ID:
            if v is None:
                st["overrides"]["shortcuts"][k] = None
            elif _clean_trigger(v):
                st["overrides"]["shortcuts"][k] = _clean_trigger(v)
    ui = ov.get("ui") if isinstance(ov.get("ui"), dict) else {}
    st["overrides"]["ui"] = _clean_ui(ui)
    rec = raw.get("recent") if isinstance(raw.get("recent"), list) else []
    seen = []
    for r in rec:
        if isinstance(r, str) and r in catalog.BY_ID and r not in seen:
            seen.append(r)
    st["recent"] = seen[:RECENT_MAX]
    st["guide"] = bool(raw.get("guide", False))
    return st


# --------------------------------------------------------------- chargement
def load():
    """(Re)lit le fichier utilisateur ; retourne la config fusionnée."""
    global _state
    with _lock:
        raw = None
        try:
            with open(user_path(), encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            raw = None
        _state = _clean_state(raw)
    return get()


def _st():
    if _state is None:
        load()
    return _state


def _enabled_set(st):
    ids = set(preset_info(st["preset"])["enabled"])
    for k, v in st["overrides"]["enabled"].items():
        (ids.add if v else ids.discard)(k)
    return ids


def get():
    """Dict fusionné (copie) : preset, enabled, shortcuts, ui, recent, guide, overrides."""
    with _lock:
        st = _st()
        shortcuts = {}
        for e in catalog.CATALOG:
            shortcuts[e["id"]] = _trigger_of(st, e["id"])
        ui = dict(DEFAULT_UI)
        ui.update(preset_info(st["preset"])["ui"])
        ui.update(st["overrides"]["ui"])
        return {"preset": st["preset"],
                "enabled": [e["id"] for e in catalog.CATALOG if e["id"] in _enabled_set(st)],
                "shortcuts": shortcuts, "ui": ui,
                "recent": list(st["recent"]), "guide": st["guide"],
                "overrides": copy.deepcopy(st["overrides"])}


def _trigger_of(st, action_id):
    sc = st["overrides"]["shortcuts"]
    if action_id in sc:
        return copy.deepcopy(sc[action_id])
    e = catalog.BY_ID.get(action_id)
    return copy.deepcopy(e["trigger"]) if e else None


# --------------------------------------------------------------- lecture
def is_enabled(action_id):
    if action_id == "open_settings":
        return True  # toujours accessible, sinon impossible de revenir aux réglages
    with _lock:
        return action_id in catalog.BY_ID and action_id in _enabled_set(_st())


def trigger(action_id):
    with _lock:
        return _trigger_of(_st(), action_id)


def shortcut_text(action_id):
    t = trigger(action_id)
    return t["value"] if t else ""


def tooltip(action_id):
    e = catalog.BY_ID.get(action_id)
    if e is None:
        return ""
    s = shortcut_text(action_id)
    return "%s [ %s ]" % (e["title"], s if s else "clic")


def active_triggers():
    """[(action_id, trigger, word)] des actions activées ayant un raccourci."""
    out = []
    with _lock:
        st = _st()
        en = _enabled_set(st)
        for e in catalog.CATALOG:
            t = _trigger_of(st, e["id"])
            if t and e["id"] in en:
                out.append((e["id"], t, e["word"]))
    return out


def ui():
    return get()["ui"]


def recent():
    with _lock:
        return list(_st()["recent"])


def guide():
    with _lock:
        return _st()["guide"]


# --------------------------------------------------------------- écriture
def push_recent(action_id):
    """Place l'action en tête des récents (max 6, sans doublon) et enregistre."""
    if action_id not in catalog.BY_ID:
        return
    with _lock:
        rec = _st()["recent"]
        if rec and rec[0] == action_id:
            return
        _st()["recent"] = ([action_id] + [r for r in rec if r != action_id])[:RECENT_MAX]
    save()


def set_guide(value):
    with _lock:
        _st()["guide"] = bool(value)


def set_preset(name, keep_overrides=False):
    """Change de preset ; efface par défaut les activations perso (enabled)."""
    if name not in preset_names():
        return False
    with _lock:
        st = _st()
        st["preset"] = name
        if not keep_overrides:
            st["overrides"]["enabled"] = {}
    return True


def _walk(path):
    if (not isinstance(path, (list, tuple)) or len(path) != 2
            or path[0] not in ("enabled", "shortcuts", "ui")):
        raise ValueError("chemin invalide : %r" % (path,))
    return path[0], path[1]


def set_override(path_list, value):
    """set_override(["enabled","matrix"], True) ; ["shortcuts","fraction"],
    trigger|None ; ["ui","scale"], 1.2. Valeur invalide : ignorée (False)."""
    try:
        section, key = _walk(path_list)
    except ValueError:
        return False
    with _lock:
        ov = _st()["overrides"]
        if section == "enabled":
            if key not in catalog.BY_ID or not isinstance(value, bool):
                return False
            ov["enabled"][key] = value
        elif section == "shortcuts":
            if key not in catalog.BY_ID:
                return False
            if value is None:
                ov["shortcuts"][key] = None
            else:
                t = _clean_trigger(value)
                if not t:
                    return False
                ov["shortcuts"][key] = t
        else:
            clean = _clean_ui({key: value})
            if key not in clean:
                return False
            ov["ui"][key] = clean[key]
    return True


def clear_override(path_list=None):
    """Retire un override (retour au preset/défaut) ; sans argument : tous."""
    with _lock:
        ov = _st()["overrides"]
        if not path_list:
            _st()["overrides"] = _empty_state()["overrides"]
            return True
        if len(path_list) == 1 and path_list[0] in ov:
            ov[path_list[0]] = {}
            return True
        try:
            section, key = _walk(path_list)
        except ValueError:
            return False
        ov[section].pop(key, None)
    return True


def reset():
    """Retour aux défauts (preset standard, aucun override, récents vidés) + save."""
    global _state
    with _lock:
        _state = _empty_state()
    save()


def save():
    """Écrit le fichier (atomique, best effort) puis prévient les abonnés."""
    with _lock:
        data = copy.deepcopy(_st())
    try:
        path = user_path()
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        _log("config.save")
    _notify()


def subscribe(cb):
    with _lock:
        if cb not in _subscribers:
            _subscribers.append(cb)


def unsubscribe(cb):
    with _lock:
        if cb in _subscribers:
            _subscribers.remove(cb)


def _notify():
    with _lock:
        cbs = list(_subscribers)
    for cb in cbs:
        try:
            cb()
        except Exception:
            _log("config subscriber")


# --------------------------------------------------------------- validation
def _norm(t):
    v = t["value"]
    return v.lower() if t["type"] == "combo" else v


def validate_shortcuts(shortcuts=None):
    """Conflits entre raccourcis des actions activées.

    ``shortcuts`` : dict id -> trigger|None à tester (sinon config courante ;
    sert à valider l'écran de réglages avant enregistrement).
    Retourne [{"ids":[a,b], "reason": "..."}] : doublon ou préfixe (une
    séquence qui en préfixe une autre empêcherait la seconde de se déclencher).
    """
    items = []
    with _lock:
        st = _st()
        en = _enabled_set(st)
        for e in catalog.CATALOG:
            if shortcuts is not None and e["id"] in shortcuts:
                t = _clean_trigger(shortcuts[e["id"]])
            else:
                t = _trigger_of(st, e["id"])
            if t and e["id"] in en:
                items.append((e["id"], t))
    out = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (a, ta), (b, tb) = items[i], items[j]
            if ta["type"] != tb["type"]:
                continue
            va, vb = _norm(ta), _norm(tb)
            ea, eb = catalog.BY_ID[a]["title"], catalog.BY_ID[b]["title"]
            if va == vb:
                out.append({"ids": [a, b], "reason":
                            "« %s » est utilisé deux fois (%s et %s)." % (ta["value"], ea, eb)})
            elif ta["type"] == "seq" and (va.startswith(vb) or vb.startswith(va)):
                out.append({"ids": [a, b], "reason":
                            "« %s » commence comme « %s » (%s et %s) : "
                            "l'un des deux ne se déclencherait jamais."
                            % (ta["value"], tb["value"], ea, eb)})
    return out
