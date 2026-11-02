#!/bin/bash
# Test de bout en bout SANS ecran: build .oxt -> install dans un profil jetable ->
# ouvre Writer -> ouvre la sidebar + deck Maths -> capture d'ecran + journal stderr.
# Usage: e2e_sidebar.sh [workdir]   (defaut: /tmp/maths-e2e). Sortie: $W/shot.png, $W/lo.log
# Lancer depuis la racine du depot. Necessite: soffice, unopkg, xvfb-run, zip, ImageMagick (import).
set -u
W="${1:-/tmp/maths-e2e}"; ROOT="$(pwd)"
mkdir -p "$W"; rm -f "$W/p.oxt" "$W/lo.log" "$W/shot.png"
(cd "$ROOT/extension" && zip -qr "$W/p.oxt" . -x '*__pycache__*')
P="-env:UserInstallation=file://$W/prof"
# root => --shared obligatoire; le cache partage survit: TOUJOURS remove avant add.
unopkg remove --shared $P fr.aifedespaix.plugin-maths >/dev/null 2>&1
echo yes | unopkg add --shared $P "$W/p.oxt" >/dev/null 2>&1   # "yes" = licence lue sur stdin
cat > "$W/drive.py" <<PY
import os, time, uno
from com.sun.star.beans import PropertyValue
l = uno.getComponentContext()
r = l.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", l)
for i in range(60):
    try: ctx = r.resolve("uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext"); break
    except Exception: time.sleep(1)
sm = ctx.ServiceManager
d = sm.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
doc = d.loadComponentFromURL("private:factory/swriter", "_blank", 0, ())
time.sleep(3)
h = sm.createInstanceWithContext("com.sun.star.frame.DispatchHelper", ctx)
fr = doc.getCurrentController().getFrame()
for c in (".uno:Sidebar", ".uno:SidebarDeck.MathsDeck"):
    h.executeDispatch(fr, c, "", 0, ()); time.sleep(4)
os.system("import -display \$DISPLAY -window root $W/shot.png")
PY
cat > "$W/run.sh" <<SH
#!/bin/bash
soffice $P --norestore --nologo --accept='socket,host=localhost,port=2002;urp;' > "$W/lo.log" 2>&1 &
python3 "$W/drive.py"; sleep 2
# pkill -x (nom exact): "pkill/pgrep -f soffice.bin" matche sa propre ligne de commande et tue le shell (exit 144).
pkill -x soffice.bin; pkill -x oosplash; exit 0
SH
chmod +x "$W/run.sh"
timeout 150 xvfb-run -a -s "-screen 0 1280x1024x24" "$W/run.sh" >/dev/null 2>&1
echo "== erreurs plugin (vide = OK) =="; grep -A8 "plugin-maths" "$W/lo.log" | head -40
echo "== capture: $W/shot.png (a regarder avec Read) =="
