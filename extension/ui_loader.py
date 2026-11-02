# -*- coding: utf-8 -*-
"""Mini-loader Glade (GTK3 .ui) -> controles UNO (awt) pour le plugin Maths.

Widgets geres: GtkButton, GtkToggleButton, GtkCheckButton, GtkEntry,
GtkComboBoxText, GtkLabel, GtkSeparator, GtkGrid, GtkBox, GtkExpander
(accordeon), GtkNotebook (onglets = rangee de boutons + pages affichees /
masquees), GtkScrolledWindow / GtkViewport (traverses, sans scroll propre).
Tout widget inconnu est ignore silencieusement.

Comportement pilote par config.py (import protege, tout est optionnel):
- btn_<id> / tgl_<id> visible ssi config.is_enabled(id) (uniquement pour les
  ids du catalogue; les autres boutons, ex. btn_settings_save, restent visibles);
- infobulle = config.tooltip(id), repli sur tooltip_text du .ui;
- btn_recent_0..5 + lbl_recent: alimentes par config.recent();
- theme / echelle / hauteur des boutons = config.ui();
- refresh() ré-applique tout; abonne a config.subscribe tant que le panneau vit.

Layout manuel en pixels. Pas de scroll interne: la deck de la sidebar defile
grace a la hauteur renvoyee par PanelUI.height_for_width().
Aucune exception ne remonte vers LibreOffice (journal sur stderr).
"""
import itertools
import sys
import traceback
import xml.etree.ElementTree as ET

try:
    import unohelper
    from com.sun.star.awt import XActionListener, XWindowListener
    HAVE_UNO = True
except Exception:  # hors LibreOffice (tests, py_compile)
    HAVE_UNO = False

    # Classes DISTINCTES: sinon "duplicate base class object" a la definition
    # de classes heritant de Base + une interface.
    class _Base(object):
        pass

    class _Stub(object):
        Base = _Base
    unohelper = _Stub()

    class XActionListener(object):
        pass

    class XWindowListener(object):
        pass

try:  # config.py est ecrit en parallele: jamais bloquant
    import config as _config
except Exception:
    _config = None
try:
    import catalog as _catalog
except Exception:
    _catalog = None

PAD = 8
GAP = 6
BTN_H = 44
HEADER_H = 40
LABEL_H = 24
FIELD_H = 32
CHECK_H = 28
SEP_H = 8
TAB_H = 36
POSSIZE_ALL = 15
MIN_WIDTH = 180
MAX_RECENT = 6

_MODELS = {
    "button": "com.sun.star.awt.UnoControlButtonModel",
    "toggle": "com.sun.star.awt.UnoControlButtonModel",
    "header": "com.sun.star.awt.UnoControlButtonModel",
    "tab": "com.sun.star.awt.UnoControlButtonModel",
    "label": "com.sun.star.awt.UnoControlFixedTextModel",
    "check": "com.sun.star.awt.UnoControlCheckBoxModel",
    "entry": "com.sun.star.awt.UnoControlEditModel",
    "combo": "com.sun.star.awt.UnoControlListBoxModel",
    "separator": "com.sun.star.awt.UnoControlFixedLineModel",
}

# Themes: jamais de rouge agressif. Couleurs RGB 0xRRGGBB.
THEMES = {
    "clair": {"bg": 0xFFFFFF, "text": 0x1F2933, "btn": 0xE8EEF6, "tab_on": 0xC9D8EC},
    "doux": {"bg": 0xF6F0E1, "text": 0x3B3A36, "btn": 0xE9DFC6, "tab_on": 0xD9C9A0},
    "contraste": {"bg": 0x111111, "text": 0xFFFFFF, "btn": 0x2E2E2E, "tab_on": 0x55555F},
}
OK_COLOR = 0x2E7D32      # vert doux
KO_COLOR = 0xC2610C      # orange doux


def _log(msg):
    try:
        sys.stderr.write("[plugin-maths] %s\n" % msg)
    except Exception:
        pass


def _log_exc(where):
    _log("%s: %s" % (where, traceback.format_exc()))


def _set(model, name, value):
    try:
        model.setPropertyValue(name, value)
    except Exception:
        pass


def _get(model, name, default=None):
    try:
        return model.getPropertyValue(name)
    except Exception:
        return default


# ------------------------------------------------------------ acces a config
def _is_catalog_id(aid):
    if _catalog is None:
        return False
    try:
        return aid in _catalog.BY_ID
    except Exception:
        return False


def _enabled(cfg, aid):
    if cfg is None or not _is_catalog_id(aid):
        return True
    try:
        return bool(cfg.is_enabled(aid))
    except Exception:
        return True


def _tooltip(cfg, aid, fallback):
    if cfg is not None and _is_catalog_id(aid):
        try:
            t = cfg.tooltip(aid)
            if t:
                return t
        except Exception:
            pass
    return fallback


def _ui_settings(cfg):
    ui = {}
    if cfg is not None:
        try:
            ui = dict(cfg.ui() or {})
        except Exception:
            ui = {}
    try:
        scale = float(ui.get("scale", 1.0))
    except (TypeError, ValueError):
        scale = 1.0
    scale = min(max(scale, 0.6), 2.0)
    try:
        bh = float(ui.get("button_height", BTN_H))
    except (TypeError, ValueError):
        bh = BTN_H
    bh = min(max(bh, 24.0), 120.0)
    theme = ui.get("theme", "clair")
    if theme not in THEMES:
        theme = "clair"
    return {"scale": scale, "button_height": bh, "theme": theme}


def _recent_ids(cfg):
    if cfg is None:
        return []
    try:
        return [r for r in list(cfg.recent() or []) if isinstance(r, str)][:MAX_RECENT]
    except Exception:
        return []


def _label_of(aid):
    try:
        return _catalog.BY_ID[aid]["label"]
    except Exception:
        return aid


# ----------------------------------------------------------------- listeners
class _ActionListener(unohelper.Base, XActionListener):
    def __init__(self, callback):
        self._cb = callback

    def actionPerformed(self, ev):
        try:
            self._cb()
        except Exception:
            _log_exc("action")

    def disposing(self, ev):
        pass


class _ResizeListener(unohelper.Base, XWindowListener):
    def __init__(self, callback):
        self._cb = callback

    def windowResized(self, ev):
        try:
            self._cb()
        except Exception:
            _log_exc("resize")

    def windowMoved(self, ev):
        pass

    def windowShown(self, ev):
        pass

    def windowHidden(self, ev):
        pass

    def disposing(self, ev):
        pass


# ------------------------------------------------------------- layout nodes
class _Leaf(object):
    """Un controle UNO. ``user_hidden`` (set_visible) et ``cfg_hidden`` (config)."""

    def __init__(self, kind, wid, label, tooltip, height):
        self.kind, self.wid, self.label, self.tooltip = kind, wid, label, tooltip
        self.base_height = height
        self.height = height
        self.items, self.active, self.text, self.checked = [], 0, "", False
        self.user_hidden = False
        self.cfg_hidden = False
        self.color = None          # couleur de texte imposee (resultat verif)
        self.wrap = False
        self.ctrl = None
        self.col, self.row = 0, 0

    @property
    def hidden(self):
        return self.user_hidden or self.cfg_hidden

    def leaves(self):
        return [self]

    def has_visible(self):
        return not self.hidden

    def place(self, x, y, w, visible):
        if self.ctrl is None:
            return 0
        try:
            if not visible or self.hidden:
                self.ctrl.setVisible(False)
                return 0
            self.ctrl.setPosSize(int(x), int(y), int(max(w, 1)), int(self.height), POSSIZE_ALL)
            self.ctrl.setVisible(True)
        except Exception:
            _log_exc("place " + str(self.wid))
        return self.height


class _Stack(object):
    col, row = 0, 0

    def __init__(self, children):
        self.children = children

    def leaves(self):
        return [l for c in self.children for l in c.leaves()]

    def has_visible(self):
        return any(c.has_visible() for c in self.children)

    def place(self, x, y, w, visible):
        cy = y
        for c in self.children:
            h = c.place(x, cy, w, visible)
            if h > 0:
                cy += h + GAP
        return max(cy - y - GAP, 0)


class _Grid(object):
    col, row = 0, 0

    def __init__(self, children):
        self.children = children  # .col / .row fournis par le .ui

    def leaves(self):
        return [l for c in self.children for l in c.leaves()]

    def has_visible(self):
        return any(c.has_visible() for c in self.children)

    def place(self, x, y, w, visible):
        if not self.children:
            return 0
        ncols = max(c.col for c in self.children) + 1
        cw = (w - GAP * (ncols - 1)) / float(ncols)
        cy = y
        if all(isinstance(c, _Leaf) for c in self.children):
            # Reflux: les boutons masques ne laissent pas de trou.
            order = sorted(self.children, key=lambda c: (c.row, c.col))
            shown = [c for c in order if visible and not c.hidden]
            for c in order:
                if c not in shown:
                    c.place(0, 0, 1, False)
            rowh = 0
            for i, c in enumerate(shown):
                col, row = i % ncols, i // ncols
                if col == 0 and row > 0:
                    cy += rowh + GAP
                    rowh = 0
                rowh = max(rowh, c.place(x + col * (cw + GAP), cy, cw, True))
            return (cy + rowh - y) if shown else 0
        for r in sorted(set(c.row for c in self.children)):
            rh = 0
            for c in [c for c in self.children if c.row == r]:
                rh = max(rh, c.place(x + c.col * (cw + GAP), cy, cw, visible))
            if rh > 0:
                cy += rh + GAP
        return max(cy - y - GAP, 0)


class _Expander(object):
    def __init__(self, title, expanded, header, body):
        self.title, self.expanded, self.header, self.body = title, expanded, header, body
        self.col, self.row = 0, 0

    def leaves(self):
        return [self.header] + self.body.leaves()

    def has_visible(self):
        return self.body.has_visible()

    def place(self, x, y, w, visible):
        if not visible or not self.body.has_visible():
            # section sans aucun bouton visible: masquee en entier
            self.header.place(0, 0, 1, False)
            self.body.place(0, 0, 1, False)
            return 0
        h = self.header.place(x, y, w, True)
        show = self.expanded
        bh = self.body.place(x, y + h + GAP, w, show)
        return h + (GAP + bh if show and bh > 0 else 0)


class _Notebook(object):
    """Onglets: rangee de boutons (``tabs``) + une seule page visible."""

    def __init__(self, tabs, pages):
        self.tabs, self.pages, self.active = tabs, pages, 0
        self.col, self.row = 0, 0

    def leaves(self):
        return list(self.tabs) + [l for p in self.pages for l in p.leaves()]

    def has_visible(self):
        return True

    def place(self, x, y, w, visible):
        if not visible or not self.pages:
            for t in self.tabs:
                t.place(0, 0, 1, False)
            for p in self.pages:
                p.place(0, 0, 1, False)
            return 0
        n = max(len(self.tabs), 1)
        cw = (w - GAP * (n - 1)) / float(n)
        for i, t in enumerate(self.tabs):
            t.place(x + i * (cw + GAP), y, cw, True)
        cy = y + TAB_H + GAP
        for i, p in enumerate(self.pages):
            h = p.place(x, cy, w, i == self.active)
            if i == self.active:
                cy += h
        return cy - y


# ------------------------------------------------------------------- parsing
def _props(obj):
    out = {}
    if obj is None:
        return out
    for p in obj.findall("property"):
        n = p.get("name")
        if n:
            out[n.replace("-", "_")] = (p.text or "").strip()
    return out


def _is_false(v):
    return str(v).strip().lower() in ("false", "0", "no")


def _is_true(v):
    return str(v).strip().lower() in ("true", "1", "yes")


def _int(v, default):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _build(obj, counter):
    """Retourne un noeud de layout, ou None (widget inconnu / invisible)."""
    cls = obj.get("class") or ""
    wid = obj.get("id") or ""
    pr = _props(obj)
    if _is_false(pr.get("visible", "True")):
        return None
    tip = pr.get("tooltip_text", "")
    if cls in ("GtkButton", "GtkToggleButton"):
        if not wid:
            return None
        leaf = _Leaf("toggle" if cls == "GtkToggleButton" else "button", wid,
                     pr.get("label", ""), tip, max(_int(pr.get("height_request"), BTN_H), 24))
        leaf.checked = _is_true(pr.get("active", "False"))
        return leaf
    if cls == "GtkCheckButton":
        if not wid:
            return None
        leaf = _Leaf("check", wid, pr.get("label", ""), tip, CHECK_H)
        leaf.checked = _is_true(pr.get("active", "False"))
        return leaf
    if cls == "GtkEntry":
        if not wid:
            return None
        leaf = _Leaf("entry", wid, "", tip, max(_int(pr.get("height_request"), FIELD_H), 22))
        leaf.text = pr.get("text", "")
        return leaf
    if cls == "GtkComboBoxText":
        if not wid:
            return None
        leaf = _Leaf("combo", wid, "", tip, max(_int(pr.get("height_request"), FIELD_H), 22))
        items = obj.find("items")
        if items is not None:
            leaf.items = [(i.text or "").strip() for i in items.findall("item")]
        leaf.active = _int(pr.get("active"), 0)
        return leaf
    if cls == "GtkLabel":
        leaf = _Leaf("label", wid or "lbl_%d" % next(counter), pr.get("label", ""), tip,
                     max(_int(pr.get("height_request"), LABEL_H), 14))
        leaf.wrap = _is_true(pr.get("wrap", "False"))
        return leaf
    if cls == "GtkSeparator":
        return _Leaf("separator", wid or "sep_%d" % next(counter), "", "", SEP_H)
    if cls == "GtkNotebook":
        return _build_notebook(obj, wid or "nb_%d" % next(counter), counter)
    kids = []
    for ch in obj.findall("child"):
        if ch.get("type") == "label":
            continue
        sub = ch.find("object")
        if sub is None:
            continue
        node = _build(sub, counter)
        if node is None:
            continue
        pk = _props(ch.find("packing"))
        node.col = _int(pk.get("left_attach"), node.col)
        node.row = _int(pk.get("top_attach"), node.row)
        kids.append(node)
    if cls == "GtkExpander":
        header = _Leaf("header", "hdr_%d" % next(counter), "", "", HEADER_H)
        return _Expander(pr.get("label", ""), not _is_false(pr.get("expanded", "False")),
                         header, _Stack(kids))
    if cls == "GtkGrid":
        return _Grid(kids) if kids else None
    if cls == "GtkBox" and pr.get("orientation", "horizontal") == "horizontal":
        for i, k in enumerate(kids):
            k.col, k.row = i, 0
        return _Grid(kids) if kids else None
    if kids:  # GtkBox vertical, GtkWindow, GtkScrolledWindow, GtkViewport, ...
        for i, k in enumerate(kids):
            k.col, k.row = 0, i
        return _Stack(kids)
    return None


def _build_notebook(obj, nid, counter):
    pages, titles = [], []
    for ch in obj.findall("child"):
        sub = ch.find("object")
        if sub is None:
            continue
        if ch.get("type") == "tab":
            titles.append(_props(sub).get("label", ""))
            continue
        node = _build(sub, counter)
        if node is not None:
            pages.append(node)
    tabs = []
    for i in range(len(pages)):
        title = titles[i] if i < len(titles) and titles[i] else "Page %d" % (i + 1)
        tabs.append(_Leaf("tab", "%s_tab_%d" % (nid, i), title, "", TAB_H))
    if not pages:
        return None
    return _Notebook(tabs, pages)


def parse_ui(ui_path):
    """Parse le .ui; retourne la liste des noeuds de premier niveau."""
    root = ET.parse(ui_path).getroot()
    counter = itertools.count()
    nodes = []
    for obj in root.findall("object"):
        node = _build(obj, counter)
        if node is not None:
            nodes.append(node)
    return nodes


def _action_id(wid):
    for pre in ("btn_", "tgl_"):
        if wid.startswith(pre):
            return wid[len(pre):]
    return None


# --------------------------------------------------------------------- UI
class PanelUI(object):
    """Contenu d'un panneau/fenetre: controles, layout, valeurs, config."""

    def __init__(self, ctx, parent_window, ui_path, on_action, on_layout_changed=None, cfg=None):
        self.ctx = ctx
        self.on_action = on_action
        self.on_layout_changed = on_layout_changed
        self.cfg = cfg if cfg is not None else _config
        self.window = None
        self.height = 0
        self.width = MIN_WIDTH
        self._nodes = []
        self._by_id = {}
        self._notebooks = []
        self._listeners = []
        self._recent = []
        self._parent = parent_window
        self._container = None
        self._resize_listener = None
        self._cfg_cb = None
        self._disposed = False
        self._st = _ui_settings(None)
        try:
            self._nodes = parse_ui(ui_path)
            self._index()
            self._create_container()
            self._create_controls()
            self._apply_config()
            self.relayout()
            self._subscribe()
        except Exception:
            _log_exc("PanelUI init")

    # -- construction
    def _index(self):
        def walk(n):
            if isinstance(n, _Notebook):
                self._notebooks.append(n)
                for p in n.pages:
                    walk(p)
            elif isinstance(n, _Expander):
                walk(n.body)
            elif isinstance(n, (_Stack, _Grid)):
                for c in n.children:
                    walk(c)
        for n in self._nodes:
            walk(n)
        for leaf in self._all_leaves():
            if leaf.kind not in ("header", "tab"):
                self._by_id[leaf.wid] = leaf

    def _create_container(self):
        smgr = self.ctx.getServiceManager()
        model = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlContainerModel", self.ctx)
        ctrl = smgr.createInstanceWithContext("com.sun.star.awt.UnoControlContainer", self.ctx)
        ctrl.setModel(model)
        toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx)
        ctrl.createPeer(toolkit, self._parent)
        try:
            r = self._parent.getPosSize()
            self.width = max(int(r.Width), MIN_WIDTH)
        except Exception:
            pass
        ctrl.setPosSize(0, 0, self.width, 10, POSSIZE_ALL)
        ctrl.setVisible(True)
        self._container, self._cmodel, self.window = ctrl, model, ctrl
        try:
            self._resize_listener = _ResizeListener(self._on_parent_resized)
            self._parent.addWindowListener(self._resize_listener)
        except Exception:
            self._resize_listener = None

    def _all_leaves(self):
        return [l for n in self._nodes for l in n.leaves()]

    def _create_controls(self):
        exp_by_header, nb_by_tab = {}, {}

        def collect(n):
            if isinstance(n, _Expander):
                exp_by_header[id(n.header)] = n
                collect(n.body)
            elif isinstance(n, _Notebook):
                for i, t in enumerate(n.tabs):
                    nb_by_tab[id(t)] = (n, i)
                for p in n.pages:
                    collect(p)
            elif isinstance(n, (_Stack, _Grid)):
                for c in n.children:
                    collect(c)
        for n in self._nodes:
            collect(n)
        for leaf in self._all_leaves():
            try:
                self._make_leaf(leaf, exp_by_header.get(id(leaf)), nb_by_tab.get(id(leaf)))
            except Exception:
                _log_exc("leaf " + str(leaf.wid))

    def _make_leaf(self, leaf, expander, nbtab):
        m = self._cmodel.createInstance(_MODELS[leaf.kind])
        k = leaf.kind
        if k == "header":
            _set(m, "Label", self._header_text(expander))
            _set(m, "Align", 0)
        elif k == "separator":
            _set(m, "Orientation", 0)
        elif k == "entry":
            _set(m, "Text", leaf.text)
        elif k == "combo":
            _set(m, "Dropdown", True)
            _set(m, "StringItemList", tuple(leaf.items))
            _set(m, "LineCount", max(min(len(leaf.items), 10), 1))
            if leaf.items:
                _set(m, "SelectedItems", (min(max(leaf.active, 0), len(leaf.items) - 1),))
        else:
            _set(m, "Label", leaf.label)
        if k == "label" and leaf.wrap:
            _set(m, "MultiLine", True)
        if k == "check":
            _set(m, "State", 1 if leaf.checked else 0)
        if k == "toggle":
            _set(m, "Toggle", True)
            _set(m, "State", 1 if leaf.checked else 0)
        if leaf.tooltip:
            _set(m, "HelpText", leaf.tooltip)
        self._cmodel.insertByName(leaf.wid, m)
        ctrl = self._container.getControl(leaf.wid)
        leaf.ctrl = ctrl
        if k == "header":
            cb = (lambda e=expander: self._toggle(e))
        elif k == "tab":
            cb = (lambda n=nbtab[0], i=nbtab[1]: self._select_tab(n, i))
        elif k in ("button", "toggle"):
            aid = _action_id(leaf.wid)
            if aid is None:
                return
            cb = (lambda a=aid: self._fire(a))
        else:
            return
        lis = _ActionListener(cb)
        ctrl.addActionListener(lis)
        self._listeners.append((ctrl, lis))

    @staticmethod
    def _font(model, height, bold=False):
        try:
            fd = model.getPropertyValue("FontDescriptor")
            fd.Height = height
            fd.Weight = 150.0 if bold else 100.0
            model.setPropertyValue("FontDescriptor", fd)
        except Exception:
            pass

    @staticmethod
    def _header_text(exp):
        return ("▾  " if exp.expanded else "▸  ") + exp.title

    # -- theme / config
    def _apply_config(self):
        """Visibilite, infobulles, recents, theme, tailles. Ne relayoute pas."""
        cfg = self.cfg
        self._st = st = _ui_settings(cfg)
        sc = st["scale"]
        th = THEMES[st["theme"]]
        try:
            _set(self._cmodel, "BackgroundColor", th["bg"])
        except Exception:
            pass
        self._recent = _recent_ids(cfg)
        for leaf in self._all_leaves():
            self._style_leaf(leaf, st, th, sc)
        self._apply_recents()
        for nb in self._notebooks:
            self._style_tabs(nb, th)

    def _style_leaf(self, leaf, st, th, sc):
        k = leaf.kind
        m = leaf.ctrl.getModel() if leaf.ctrl is not None else None
        if m is None:
            return
        aid = _action_id(leaf.wid) if k in ("button", "toggle") else None
        if aid is not None and not aid.startswith("recent_"):
            leaf.cfg_hidden = not _enabled(self.cfg, aid)
            tip = _tooltip(self.cfg, aid, leaf.tooltip)
            if tip:
                _set(m, "HelpText", tip)
        if k in ("button", "toggle"):
            leaf.height = int(round(st["button_height"] * sc))
            self._font(m, 14.0 * sc)
            _set(m, "BackgroundColor", th["btn"])
            _set(m, "TextColor", th["text"])
        elif k == "header":
            leaf.height = int(round(HEADER_H * sc))
            self._font(m, 11.0 * sc, bold=True)
            _set(m, "BackgroundColor", th["bg"])
            _set(m, "TextColor", th["text"])
        elif k == "tab":
            leaf.height = int(round(TAB_H * sc))
            self._font(m, 11.0 * sc)
            _set(m, "TextColor", th["text"])
        elif k == "label":
            leaf.height = int(round(leaf.base_height * sc))
            self._font(m, 10.5 * sc)
            _set(m, "BackgroundColor", th["bg"])
            _set(m, "TextColor", leaf.color if leaf.color is not None else th["text"])
        elif k == "check":
            leaf.height = int(round(leaf.base_height * sc))
            self._font(m, 11.0 * sc)
            _set(m, "BackgroundColor", th["bg"])
            _set(m, "TextColor", th["text"])
        elif k in ("entry", "combo"):
            leaf.height = int(round(leaf.base_height * sc))
            self._font(m, 12.0 * sc)

    def _style_tabs(self, nb, th):
        for i, t in enumerate(nb.tabs):
            if t.ctrl is None:
                continue
            m = t.ctrl.getModel()
            on = (i == nb.active)
            _set(m, "BackgroundColor", th["tab_on"] if on else th["btn"])
            self._font(m, 11.0 * self._st["scale"], bold=on)

    def _apply_recents(self):
        """btn_recent_N: libelle (catalogue) et visibilite selon config.recent()."""
        any_recent = False
        for i in range(MAX_RECENT):
            leaf = self._by_id.get("btn_recent_%d" % i)
            if leaf is None:
                continue
            if i < len(self._recent) and _enabled(self.cfg, self._recent[i]):
                aid = self._recent[i]
                leaf.cfg_hidden = False
                any_recent = True
                if leaf.ctrl is not None:
                    m = leaf.ctrl.getModel()
                    _set(m, "Label", _label_of(aid))
                    _set(m, "HelpText", _tooltip(self.cfg, aid, "Action récente"))
            else:
                leaf.cfg_hidden = True
        lbl = self._by_id.get("lbl_recent")
        if lbl is not None:
            lbl.cfg_hidden = not any_recent

    # -- actions
    def _values_snapshot(self):
        try:
            return self.get_values()
        except Exception:
            return {}

    def _fire(self, action_id):
        try:
            if action_id.startswith("recent_"):
                idx = _int(action_id[len("recent_"):], -1)
                if not 0 <= idx < len(self._recent):
                    return
                action_id = self._recent[idx]
            self.on_action(action_id, self._values_snapshot())
        except Exception:
            _log_exc("on_action " + str(action_id))

    def _toggle(self, exp):
        exp.expanded = not exp.expanded
        try:
            self._container.getControl(exp.header.wid).getModel().setPropertyValue(
                "Label", self._header_text(exp))
        except Exception:
            pass
        self.relayout()
        self._notify_layout()

    def _select_tab(self, nb, index):
        nb.active = index
        try:
            self._style_tabs(nb, THEMES[self._st["theme"]])
        except Exception:
            _log_exc("tabs")
        self.relayout()
        self._notify_layout()

    def _notify_layout(self):
        if self.on_layout_changed:
            try:
                self.on_layout_changed()
            except Exception:
                _log_exc("on_layout_changed")

    # -- API valeurs
    def get_value(self, wid):
        leaf = self._by_id.get(wid)
        if leaf is None or leaf.ctrl is None:
            return None
        m = leaf.ctrl.getModel()
        k = leaf.kind
        if k in ("toggle", "check"):
            return bool(_get(m, "State", 0))
        if k == "entry":
            return _get(m, "Text", "") or ""
        if k == "combo":
            sel = _get(m, "SelectedItems", ()) or ()
            items = _get(m, "StringItemList", ()) or ()
            if sel and 0 <= sel[0] < len(items):
                return items[sel[0]]
            return ""
        if k == "label":
            return _get(m, "Label", "") or ""
        return None

    def set_value(self, wid, value):
        leaf = self._by_id.get(wid)
        if leaf is None or leaf.ctrl is None:
            return
        m = leaf.ctrl.getModel()
        k = leaf.kind
        if k in ("toggle", "check"):
            _set(m, "State", 1 if value else 0)
        elif k == "entry":
            _set(m, "Text", "" if value is None else str(value))
        elif k == "combo":
            items = list(_get(m, "StringItemList", ()) or ())
            if isinstance(value, int) and not isinstance(value, bool):
                idx = value
            else:
                idx = items.index(value) if value in items else -1
            if 0 <= idx < len(items):
                _set(m, "SelectedItems", (idx,))
        elif k == "label":
            _set(m, "Label", "" if value is None else str(value))

    def get_values(self):
        """id -> valeur pour entry / check / combo / toggle."""
        out = {}
        for wid, leaf in self._by_id.items():
            if leaf.kind in ("entry", "check", "combo", "toggle"):
                out[wid] = self.get_value(wid)
        return out

    def set_text(self, wid, text, color=None):
        """Texte d'un label (ou bouton); ``color`` = entier 0xRRGGBB ou None (theme)."""
        leaf = self._by_id.get(wid)
        if leaf is None or leaf.ctrl is None:
            return
        leaf.color = color
        m = leaf.ctrl.getModel()
        _set(m, "Label", "" if text is None else str(text))
        if leaf.kind == "label":
            _set(m, "TextColor", color if color is not None else THEMES[self._st["theme"]]["text"])

    def set_visible(self, wid, visible):
        leaf = self._by_id.get(wid)
        if leaf is None:
            return
        leaf.user_hidden = not visible
        self.relayout()

    # -- layout
    def _on_parent_resized(self):
        try:
            r = self._parent.getPosSize()
            w = max(int(r.Width), MIN_WIDTH)
        except Exception:
            return
        if w != self.width:
            self.width = w
            self.relayout()

    def relayout(self, width=None):
        """Recalcule les positions; retourne la hauteur totale (px)."""
        if self._disposed:
            return self.height
        try:
            if width:
                self.width = max(int(width), MIN_WIDTH)
            y = PAD
            for n in self._nodes:
                h = n.place(PAD, y, self.width - 2 * PAD, True)
                if h > 0:
                    y += h + GAP
            self.height = max(y + PAD - GAP, 2 * PAD)
            if self.window is not None:
                self.window.setPosSize(0, 0, self.width, self.height, POSSIZE_ALL)
        except Exception:
            _log_exc("relayout")
        return self.height

    def height_for_width(self, width):
        return self.relayout(width)

    def refresh(self):
        """Ré-applique config (visibilite, tooltips, recents, theme, tailles)."""
        if self._disposed or self.window is None:
            return
        try:
            self._apply_config()
        except Exception:
            _log_exc("refresh")
        self.relayout()

    # -- abonnement config
    def _subscribe(self):
        if self.cfg is None or not hasattr(self.cfg, "subscribe"):
            return
        try:
            self._cfg_cb = self._on_config_changed
            self.cfg.subscribe(self._cfg_cb)
        except Exception:
            self._cfg_cb = None
            _log_exc("subscribe")

    def _on_config_changed(self, *args):
        try:
            self.refresh()
            self._notify_layout()
        except Exception:
            _log_exc("config callback")

    def dispose(self):
        self._disposed = True
        try:
            if self._cfg_cb is not None and self.cfg is not None:
                try:
                    self.cfg.unsubscribe(self._cfg_cb)
                except Exception:
                    pass
            self._cfg_cb = None
            if self._resize_listener is not None:
                self._parent.removeWindowListener(self._resize_listener)
            for ctrl, lis in self._listeners:
                try:
                    ctrl.removeActionListener(lis)
                except Exception:
                    pass
            self._listeners = []
            if self.window is not None:
                self.window.dispose()
        except Exception:
            _log_exc("dispose")
        self.window = None


def load_ui(ctx, parent_window, ui_path, on_action, cfg=None, on_layout_changed=None):
    """Retourne un PanelUI (jamais d'exception).

    ``on_action(action_id, values)``; ``values`` = get_values() au moment du clic.
    ``cfg``: module/objet de config (defaut: module ``config`` s'il existe).
    """
    return PanelUI(ctx, parent_window, ui_path, on_action, on_layout_changed, cfg)


def load_into(ctx, parent_window, ui_path, on_action):
    """API du contrat v1: ``on_action(action_id)``; retourne le XWindow (ou None)."""
    return load_ui(ctx, parent_window, ui_path, lambda a, v: on_action(a)).window
