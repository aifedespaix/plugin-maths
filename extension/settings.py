# -*- coding: utf-8 -*-
"""Ecran de reglages (fenetre non modale) du plugin Maths.

Charge ui/settings.ui avec ui_loader.load_ui. Les cases ``chk_<id>`` et les
champs ``ent_shortcut_<id>`` sont lus/ecrits dynamiquement: un widget absent du
.ui est simplement ignore. Seules les differences avec le profil (preset) sont
stockees comme surcharges dans la config utilisateur.

Limites: l'API exacte de lecture des GtkComboBoxText (texte ou index) depend
de ui_loader; ``_combo_index`` accepte les deux. Aucune exception ne remonte.
"""
import re
import sys
import traceback

try:
    import uno
    import unohelper
    from com.sun.star.awt import XTopWindowListener
    HAVE_UNO = True
except Exception:  # hors LibreOffice
    HAVE_UNO = False
    uno = None

    class _Stub(object):
        Base = object
    unohelper = _Stub()
    XTopWindowListener = object

try:
    import catalog
except Exception:
    catalog = None
try:
    import config
except Exception:
    config = None
try:
    import ui_loader
except Exception:
    ui_loader = None

EXT_ID = "fr.aifedespaix.plugin-maths"
PRESETS = ["simple", "standard", "complet"]
THEMES = ["auto", "clair", "doux", "sombre", "contraste"]
SCALES = [0.8, 1.0, 1.2, 1.4, 1.6]
HEIGHTS = [36, 44, 52, 60]
GUIDE_COLORS = ["#FFF3C4", "#DCEBFF", "#DDF3DD", "#FBE3EC", "#E8E8E8"]
THEME_LABELS = ["Automatique (suit LibreOffice)", "Clair", "Doux", "Sombre", "Contraste élevé"]
SCALE_LABELS = ["80 %", "100 %", "120 %", "140 %", "160 %"]
HEIGHT_LABELS = ["Petite (36)", "Normale (44)", "Grande (52)", "Très grande (60)"]
COLOR_LABELS = ["Jaune clair", "Bleu clair", "Vert clair", "Rose clair", "Gris clair"]
PRESET_LABELS = ["Simple", "Standard", "Complet"]
OK_COLOR = 0x2E7D32
WARN_COLOR = 0xB65A00
_MODS = ("ctrl", "alt", "shift", "strg", "altgr")

_state = {"dialog": None, "ui": None, "listener": None}


def _log(msg):
    try:
        sys.stderr.write("[plugin-maths] settings: %s\n" % msg)
    except Exception:
        pass


def _log_exc(where):
    _log("%s: %s" % (where, traceback.format_exc()))


# ------------------------------------------------------------------ helpers
def _combo_index(value, labels, values=None):
    """Retourne l'index choisi a partir d'un index ou d'un texte; -1 sinon."""
    try:
        if isinstance(value, bool):
            return -1
        if isinstance(value, int):
            return value if 0 <= value < len(labels) else -1
        s = str(value).strip().lower()
        for i, lab in enumerate(labels):
            if s == lab.lower():
                return i
        if values is not None:
            for i, v in enumerate(values):
                if s == str(v).lower():
                    return i
    except Exception:
        pass
    return -1


def _nearest(values, x, default_index):
    try:
        return min(range(len(values)), key=lambda i: abs(values[i] - float(x)))
    except Exception:
        return default_index


def parse_shortcut(text):
    """'Ctrl+Alt+G' -> combo, '//' -> sequence, '' -> None."""
    t = (text or "").strip()
    if not t:
        return None
    parts = [p.strip() for p in t.split("+")]
    if len(parts) >= 2 and parts[0].lower() in _MODS:
        return {"type": "combo", "value": "+".join(p[:1].upper() + p[1:] if len(p) > 1 else p.upper()
                                                    for p in parts)}
    return {"type": "seq", "value": t}


def _default_enabled(preset):
    """Ensemble des ids actives par defaut dans un profil."""
    ids = None
    try:
        info = config.preset_info(preset) or {}
        en = info.get("enabled")
        if en == "all":
            return None  # tout
        if isinstance(en, (list, tuple)):
            ids = set(en)
    except Exception:
        pass
    if ids is None:
        try:
            ids = set(catalog.ids_for_preset(preset))
        except Exception:
            ids = set()
    return ids


def _action_ids():
    try:
        return [e["id"] for e in catalog.CATALOG]
    except Exception:
        return []


def _default_trigger(aid):
    try:
        return catalog.BY_ID[aid].get("trigger")
    except Exception:
        return None


def _shortcut_text(aid):
    try:
        return config.shortcut_text(aid) or ""
    except Exception:
        return ""


# --------------------------------------------------------------- population
def _populate(ui):
    """Remplit les widgets depuis la config courante."""
    cfg = config.get() if config else {}
    preset = cfg.get("preset", "standard")
    for aid in _action_ids():
        try:
            ui.set_value("chk_" + aid, bool(config.is_enabled(aid)))
            ui.set_value("ent_shortcut_" + aid, _shortcut_text(aid))
        except Exception:
            pass
    pi = _combo_index(preset, PRESET_LABELS, PRESETS)
    _safe_set(ui, "cmb_preset", PRESET_LABELS[pi if pi >= 0 else 1])
    _show_preset_desc(ui, PRESETS[pi if pi >= 0 else 1])
    u = config.ui() if config else {}
    _safe_set(ui, "cmb_theme", THEME_LABELS[_idx(THEMES, u.get("theme"), 0)])
    _safe_set(ui, "cmb_scale", SCALE_LABELS[_nearest(SCALES, u.get("scale", 1.0), 1)])
    _safe_set(ui, "cmb_button_height", HEIGHT_LABELS[_nearest(HEIGHTS, u.get("button_height", 44), 1)])
    col = str(u.get("guide_color", "#FFF3C4")).upper()
    _safe_set(ui, "cmb_guide_color", COLOR_LABELS[_idx([c.upper() for c in GUIDE_COLORS], col, 0)])
    _show_conflicts(ui)


def _idx(values, v, default):
    try:
        return values.index(v)
    except Exception:
        return default


def _safe_set(ui, wid, value):
    try:
        ui.set_value(wid, value)
    except Exception:
        _log_exc("set_value " + wid)


def _show_preset_desc(ui, preset):
    desc = ""
    try:
        desc = (config.preset_info(preset) or {}).get("description", "")
    except Exception:
        pass
    try:
        ui.set_text("lbl_preset_desc", desc)
    except Exception:
        pass


def _show_conflicts(ui, conflicts=None):
    try:
        if conflicts is None:
            conflicts = config.validate_shortcuts() if config else []
        if conflicts:
            ui.set_text("lbl_settings_conflicts", _conflict_message(conflicts), WARN_COLOR)
        else:
            ui.set_text("lbl_settings_conflicts", "")
    except Exception:
        pass


def _title(aid):
    try:
        return catalog.BY_ID[aid]["title"]
    except Exception:
        return aid


def _conflict_message(conflicts):
    lines = []
    for c in conflicts[:3]:
        try:
            names = " et ".join("« %s »" % _title(i) for i in c.get("ids", []))
            lines.append("Raccourcis en conflit : %s (%s)" % (names, c.get("reason", "")))
        except Exception:
            pass
    if len(conflicts) > 3:
        lines.append("... et %d autre(s)." % (len(conflicts) - 3))
    return "\n".join(lines)


# --------------------------------------------------------------- actions
def _apply_preset_to_checks(ui):
    v = ui.get_values()
    i = _combo_index(v.get("cmb_preset"), PRESET_LABELS, PRESETS)
    preset = PRESETS[i if i >= 0 else 1]
    en = _default_enabled(preset)
    for aid in _action_ids():
        _safe_set(ui, "chk_" + aid, True if en is None else (aid in en))
    _show_preset_desc(ui, preset)
    ui.set_text("lbl_settings_status", "Profil appliqué aux cases. Clique sur « Enregistrer » pour le garder.")


def _save(ui):
    v = ui.get_values()
    i = _combo_index(v.get("cmb_preset"), PRESET_LABELS, PRESETS)
    preset = PRESETS[i if i >= 0 else 1]
    config.set_preset(preset)
    en = _default_enabled(preset)
    for aid in _action_ids():
        key = "chk_" + aid
        if key not in v:
            continue
        want = bool(v[key])
        default = True if en is None else (aid in en)
        if aid == "open_settings":
            continue
        if want == default:
            config.clear_override(["enabled", aid])
        else:
            config.set_override(["enabled", aid], want)
        skey = "ent_shortcut_" + aid
        if skey in v:
            trig = parse_shortcut(v[skey])
            dtrig = _default_trigger(aid)
            if trig == dtrig:
                config.clear_override(["shortcuts", aid])
            else:
                config.set_override(["shortcuts", aid], trig)
    # affichage
    for wid, labels, values, name in (
            ("cmb_theme", THEME_LABELS, THEMES, "theme"),
            ("cmb_scale", SCALE_LABELS, SCALES, "scale"),
            ("cmb_button_height", HEIGHT_LABELS, HEIGHTS, "button_height"),
            ("cmb_guide_color", COLOR_LABELS, GUIDE_COLORS, "guide_color")):
        if wid in v:
            k = _combo_index(v[wid], labels)
            if k >= 0:
                config.set_override(["ui", name], values[k])
    conflicts = config.validate_shortcuts()
    if conflicts:
        # on n'enregistre rien: relit la config disque pour annuler les surcharges en memoire
        try:
            config.load()
        except Exception:
            pass
        ui.set_text("lbl_settings_conflicts", _conflict_message(conflicts), WARN_COLOR)
        ui.set_text("lbl_settings_status", "Non enregistré : change un des raccourcis en conflit.", WARN_COLOR)
        return
    config.save()
    ui.set_text("lbl_settings_conflicts", "")
    ui.set_text("lbl_settings_status", "✓ Réglages enregistrés.", OK_COLOR)


def _reset(ui):
    config.reset()
    config.save()
    _populate(ui)
    ui.set_text("lbl_settings_status", "✓ Réglages remis par défaut.", OK_COLOR)


def _on_action(action_id, values=None):
    ui = _state.get("ui")
    try:
        if ui is None or config is None:
            return
        if action_id == "settings_save":
            _save(ui)
        elif action_id == "settings_reset":
            _reset(ui)
        elif action_id == "settings_preset":
            _apply_preset_to_checks(ui)
        elif action_id == "settings_close":
            close()
    except Exception:
        _log_exc("action " + str(action_id))
        try:
            ui.set_text("lbl_settings_status", "Une erreur est survenue. Réessaie.", WARN_COLOR)
        except Exception:
            pass


class _CloseListener(unohelper.Base, XTopWindowListener):
    def windowClosing(self, ev):
        try:
            close()
        except Exception:
            _log_exc("windowClosing")

    def windowOpened(self, ev):
        pass

    def windowClosed(self, ev):
        pass

    def windowMinimized(self, ev):
        pass

    def windowNormalized(self, ev):
        pass

    def windowActivated(self, ev):
        pass

    def windowDeactivated(self, ev):
        pass

    def disposing(self, ev):
        pass


def close():
    """Ferme la fenetre de reglages (idempotent)."""
    ui, dlg = _state.get("ui"), _state.get("dialog")
    _state.update(ui=None, dialog=None, listener=None)
    try:
        if ui is not None:
            ui.dispose()
    except Exception:
        _log_exc("ui.dispose")
    try:
        if dlg is not None:
            dlg.setVisible(False)
            dlg.dispose()
    except Exception:
        _log_exc("dialog.dispose")


def _ui_path(ctx):
    """Chemin systeme de ui/settings.ui (PackageInformationProvider, sinon relatif)."""
    try:
        pip = ctx.getValueByName("/singletons/com.sun.star.deployment.PackageInformationProvider")
        url = pip.getPackageLocation(EXT_ID)
        if url:
            return uno.fileUrlToSystemPath(url.rstrip("/") + "/ui/settings.ui")
    except Exception:
        pass
    import os
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "settings.ui")


def _create_dialog(ctx):
    smgr = ctx.getServiceManager()
    model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", ctx)
    try:
        model.setPropertyValue("Title", "Réglages du plugin Maths")
    except Exception:
        pass
    dlg = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlDialog", ctx)
    dlg.setModel(model)
    toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx)
    dlg.createPeer(toolkit, None)
    peer = dlg.getPeer()
    try:
        peer.setTitle("Réglages du plugin Maths")  # XDialog
    except Exception:
        pass
    dlg.setPosSize(120, 80, 600, 760, 15)
    return dlg, peer


def open_settings(ctx):
    """Ouvre (ou ramene au premier plan) la fenetre de reglages non modale."""
    try:
        if config is None or ui_loader is None or catalog is None:
            _log("modules config/ui_loader/catalog indisponibles")
            return
        dlg = _state.get("dialog")
        if dlg is not None:
            try:
                dlg.setVisible(True)
                dlg.toFront()
                return
            except Exception:
                close()
        dlg, peer = _create_dialog(ctx)
        ui = ui_loader.load_ui(ctx, peer, _ui_path(ctx), _on_action)
        _state.update(dialog=dlg, ui=ui)
        _populate(ui)
        try:
            lst = _CloseListener()
            dlg.addTopWindowListener(lst)
            _state["listener"] = lst
        except Exception:
            _log_exc("addTopWindowListener")
        dlg.setVisible(True)
    except Exception:
        _log_exc("open_settings")
