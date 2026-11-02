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
except Exception:  # hors LibreOffice
    HAVE_UNO = False

    class _Stub(object):
        Base = object
    unohelper = _Stub()
    XServiceInfo = XUIElementFactory = XUIElement = XToolPanel = XSidebarPanel = object

IMPL_NAME = "fr.aifedespaix.plugin_maths.PanelFactory"
SERVICE_NAMES = ("com.sun.star.ui.UIElementFactory",)
PANEL_URL = "private:resource/toolpanel/MathsPanelFactory/MathsPanel"
EXTENSION_ID = "fr.aifedespaix.plugin-maths"
UIELEMENT_TYPE_TOOLPANEL = 7


def _log_exc(where):
    try:
        sys.stderr.write("[plugin-maths] %s: %s\n" % (where, traceback.format_exc()))
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


class MathsPanel(unohelper.Base, XSidebarPanel, XUIElement, XToolPanel):
    def __init__(self, ctx, frame, parent_window, url, sidebar):
        self.ctx, self.frame, self.url, self.sidebar = ctx, frame, url, sidebar
        self.parent_window = parent_window
        self.ui = None
        try:
            from ui_loader import load_ui
            self.ui = load_ui(ctx, parent_window, _ui_path(ctx), self._on_action, self._request_layout)
        except Exception:
            _log_exc("load ui")

    def _on_action(self, action_id):
        try:
            import actions
            actions.dispatch(self.ctx, action_id)
        except Exception:
            _log_exc("dispatch " + str(action_id))

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
