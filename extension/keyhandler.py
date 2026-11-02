# -*- coding: utf-8 -*-
"""Détection des séquences tapées (``//``, ``sqrt``...) et raccourcis clavier.

La logique de détection (``match_sequence``) est pure Python et testable hors
LibreOffice. Le ``MathsKeyHandler`` fait le lien avec l'API UNO.
"""
import actions
import math_insert

try:  # pragma: no cover - dépend de LibreOffice
    import unohelper
    from com.sun.star.awt import XKeyHandler
except ImportError:  # hors LibreOffice : bases factices pour pouvoir importer
    class _Base(object):
        pass

    class XKeyHandler(object):
        pass
    unohelper = None
    _UnoBase = _Base
else:
    _UnoBase = unohelper.Base

# Valeurs de repli (config/catalog absents) : séquence -> action_id.
DEFAULT_SEQUENCES = {
    "//": "fraction", "sqrt": "sqrt", "^^": "power", "__": "subscript",
    "vec": "vector", "+-": "plus_minus", "<=": "leq", ">=": "geq",
    "!=": "neq", "~=": "approx",
}
DEFAULT_WORDS = frozenset(("sqrt", "vec"))      # ne se déclenchent pas dans un mot
DEFAULT_COMBOS = {"Ctrl+Alt+G": "guide", "Ctrl+Alt+E": "align_equals",
                  "Ctrl+Alt+Return": "equation_step"}
BUFFER_MAX = 12

# Tables actives, reconstruites par rebuild_tables() à chaque changement de config.
SEQUENCES = dict(DEFAULT_SEQUENCES)
WORD_SEQUENCES = set(DEFAULT_WORDS)
COMBOS = {}                  # (modificateurs, KeyCode) -> action_id
_ORDERED = []

# Codes de touches (com.sun.star.awt.Key) et modificateurs (KeyModifier).
KEY_TAB, KEY_RETURN, KEY_ESCAPE, KEY_BACKSPACE = 1282, 1280, 1281, 1283
MOD_SHIFT, MOD_CTRL, MOD_ALT = 1, 2, 4     # SHIFT, MOD1 (Ctrl), MOD2 (Alt)
_MOD_NAMES = {"ctrl": MOD_CTRL, "alt": MOD_ALT, "shift": MOD_SHIFT}


def key_code(name):
    """Nom de touche ("G", "7", "Return", "F5"...) -> KeyCode awt, ou None (pur)."""
    n = name.strip().lower()
    if len(n) == 1 and "a" <= n <= "z":
        return 512 + ord(n) - ord("a")        # A=512
    if len(n) == 1 and n.isdigit():
        return 256 + int(n)                   # NUM0=256
    if n in ("return", "enter"):
        return KEY_RETURN
    if n in ("tab",):
        return KEY_TAB
    if n in ("esc", "escape"):
        return KEY_ESCAPE
    if n == "space":
        return 1284
    if n.startswith("f") and n[1:].isdigit() and 1 <= int(n[1:]) <= 12:
        return 768 + int(n[1:]) - 1           # F1=768
    return None


def parse_combo(text):
    """"Ctrl+Alt+G" -> (modificateurs, KeyCode) ou None si invalide (pur)."""
    mods, code = 0, None
    for part in str(text or "").split("+"):
        low = part.strip().lower()
        if low in _MOD_NAMES:
            mods |= _MOD_NAMES[low]
        elif code is None and low:
            code = key_code(low)
        else:
            return None
    return (mods, code) if code is not None and mods else None


def build_tables(entries):
    """Construit (séquences, mots, combos) depuis une liste de triggers (pur).

    ``entries`` : itérable de ``(action_id, trigger_dict, word_bool)``.
    """
    seqs, words, combos = {}, set(), {}
    for action_id, trig, word in entries:
        if not trig:
            continue
        value = str(trig.get("value") or "")
        if trig.get("type") == "seq" and value:
            seqs[value] = action_id
            if word:
                words.add(value)
        elif trig.get("type") == "combo":
            parsed = parse_combo(value)
            if parsed:
                combos[parsed] = action_id
    return seqs, words, combos


def _config_entries():
    """Triggers actifs lus dans catalog/config ; None si ces modules manquent."""
    try:
        import catalog
        import config
    except Exception:
        return None
    out = []
    for item in catalog.CATALOG:
        aid = item["id"]
        try:
            if not config.is_enabled(aid) and item.get("kind") != "tool":
                continue
            if item.get("kind") == "tool" and not config.is_enabled(aid):
                continue
            out.append((aid, config.trigger(aid), bool(item.get("word"))))
        except Exception:
            math_insert.log_exception("_config_entries(%s)" % aid)
    return out


def rebuild_tables():
    """Reconstruit les tables de déclencheurs (config modifiée ou repli)."""
    global SEQUENCES, WORD_SEQUENCES, COMBOS, _ORDERED
    try:
        entries = _config_entries()
    except Exception:
        entries = None
        math_insert.log_exception("rebuild_tables")
    if entries is None:   # pas de catalog/config : table intégrée
        entries = [(a, {"type": "seq", "value": q}, q in DEFAULT_WORDS)
                   for q, a in DEFAULT_SEQUENCES.items()]
        entries += [(a, {"type": "combo", "value": c}, False) for c, a in DEFAULT_COMBOS.items()]
    SEQUENCES, WORD_SEQUENCES, COMBOS = build_tables(entries)
    _ORDERED = sorted(SEQUENCES, key=len, reverse=True)


_SUBSCRIBED = []


def _subscribe_config():
    """S'abonne (une fois) aux changements de config ; ignore l'absence de config."""
    if _SUBSCRIBED:
        return
    _SUBSCRIBED.append(True)
    try:
        import config
        config.subscribe(_on_config_changed)
    except Exception:
        pass


def _on_config_changed(*_args):
    rebuild_tables()
    for handler in list(_INSTALLED.values()):
        try:
            math_insert.sync_guide_state(handler.ctx)
        except Exception:
            pass
        break      # une seule resynchronisation suffit


def match_sequence(buffer, prev_char_fn=lambda n: ""):
    """Cherche une séquence qui termine ``buffer``.

    ``buffer`` contient les derniers caractères tapés, le dernier compris.
    ``prev_char_fn(n)`` renvoie le caractère du document situé juste avant la
    séquence de longueur ``n`` (utilisé quand le tampon est trop court pour
    le contenir ; le dernier caractère n'étant pas encore dans le document,
    il faut remonter de ``n`` positions).
    Retourne ``(sequence, action_id)`` ou ``None``.
    """
    for seq in _ORDERED:
        if not buffer.endswith(seq):
            continue
        n = len(seq)
        before = buffer[-n - 1] if len(buffer) > n else prev_char_fn(n)
        if seq in WORD_SEQUENCES and before and before.isalpha():
            continue          # anti-"avec" : la séquence est dans un mot
        if seq == "//" and before == ":":
            continue          # anti-URL : "http://"
        return seq, SEQUENCES[seq]
    return None


rebuild_tables()


def _as_char(key_char):
    """KeyChar UNO (str de 1 caractère, ou entier selon la version) -> str."""
    if isinstance(key_char, int):
        return chr(key_char) if key_char else ""
    return key_char or ""


class MathsKeyHandler(_UnoBase, XKeyHandler):
    """Remplace les séquences tapées par des formules. Ne casse jamais la frappe."""

    def __init__(self, ctx, controller):
        self.ctx = ctx
        self.controller = controller
        self.buffer = ""

    # --- XKeyHandler -------------------------------------------------------
    def keyPressed(self, ev):
        """Retourne True seulement si l'événement est consommé."""
        try:
            return self._on_key(ev)
        except Exception:
            self.buffer = ""
            math_insert.log_exception("keyPressed")
            return False       # en cas de doute, la frappe passe normalement

    def keyReleased(self, ev):
        return False

    def disposing(self, source):
        _INSTALLED.pop(id(self.controller), None)

    # --- logique -----------------------------------------------------------
    def _on_key(self, ev):
        mods, code = ev.Modifiers, ev.KeyCode
        char = _as_char(ev.KeyChar)
        ctrl, alt = bool(mods & MOD_CTRL), bool(mods & MOD_ALT)

        # Ctrl+Alt+G / Ctrl+Alt+E (on ignore AltGr+lettre qui produit un
        # caractère non ASCII comme "€").
        if ctrl and alt and code in SHORTCUT_COMBOS and (not char or ord(char) < 128):
            self.buffer = ""
            actions.run_action(self.controller.getModel(), SHORTCUT_COMBOS[code])
            return True

        if code == KEY_BACKSPACE and not (ctrl or alt):
            self.buffer = self.buffer[:-1]
            return False

        printable = len(char) == 1 and ord(char) >= 32 and ord(char) != 127
        # Ctrl seul ou Alt seul : raccourci d'un autre programme -> on ne touche à rien.
        # (Ctrl+Alt avec caractère imprimable = AltGr, ex. "~" : c'est de la frappe.)
        if (ctrl != alt) or not printable:
            self.buffer = ""
            return False

        self.buffer = (self.buffer + char)[-BUFFER_MAX:]
        view = self.controller.getViewCursor()
        if not view.isCollapsed():
            self.buffer = ""        # du texte est sélectionné : frappe normale
            return False
        found = match_sequence(self.buffer, lambda n: self._peek(view, n))
        if found is None:
            return False
        seq, action_id = found
        self.buffer = ""
        return self._replace(view, seq, action_id)

    @staticmethod
    def _peek(view, n):
        """Caractère situé n positions avant le curseur ('' si début du document)."""
        text = view.getText()
        cur = text.createTextCursorByRange(view.getStart())
        if not cur.goLeft(n, True):
            return ""
        s = cur.getString()
        return s[0] if len(s) == n else ""

    def _replace(self, view, seq, action_id):
        """Supprime les len(seq)-1 caractères déjà insérés puis insère la formule.

        Le dernier caractère de la séquence n'est pas encore dans le document
        (keyPressed arrive avant l'insertion) : en retournant True on le
        consomme, il ne sera jamais inséré.
        """
        n = len(seq) - 1
        if n > 0:
            view.goLeft(n, True)
            if view.getString() != seq[:-1]:      # le document ne correspond pas : on abandonne
                view.collapseToEnd()
                return False
            view.setString("")                    # supprime les caractères tapés
        actions.run_action(self.controller.getModel(), action_id)
        return True


# Gestionnaires installés (un par controller) ; garde aussi une référence
# Python pour que le handler ne soit pas ramassé.
_INSTALLED = {}


def install(ctx, controller):
    """Installe (une seule fois) le KeyHandler sur le controller Writer."""
    if controller is None or id(controller) in _INSTALLED:
        return _INSTALLED.get(id(controller))
    model = controller.getModel()
    if model is None or not model.supportsService("com.sun.star.text.TextDocument"):
        return None
    handler = MathsKeyHandler(ctx, controller)
    controller.addKeyHandler(handler)
    _INSTALLED[id(controller)] = handler
    return handler
