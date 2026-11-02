# -*- coding: utf-8 -*-
"""Panneau lateral (sidebar) Maths: fabrique + element UI."""
import os
import sys
import traceback

try:
    import uno
    import unohelper
    from com.sun.star.lang import XServiceInfo
    from com.sun.star.ui import XUIElementFactory, XUIElement, XToolPanel, XSidebarPanel
    HAVE_UNO = True
except Exception:  # hors LibreOffice (tests, py_compile)
    uno = None
    HAVE_UNO = False

    # Bases de repli DISTINCTES: "XServiceInfo = XUIElement = ... = object"
    # donnait "duplicate base class object" des que deux interfaces (ou
    # Base + une interface) etaient heritees ensemble.
    class _StubBase(object):
        pass

    class _Stub(object):
        Base = _StubBase
    unohelper = _Stub()

    class XServiceInfo(object):
        pass

    class XUIElementFactory(object):
        pass

    class XUIElement(object):
        pass

    class XToolPanel(object):
        pass

    class XSidebarPanel(object):
        pass

IMPL_NAME = "fr.aifedespaix.plugin_maths.PanelFactory"
SERVICE_NAMES = ("com.sun.star.ui.UIElementFactory",)
PANEL_URL = "private:resource/toolpanel/MathsPanelFactory/MathsPanel"
EXTENSION_ID = "fr.aifedespaix.plugin-maths"
UIELEMENT_TYPE_TOOLPANEL = 7


def _log_exc(where):
    msg = "%s: %s" % (where, traceback.format_exc())
    try:
        sys.stderr.write("[plugin-maths] %s\n" % msg)
    except Exception:
        pass
    try:  # journal lisible sous Windows: %TEMP%\\plugin-maths.log
        import tempfile
        with open(os.path.join(tempfile.gettempdir(), "plugin-maths.log"), "a",
                  encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def _ui_path(ctx):
    """Chemin systeme de ui/sidebar.ui (via PackageInformationProvider, sinon relatif)."""
    try:
        pip = ctx.getValueByName("/singletons/com.sun.star.deployment.PackageInformationProvider")
        url = pip.getPackageLocation(EXTENSION_ID)
        if url:
            return uno.fileUrlToSystemPath(url.rstrip("/") + "/ui/sidebar.ui")
    except Exception:
        _log_exc("package location")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "sidebar.ui")


OK_COLOR = 0x2E7D32   # vert doux
KO_COLOR = 0xC2610C   # orange doux (jamais de rouge agressif)


class MathsPanel(unohelper.Base, XSidebarPanel, XUIElement, XToolPanel):
    def __init__(self, ctx, frame, parent_window, url, sidebar):
        self.ctx, self.frame, self.url, self.sidebar = ctx, frame, url, sidebar
        self.parent_window = parent_window
        self.ui = None
        try:
            from ui_loader import load_ui
            self.ui = load_ui(ctx, parent_window, _ui_path(ctx), self._on_action,
                              on_layout_changed=self._request_layout)
            self._sync_guide()
        except Exception:
            _log_exc("load ui")

    def _sync_guide(self):
        """Aligne le toggle du guidage sur l'etat du document courant."""
        try:
            if self.ui is None:
                return
            import math_insert
            state = None
            if hasattr(math_insert, "sync_guide_state"):
                state = math_insert.sync_guide_state(self.ctx)
            self.ui.set_value("tgl_guide", bool(state))
        except Exception:
            _log_exc("sync guide")

    def _composer_action(self, action_id, values):
        """Bloc formule: ouvre / valide / annule. Retourne True si traite."""
        if self.ui is None:
            return False
        import composer
        if action_id == "composer_cancel":
            self.ui.close_composer()
            self._request_layout()
            return True
        if action_id == "composer_ok":
            import actions
            cid = self.ui.composer_id
            if cid:
                formula = composer.build(cid, self.ui.composer_values())
                self.ui.close_composer()
                actions.insert_formula(self.ctx, cid, formula)
            self._after_action(action_id, None)
            return True
        spec = composer.spec_for(action_id)
        if spec is None:
            return False
        import actions
        if self.ui.open_composer(spec, actions.selected_text(self.ctx)):
            self._request_layout()
            return True
        return False

    def _on_action(self, action_id, values=None):
        result = None
        try:
            if self._composer_action(action_id, values):
                return
        except Exception:
            _log_exc("composer " + str(action_id))
        try:
            import actions
            try:
                result = actions.dispatch(self.ctx, action_id, values or {})
            except TypeError:  # ancienne signature dispatch(ctx, id)
                result = actions.dispatch(self.ctx, action_id)
        except Exception:
            _log_exc("dispatch " + str(action_id))
        self._after_action(action_id, result)

    def _after_action(self, action_id, result):
        try:
            if self.ui is None:
                return
            if isinstance(result, dict) and "text" in result:
                ok = result.get("ok")
                color = OK_COLOR if ok is True else KO_COLOR if ok is False else None
                self.ui.set_text("lbl_verify_result", result.get("text", ""), color)
            if action_id == "guide":
                self._sync_guide()
            self.ui.refresh()  # recents mis a jour, config relue
            self._request_layout()
        except Exception:
            _log_exc("after action")

    def _request_layout(self):
        try:
            if self.sidebar is not None:
                self.sidebar.requestLayout()
        except Exception:
            _log_exc("requestLayout")

    # XSidebarPanel
    def getHeightForWidth(self, width):
        h = 200
        try:
            if self.ui is not None:
                h = self.ui.height_for_width(width)
        except Exception:
            _log_exc("height")
        # min = max = preferred: la deck defile si le contenu depasse.
        if uno is None:
            return (h, h, h)
        return uno.createUnoStruct("com.sun.star.ui.LayoutSize", h, h, h)

    def getMinimalWidth(self):
        return 200

    # XUIElement
    def getFrame(self):
        return self.frame

    def getResourceURL(self):
        return self.url

    def getType(self):
        return UIELEMENT_TYPE_TOOLPANEL

    def getRealInterface(self):
        return self.ui.window if self.ui is not None else None

    # XToolPanel
    def getWindow(self):
        return self.getRealInterface()

    def createAccessible(self, parent):
        return None

    # XComponent
    def dispose(self):
        try:
            if self.ui is not None:
                self.ui.dispose()
        except Exception:
            _log_exc("dispose")
        self.ui = None

    def addEventListener(self, listener):
        pass

    def removeEventListener(self, listener):
        pass


class MathsPanelFactory(unohelper.Base, XUIElementFactory, XServiceInfo):
    def __init__(self, ctx):
        self.ctx = ctx

    def createUIElement(self, url, args):
        if url != PANEL_URL:
            from com.sun.star.container import NoSuchElementException
            raise NoSuchElementException(url, self)
        props = {}
        for a in args:
            props[a.Name] = a.Value
        parent = props.get("ParentWindow")
        if parent is None:
            from com.sun.star.lang import IllegalArgumentException
            raise IllegalArgumentException("ParentWindow manquant", self, 1)
        return MathsPanel(self.ctx, props.get("Frame"), parent, url, props.get("Sidebar"))

    # XServiceInfo
    def getImplementationName(self):
        return IMPL_NAME

    def supportsService(self, name):
        return name in SERVICE_NAMES

    def getSupportedServiceNames(self):
        return SERVICE_NAMES
