---
name: libreoffice-sidebar-dev
description: Pieges et regles pour developper l'extension LibreOffice (.oxt, pyuno) de ce depot - panneau sidebar, ui_loader.py, Sidebar.xcu/Factories.xcu, installation et test sans ecran. A lire avant de toucher a sidebar.py, ui_loader.py, settings.py, aux .xcu ou au manifest.
---

# Developper le plugin Maths (LibreOffice sidebar, pyuno)

## Verite terrain d'abord
Un panneau qui "s'ouvre et se referme tout de suite" = **le panneau est vide/hauteur ~0**, presque
toujours parce que la creation des controles a leve une exception (avalee par les `try/except` du
code, visible uniquement sur stderr). Ne jamais deviner: **reproduire avec `scripts/e2e_sidebar.sh`**
(voir plus bas) et lire `lo.log` + la capture. Les tests unitaires (`python3 -m unittest discover -s tests`)
ne couvrent PAS l'UNO reel: ils ont passe pendant que le panneau etait casse.

## Regles UNO / pyuno verifiees (LO 24.2, bug reel corrige en 0.2.2)
- `UnoControlContainerModel` n'expose **ni `createInstance` ni `insertByName`** a pyuno
  (`AttributeError`). Utiliser **`UnoControlDialogModel`** comme modele du conteneur.
- Pour le **controle**, utiliser **`UnoControlContainer`** (embarque dans la fenetre parent de la sidebar).
  `UnoControlDialog` + `createPeer(toolkit, parent)` ouvre une **fenetre flottante en (0,0)**, pas dans la sidebar.
- Avec cette combinaison, `container.getControl(nom)` peut renvoyer `None` apres `insertByName`: creer alors
  le controle (`createInstanceWithContext(model.DefaultControl)`), `ctrl.setModel(m)`, `container.addControl(nom, ctrl)`.
- Sequence: `model = DialogModel` ; `ctrl = Container` ; `ctrl.setModel(model)` ; `ctrl.createPeer(toolkit, parent)` ;
  puis ajouter les sous-modeles via `model.createInstance(...)` + `model.insertByName(...)`.
- Les exceptions ne doivent pas remonter a LibreOffice (crash/refermeture silencieuse): on les journalise sur stderr
  avec le prefixe `[plugin-maths]`. Consequence: **toujours relire le log apres un changement d'UI**.
- `getHeightForWidth` doit renvoyer un `com.sun.star.ui.LayoutSize(Minimum, Maximum, Preferred)`; une hauteur
  nulle/minuscule donne un panneau invisible. La hauteur reelle appliquee peut differer (le layouter passe par XWindow).
- `XSidebarPanel` a **deux** methodes: `getHeightForWidth` ET **`getMinimalWidth`** (absente => crash de LO >= 5.1).
  Garder `getMinimalWidth()` raisonnable (la largeur max de sidebar devient `minimalWidth + 100px` si elle depasse le reglage).
- Le panneau doit implementer `XUIElement` (getFrame, getResourceURL, getType=7 pour toolpanel, getRealInterface),
  `XToolPanel` (getWindow, createAccessible) et `XSidebarPanel`; la fabrique implemente `XUIElementFactory`
  (`createUIElement(url, args)` lit `ParentWindow`, `Frame`, `Sidebar` dans les args) et `XServiceInfo`.
- La duree de vie du composant = celle du panneau: ne pas y garder d'etat durable (utiliser config.py / le document).
- Hors LibreOffice (tests), les imports `uno`/`unohelper` sont remplaces par des stubs a bases DISTINCTES
  (sinon "duplicate base class object").

## Configuration (fichiers .xcu + manifest)
- `META-INF/manifest.xml` doit declarer `main.py` (uno-component;type=Python) + chaque `.xcu`
  (`application/vnd.sun.star.configuration-data`). Seul `main.py` est un composant Python; les autres modules
  sont importes via `sys.path` (voir debut de main.py).
- `Sidebar.xcu` (`org.openoffice.Office.UI` / `Sidebar`): `Content/DeckList/<Deck>` (Title, Id, IconURL,
  HighContrastIconURL, TitleBarIconURL, ContextList, OrderIndex) et `Content/PanelList/<Panel>` (Title, Id, DeckId,
  ContextList, ImplementationURL, OrderIndex, WantsCanvas). `ContextList` = `application, contexte, visible ;`
  (ex. `com.sun.star.text.TextDocument, any, visible ;`, verifie fonctionnel sur Writer).
- `ImplementationURL` du panneau == l'URL que la fabrique accepte (`PANEL_URL` dans sidebar.py ==
  `private:resource/toolpanel/MathsPanelFactory/MathsPanel`); le nom du noeud de `Factories.xcu` en est le prefixe;
  `FactoryImplementation` == `IMPL_NAME` enregistre dans main.py. **Un seul caractere different = panneau jamais cree.**
- Icones: PNG 26x26 pour la deck (`%origin%/icons/...`), variante high-contrast fournie.
- Apres modif d'un .xcu: desinstaller/reinstaller l'extension (la config est mise en cache a l'install).

## Installer / tester sans ecran
`bash .claude/skills/libreoffice-sidebar-dev/scripts/e2e_sidebar.sh [dossier]` depuis la racine du depot:
construit l'oxt, l'installe dans un profil jetable, ouvre Writer + la deck, ecrit `shot.png` et `lo.log`.
Pieges rencontres:
- root => `unopkg add --shared` obligatoire; la licence est lue sur stdin (`echo yes |`).
- Le cache partage (`/var/spool/libreoffice/uno_packages`) survit: **`unopkg remove` avant chaque `add`**, sinon
  l'ancienne version tourne (on a perdu du temps a "tester" du vieux code).
- Ne jamais `pkill -f`/`pgrep -f soffice.bin`: ca matche la ligne de commande du shell appelant et le tue (exit 144). Utiliser `pkill -x soffice.bin`.
- `UNO_...` dispatch: `.uno:Sidebar` puis `.uno:SidebarDeck.<IdDeck>` (ici `MathsDeck`).
- En local sur LO reel: lancer `soffice` depuis un terminal pour voir stderr (`[plugin-maths] ...`).
- La capture se lit avec l'outil Read (image). Verifier visuellement: contenu present, **embarque** dans la sidebar,
  pas de fenetre flottante.

## Process release
Push sur `main` => release auto (CHANGELOG, `update.xml`, version dans description.xml). Ne pas modifier les
versions a la main (voir `.github/workflows/release.yml`). Build local: `build.ps1`.

## Limites de cette fiche
La doc officielle (wiki DocumentFoundation, api.libreoffice.org) etait partiellement inaccessible (anti-bot) ou
sans details sur `LayoutSize` (valeurs -1). Les regles "UNO / pyuno" ci-dessus sont **verifiees empiriquement sur
LO 24.2**; l'utilisateur est sur une 26.8: en cas de doute, reproduire sur sa version via le log stderr.
