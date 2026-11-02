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

# Séquence tapée -> action_id (voir actions.FORMULAS).
SEQUENCES = {
    "//": "fraction", "sqrt": "sqrt", "^^": "power", "__": "subscript",
    "vec": "vector", "+-": "plus_minus", "<=": "leq", ">=": "geq",
    "!=": "neq", "~=": "approx",
}
# Mots : ne se déclenchent pas au milieu d'un mot ("avec" ne doit pas donner "vec").
WORD_SEQUENCES = ("sqrt", "vec")
_ORDERED = sorted(SEQUENCES, key=len, reverse=True)
BUFFER_MAX = 8

# Codes de touches (com.sun.star.awt.Key) et modificateurs (KeyModifier).
KEY_G, KEY_E = 518, 516                    # A=512 -> G=518, E=516
KEY_BACKSPACE = 1283
MOD_CTRL, MOD_ALT = 2, 4                   # MOD1 (Ctrl), MOD2 (Alt)
SHORTCUT_COMBOS = {KEY_G: "guide", KEY_E: "align_equals"}  # avec Ctrl+Alt


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
