# -*- coding: utf-8 -*-
"""Point d'entrée de l'extension (seul fichier déclaré uno-component Python).

Enregistre :
* ``Startup`` : job lancé sur OnNew / OnLoad / OnViewCreated, qui installe le
  KeyHandler sur la fenêtre du document ;
* ``MathsPanelFactory`` (sidebar.py) : fabrique du panneau latéral.
"""
import os
import sys

# Les modules frères (keyhandler, actions...) sont dans le même dossier que
# main.py : on l'ajoute au chemin de recherche Python.
try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:  # pragma: no cover
    _HERE = None
if _HERE and _HERE not in sys.path:
    sys.path.insert(0, _HERE)

try:  # pragma: no cover - dépend de LibreOffice
    import unohelper
    from com.sun.star.task import XJob
except ImportError:  # hors LibreOffice
    class _Base(object):
        pass

    class XJob(object):
        pass

    class _Helper(object):
        def addImplementation(self, *args):
            pass
    unohelper = None
    _UnoBase = _Base
    g_ImplementationHelper = _Helper()
else:
    _UnoBase = unohelper.Base
    g_ImplementationHelper = unohelper.ImplementationHelper()

import keyhandler
import math_insert

try:  # sidebar.py est écrit à part : main.py doit rester importable sans lui
    from sidebar import MathsPanelFactory
except Exception:  # ImportError ou erreur dans sidebar.py
    MathsPanelFactory = None
    math_insert.log_exception("import sidebar")

STARTUP_IMPL_NAME = "fr.aifedespaix.plugin_maths.Startup"


def _find_controller(ctx, env):
    """Controller du document concerné par l'événement (ou du doc courant)."""
    for item in env:
        if item.Name == "Model" and item.Value is not None:
            return item.Value.getCurrentController()
        if item.Name == "Frame" and item.Value is not None:
            return item.Value.getController()
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    comp = desktop.getCurrentComponent()
    return comp.getCurrentController() if comp is not None else None


class Startup(_UnoBase, XJob):
    """Job déclenché par les événements document (voir Jobs.xcu)."""

    def __init__(self, ctx):
        self.ctx = ctx

    def execute(self, args):
        try:
            env = ()
            for arg in args:
                if arg.Name == "Environment":
                    env = arg.Value
            controller = _find_controller(self.ctx, env)
            keyhandler.install(self.ctx, controller)
        except Exception:
            math_insert.log_exception("Startup.execute")
        return ()


g_ImplementationHelper.addImplementation(
    Startup, STARTUP_IMPL_NAME, ("com.sun.star.task.Job",))

if MathsPanelFactory is not None:
    g_ImplementationHelper.addImplementation(
        MathsPanelFactory,
        getattr(sys.modules.get("sidebar"), "IMPL_NAME", "fr.aifedespaix.plugin_maths.PanelFactory"),
        getattr(sys.modules.get("sidebar"), "SERVICE_NAMES", ("com.sun.star.ui.UIElementFactory",)))
