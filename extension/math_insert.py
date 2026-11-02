# -*- coding: utf-8 -*-
"""Insertion et gestion des formules (objets Math) dans Writer.

Ce module ne contient que de la logique "document" : il reçoit un document
Writer (``doc``) et agit dessus. Il ne connaît ni le clavier ni la sidebar.

Les imports ``uno`` sont protégés : le module reste importable hors
LibreOffice (tests de logique pure).
"""
import sys
import traceback

try:  # pragma: no cover - dépend de LibreOffice
    import uno
except ImportError:  # hors LibreOffice
    uno = None

# CLSID de l'objet "Formule" (LibreOffice Math) embarqué dans Writer.
MATH_CLSID = "078B7ABA-54FC-457F-8551-6147e776a997"
MARKER = "<?>"                    # champ vide StarMath (sauté avec F4)
GUIDE_PROP = "MathsGuide"         # propriété utilisateur du document
GUIDE_COLOR = 0xFFF3C4            # fond clair du guidage visuel
AS_CHARACTER = 1                  # TextContentAnchorType.AS_CHARACTER (valeur de l'enum)
EMBED_UI_ACTIVE = 3               # com.sun.star.embed.EmbedStates.UI_ACTIVE
PROPERTY_REMOVABLE = 128          # com.sun.star.beans.PropertyAttribute.REMOVABLE
HUNDREDTH_MM_PER_PT = 35.28       # 1 pt = 35,28 centièmes de mm


def log_exception(where):
    """Écrit la dernière exception sur stderr sans jamais la propager."""
    try:
        sys.stderr.write("[plugin-maths] erreur dans %s\n%s\n" % (where, traceback.format_exc()))
    except Exception:
        pass


def _anchor_as_character():
    """Valeur d'enum TextContentAnchorType.AS_CHARACTER (ou 1 hors UNO)."""
    if uno is not None:
        try:
            return uno.Enum("com.sun.star.text.TextContentAnchorType", "AS_CHARACTER")
        except Exception:
            pass
    return AS_CHARACTER


def fill_first_marker(formula, selected_text):
    """Remplace le 1er marqueur ``<?>`` par le texte sélectionné (logique pure).

    Un texte simple (lettres/chiffres) est mis tel quel ; sinon on le met entre
    guillemets pour que StarMath le traite comme du texte littéral.
    """
    text = (selected_text or "").strip()
    if not text or MARKER not in formula:
        return formula
    if not text.replace(".", "", 1).replace(",", "", 1).isalnum():
        text = '"%s"' % text.replace('"', "")
    return formula.replace(MARKER, text, 1)


# --------------------------------------------------------------------------
# Insertion
# --------------------------------------------------------------------------
def insert_math(doc, formula, tab_and_go=True):
    """Insère une formule StarMath comme objet Math *as-character* au curseur.

    Exemple pédagogique : ``insert_math(doc, "{<?>} over {<?>}")`` insère une
    fraction vide à l'endroit où se trouve le curseur, sans ouvrir la boîte
    de dialogue de Math, puis place l'élève dans le 1er champ à remplir.

    Étapes :
      1. On récupère le *view cursor* : c'est le curseur visible de
         l'utilisateur (le "|" qui clignote). Si du texte est sélectionné,
         ``getString()`` le renvoie : on s'en sert pour remplir le 1er champ.
      2. On demande au document de fabriquer un objet vide de type
         ``TextEmbeddedObject`` (un "objet OLE" Writer). Il n'est pas encore
         dans le texte : ``createInstance`` crée seulement l'objet.
      3. On lui donne le CLSID de Math (c'est ce qui dit "je suis une
         formule") et on l'ancre *comme un caractère* : la formule suit le
         texte comme une lettre, au lieu de flotter dans la page.
      4. ``insertTextContent(curseur, objet, remplacer)`` le place dans le
         texte. ``remplacer=True`` écrase la sélection ; sinon on insère à la
         position du curseur.
      5. Seulement après l'insertion, ``objet.EmbeddedObject`` donne accès au
         document Math lui-même : on écrit sa propriété ``Formula`` (le code
         StarMath). Les ``<?>`` sont des "marqueurs" : champs vides que la
         touche F4 de Math permet de parcourir.
      6. Si le guidage visuel est actif, on colore le fond de l'objet.
      7. Tab & Go (voir ``_tab_and_go``) : on active l'objet et on saute au
         premier marqueur pour que l'élève tape directement.

    Retourne l'objet inséré, ou ``None`` en cas d'échec (l'erreur est loggée,
    jamais propagée : ce code est appelé depuis le clavier).
    """
    try:
        controller = doc.getCurrentController()
        cursor = controller.getViewCursor()                      # (1)
        selected = "" if cursor.isCollapsed() else cursor.getString()
        formula = fill_first_marker(formula, selected)

        obj = doc.createInstance("com.sun.star.text.TextEmbeddedObject")   # (2)
        obj.CLSID = MATH_CLSID                                   # (3)
        obj.AnchorType = _anchor_as_character()

        # (4) True = remplace la sélection éventuelle
        cursor.getText().insertTextContent(cursor, obj, bool(selected))

        obj.EmbeddedObject.Formula = formula                     # (5)

        if is_guide_on(doc):                                     # (6)
            _apply_guide(obj, True)

        if tab_and_go and MARKER in formula:                     # (7)
            _tab_and_go(doc, obj)
        return obj
    except Exception:
        log_exception("insert_math")
        return None


def _tab_and_go(doc, obj):
    """Active l'objet formule et saute au premier marqueur ``<?>``.

    Limites de l'API (à connaître) :
    * il n'existe pas d'appel UNO officiel "éditer cet objet" ; on tente
      ``changeState(UI_ACTIVE)`` sur l'objet OLE, ce qui est ce que fait le
      double-clic. Selon la version, l'éditeur peut mettre un instant à
      prendre le focus : le saut peut alors ne pas avoir lieu.
    * le saut utilise la commande ``.uno:NextMark`` (F4 dans Math). Elle est
      envoyée au *frame* du document ; si le focus n'est pas encore dans
      l'éditeur de formule, elle est sans effet (pas d'erreur).
    Tout est en "meilleur effort" : un échec ne doit jamais gêner l'insertion.
    """
    try:
        doc.getCurrentController().select(obj)
        obj.getExtendedControlOverEmbeddedObject().changeState(EMBED_UI_ACTIVE)
    except Exception:
        log_exception("_tab_and_go/activate")
        return
    try:
        _dispatch_uno(doc, ".uno:NextMark")
    except Exception:
        log_exception("_tab_and_go/nextmark")


def _dispatch_uno(doc, command):
    """Envoie une commande .uno au frame du document."""
    ctx = uno.getComponentContext()
    smgr = ctx.ServiceManager
    helper = smgr.createInstanceWithContext("com.sun.star.frame.DispatchHelper", ctx)
    frame = doc.getCurrentController().getFrame()
    helper.executeDispatch(frame, command, "", 0, ())


# --------------------------------------------------------------------------
# Guidage visuel
# --------------------------------------------------------------------------
def _is_math_object(obj):
    try:
        return str(obj.CLSID).upper() == MATH_CLSID.upper()
    except Exception:
        return False


def iter_math_objects(doc):
    """Génère tous les objets formule (TextEmbeddedObject Math) du document."""
    try:
        embedded = doc.getEmbeddedObjects()
        for i in range(embedded.getCount()):
            obj = embedded.getByIndex(i)
            if _is_math_object(obj):
                yield obj
    except Exception:
        log_exception("iter_math_objects")


def _apply_guide(obj, enabled):
    """Colore (ou décolore) le fond d'un objet formule."""
    try:
        if enabled:
            obj.BackColor = GUIDE_COLOR
            obj.BackTransparent = False
        else:
            obj.BackTransparent = True
    except Exception:
        log_exception("_apply_guide")


def is_guide_on(doc):
    """Lit la propriété utilisateur ``MathsGuide`` du document (défaut : False)."""
    try:
        props = doc.getDocumentProperties().getUserDefinedProperties()
        return bool(props.getPropertyValue(GUIDE_PROP))
    except Exception:
        return False


def set_guide(doc, enabled):
    """Active/désactive le guidage visuel et l'applique à toutes les formules.

    L'état est mémorisé dans le document (propriété utilisateur
    ``MathsGuide``), donc conservé à l'enregistrement.
    """
    try:
        props = doc.getDocumentProperties().getUserDefinedProperties()
        try:
            props.setPropertyValue(GUIDE_PROP, bool(enabled))
        except Exception:  # propriété inexistante : on la crée
            props.addProperty(GUIDE_PROP, PROPERTY_REMOVABLE, bool(enabled))
        for obj in iter_math_objects(doc):
            _apply_guide(obj, bool(enabled))
    except Exception:
        log_exception("set_guide")


# --------------------------------------------------------------------------
# Alignement des "="
# --------------------------------------------------------------------------
def estimate_left_width(portions, char_width):
    """Largeur estimée (1/100 mm) de ce qui précède le 1er "=" d'un paragraphe.

    ``portions`` : liste de tuples ``("text", chaine)`` ou
    ``("formula", code_starmath, largeur_objet)``. Retourne ``None`` s'il n'y
    a aucun "=" (logique pure, testable).

    Pour une formule on suppose la largeur proportionnelle au nombre de
    caractères du code StarMath : approximation, d'où un alignement "à peu
    près" pour les objets (exact pour le texte brut, voir ``align_equals``).
    """
    total = 0.0
    for p in portions:
        if p[0] == "text":
            idx = p[1].find("=")
            if idx >= 0:
                return total + idx * char_width
            total += len(p[1]) * char_width
        else:
            code, width = p[1], p[2]
            idx = code.find("=")
            if idx >= 0:
                return total + width * (float(idx) / max(len(code), 1))
            total += width
    return None


def _paragraphs(doc):
    """Paragraphes de la sélection (ou du paragraphe courant si rien n'est sélectionné)."""
    controller = doc.getCurrentController()
    sel = controller.getSelection()
    ranges = []
    try:
        if sel.supportsService("com.sun.star.text.TextRanges"):
            ranges = [sel.getByIndex(i) for i in range(sel.getCount())]
    except Exception:
        pass
    if not ranges:
        ranges = [controller.getViewCursor()]
    for rng in ranges:
        enum = rng.getText().createTextCursorByRange(rng).createEnumeration()
        while enum.hasMoreElements():
            para = enum.nextElement()
            if para.supportsService("com.sun.star.text.Paragraph"):
                yield para


def _portions(para):
    """Décompose un paragraphe en portions texte / formule (voir estimate_left_width)."""
    out = []
    enum = para.createEnumeration()
    while enum.hasMoreElements():
        por = enum.nextElement()
        kind = por.TextPortionType
        if kind == "Text":
            out.append(("text", por.getString()))
        elif kind == "TextContent":
            content = por.TextContent
            if content is not None and _is_math_object(content):
                out.append(("formula", content.EmbeddedObject.Formula, content.Width))
    return out


def align_equals(doc):
    """Aligne verticalement les "=" des paragraphes sélectionnés.

    Solution retenue (la plus robuste sans toucher au contenu des formules) :
    * paragraphe de texte brut : une tabulation initiale est insérée et un
      taquet *décimal* dont le caractère décimal est "=" est posé à la
      position P. Writer aligne alors exactement les "=" sur P.
    * paragraphe contenant une formule avec "=" : un taquet ne peut pas
      pointer à l'intérieur d'un objet ; on décale donc le paragraphe
      (retrait gauche) de P - largeur estimée de la partie avant "=".
      L'alignement est alors approximatif (l'estimation est proportionnelle
      au code StarMath). Le contenu des formules n'est jamais modifié.
    P est la plus grande largeur estimée avant un "=". Tout est dans un seul
    bloc d'annulation (Ctrl+Z annule d'un coup).
    """
    try:
        paras = list(_paragraphs(doc))
        infos = []
        for para in paras:
            portions = _portions(para)
            cw = float(para.CharHeight) * 0.5 * HUNDREDTH_MM_PER_PT  # largeur moyenne d'un caractère
            left = estimate_left_width(portions, cw)
            if left is not None:
                infos.append((para, left, any(p[0] == "formula" for p in portions)))
        if not infos:
            return
        pos = int(max(left for _p, left, _f in infos)) + 300  # marge de 3 mm
        undo = doc.getUndoManager()
        undo.enterUndoContext("Aligner les =")
        try:
            for para, left, has_formula in infos:
                if has_formula:
                    para.ParaLeftMargin = max(pos - int(left), 0)
                else:
                    _set_decimal_tab(para, pos)
        finally:
            undo.leaveUndoContext()
    except Exception:
        log_exception("align_equals")


def _set_decimal_tab(para, pos):
    """Pose un taquet décimal sur "=" à ``pos`` et une tabulation en début de ligne."""
    tab = uno.createUnoStruct("com.sun.star.style.TabStop")
    tab.Position = pos
    tab.Alignment = uno.Enum("com.sun.star.style.TabAlign", "DECIMAL")
    tab.DecimalChar = "="
    tab.FillChar = " "
    para.ParaLeftMargin = 0
    para.ParaTabStops = (tab,)
    if not para.getString().startswith("\t"):
        para.getText().insertString(para.getStart(), "\t", False)
