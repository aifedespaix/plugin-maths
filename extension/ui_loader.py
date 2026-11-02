# -*- coding: utf-8 -*-
"""Mini-loader Glade (GTK3 .ui) -> controles UNO (awt) pour le panneau Maths.

Principes:
- parse le .ui avec xml.etree, ignore silencieusement tout widget inconnu;
- GtkButton / GtkToggleButton -> bouton UNO; GtkLabel -> texte fixe;
  GtkGrid -> grille; GtkBox -> pile (verticale) ou ligne (horizontale);
  GtkExpander -> en-tete cliquable + groupe de controles afficher/masquer;
- layout manuel en pixels, recalcule au redimensionnement et au repli/depli;
- aucune exception ne remonte vers LibreOffice (tout est journalise sur stderr).
Limite: pas de scroll interne; c'est la deck de la sidebar qui defile, grace a
la hauteur renvoyee par PanelUI.height_for_width().
"""
import sys
import traceback
import xml.etree.ElementTree as ET

try:
    import unohelper
    from com.sun.star.awt import XActionListener, XWindowListener
    HAVE_UNO = True
except Exception:  # hors LibreOffice (tests, py_compile)
    HAVE_UNO = False

    class _Stub(object):
        Base = object
    unohelper = _Stub()
    XActionListener = object
    XWindowListener = object

PAD = 8
GAP = 6
BTN_H = 44
HEADER_H = 40
LABEL_H = 24
POSSIZE_ALL = 15
MIN_WIDTH = 180

_MODELS = {
    "button": "com.sun.star.awt.UnoControlButtonModel",
    "toggle": "com.sun.star.awt.UnoControlButtonModel",
    "header": "com.sun.star.awt.UnoControlButtonModel",
    "label": "com.sun.star.awt.UnoControlFixedTextModel",
}


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
    def __init__(self, kind, wid, label, tooltip, height):
        self.kind, self.wid, self.label, self.tooltip = kind, wid, label, tooltip
        self.height = height
        self.ctrl = None
        self.col, self.row = 0, 0

    def leaves(self):
        return [self]

    def place(self, x, y, w, visible):
        if self.ctrl is not None:
            try:
                self.ctrl.setPosSize(int(x), int(y), int(max(w, 1)), self.height, POSSIZE_ALL)
                self.ctrl.setVisible(bool(visible))
            except Exception:
                _log_exc("place " + str(self.wid))
        return self.height


class _Stack(object):
    col, row = 0, 0

    def __init__(self, children):
        self.children = children

    def leaves(self):
        return [l for c in self.children for l in c.leaves()]

    def place(self, x, y, w, visible):
        cy = y
        for c in self.children:
            h = c.place(x, cy, w, visible)
            cy += h + (GAP if visible else 0)
        return max(cy - y - GAP, 0) if visible and self.children else 0


class _Grid(object):
    col, row = 0, 0

    def __init__(self, children):
        self.children = children  # _Leaf/_Stack/_Expander avec .col/.row

    def leaves(self):
        return [l for c in self.children for l in c.leaves()]

    def place(self, x, y, w, visible):
        if not self.children:
            return 0
        ncols = max(c.col for c in self.children) + 1
        cw = (w - GAP * (ncols - 1)) / float(ncols)
        rows = sorted(set(c.row for c in self.children))
        cy = y
        for r in rows:
            rh = 0
            for c in [c for c in self.children if c.row == r]:
                rh = max(rh, c.place(x + c.col * (cw + GAP), cy, cw, visible))
            cy += rh + (GAP if visible else 0)
        return max(cy - y - GAP, 0) if visible else 0


class _Expander(object):
    def __init__(self, title, expanded, header, body):
        self.title, self.expanded, self.header, self.body = title, expanded, header, body
        self.col, self.row = 0, 0

    def leaves(self):
        return [self.header] + self.body.leaves()

    def place(self, x, y, w, visible):
        h = self.header.place(x, y, w, visible)
        show = visible and self.expanded
        bh = self.body.place(x, y + h + GAP, w, show)
        return h + (GAP + bh if show else 0)


# ------------------------------------------------------------------- parsing
def _props(obj):
    out = {}
    for p in obj.findall("property"):
        n = p.get("name")
        if n:
            out[n.replace("-", "_")] = (p.text or "").strip()
    return out


def _is_false(v):
    return str(v).strip().lower() in ("false", "0", "no")


def _build(obj, counter):
    """Retourne un noeud de layout, ou None (widget inconnu / invisible)."""
    cls = obj.get("class") or ""
    wid = obj.get("id") or ""
    pr = _props(obj)
    if _is_false(pr.get("visible", "True")):
        return None
    if cls in ("GtkButton", "GtkToggleButton"):
        if not wid:
            return None
        try:
            h = int(pr.get("height_request", "") or BTN_H)
        except ValueError:
            h = BTN_H
        return _Leaf("toggle" if cls == "GtkToggleButton" else "button",
                     wid, pr.get("label", ""), pr.get("tooltip_text", ""), max(h, 24))
    if cls == "GtkLabel":
        return _Leaf("label", wid or "lbl_%d" % next(counter), pr.get("label", ""), pr.get("tooltip_text", ""), LABEL_H)
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
        pk = _props(ch.find("packing")) if ch.find("packing") is not None else {}
        try:
            node.col = int(pk.get("left_attach", node.col))
            node.row = int(pk.get("top_attach", node.row))
        except ValueError:
            pass
        kids.append(node)
    if cls == "GtkExpander":
        title = pr.get("label", "")
        expanded = not _is_false(pr.get("expanded", "False"))
        header = _Leaf("header", "hdr_%d" % next(counter), "", "", HEADER_H)
        return _Expander(title, expanded, header, _Stack(kids))
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
    return None  # widget inconnu sans enfant: ignore


def parse_ui(ui_path):
    """Parse le .ui; retourne la liste des noeuds de premier niveau."""
    import itertools
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
    """Contenu du panneau: construit les controles, gere layout et repli."""

    def __init__(self, ctx, parent_window, ui_path, on_action, on_layout_changed=None):
        self.ctx = ctx
        self.on_action = on_action
        self.on_layout_changed = on_layout_changed
        self.window = None
        self.height = 0
        self.width = MIN_WIDTH
        self._nodes = []
        self._listeners = []
        self._parent = parent_window
        self._container = None
        self._resize_listener = None
        try:
            self._nodes = parse_ui(ui_path)
            self._create_container()
            self._create_controls()
            self.relayout()
        except Exception:
            _log_exc("PanelUI init")

    # -- construction
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
        exp_by_header = {}

        def collect(n):
            if isinstance(n, _Expander):
                exp_by_header[id(n.header)] = n
                collect(n.body)
            elif isinstance(n, (_Stack, _Grid)):
                for c in n.children:
                    collect(c)
        for n in self._nodes:
            collect(n)
        for leaf in self._all_leaves():
            try:
                self._make_leaf(leaf, exp_by_header.get(id(leaf)))
            except Exception:
                _log_exc("leaf " + str(leaf.wid))

    def _make_leaf(self, leaf, expander):
        name = leaf.wid
        m = self._cmodel.createInstance(_MODELS[leaf.kind])
        if leaf.kind == "header":
            _set(m, "Label", self._header_text(expander))
            _set(m, "Align", 0)
        else:
            _set(m, "Label", leaf.label)
        if leaf.tooltip:
            _set(m, "HelpText", leaf.tooltip)
        if leaf.kind == "toggle":
            _set(m, "Toggle", True)
        if leaf.kind in ("button", "toggle"):
            self._bigger_font(m, 14.0)
        elif leaf.kind == "header":
            self._bigger_font(m, 11.0, bold=True)
        self._cmodel.insertByName(name, m)
        ctrl = self._container.getControl(name)
        leaf.ctrl = ctrl
        if leaf.kind == "header":
            cb = (lambda e=expander: self._toggle(e))
        elif leaf.kind in ("button", "toggle"):
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
    def _bigger_font(model, height, bold=False):
        try:
            fd = model.getPropertyValue("FontDescriptor")
            fd.Height = height
            if bold:
                fd.Weight = 150.0
            model.setPropertyValue("FontDescriptor", fd)
        except Exception:
            pass

    @staticmethod
    def _header_text(exp):
        return ("▾  " if exp.expanded else "▸  ") + exp.title

    # -- actions
    def _fire(self, action_id):
        try:
            self.on_action(action_id)
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
        if self.on_layout_changed:
            try:
                self.on_layout_changed()
            except Exception:
                _log_exc("on_layout_changed")

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
        try:
            if width:
                self.width = max(int(width), MIN_WIDTH)
            y = PAD
            for n in self._nodes:
                y += n.place(PAD, y, self.width - 2 * PAD, True) + GAP
            self.height = y + PAD - GAP
            if self.window is not None:
                self.window.setPosSize(0, 0, self.width, self.height, POSSIZE_ALL)
        except Exception:
            _log_exc("relayout")
        return self.height

    def height_for_width(self, width):
        return self.relayout(width)

    def dispose(self):
        try:
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


def load_ui(ctx, parent_window, ui_path, on_action, on_layout_changed=None):
    """Retourne un PanelUI (jamais d'exception)."""
    return PanelUI(ctx, parent_window, ui_path, on_action, on_layout_changed)


def load_into(ctx, parent_window, ui_path, on_action):
    """API du contrat: retourne le XWindow du contenu (ou None en cas d'echec)."""
    return load_ui(ctx, parent_window, ui_path, on_action).window
