# plugin-maths

Extension LibreOffice Writer pour écrire les maths facilement sur ordinateur : panneau latéral avec boutons, raccourcis clavier tapés au vol, guidage visuel des formules et alignement des « = ».

## Pourquoi ce projet

Conçu pour aider les élèves qui travaillent sur PC à retrouver l'aisance du papier. Il remplace la saisie StarMath de LibreOffice (code à taper, fenêtre séparée) par une interface simple et sans surcharge : on écrit les maths directement dans le texte, comme sur une feuille.

- **Panneau latéral** : gros boutons, trois blocs repliables (Nombres & Opérations, Gabarits, Géométrie / Trigonométrie), infobulle sur chaque bouton avec l'action et son raccourci.
- **Insertion au curseur** : fractions, racines, puissances, vecteurs… insérés comme objets Math dans le texte, sans fenêtre modale. Le gabarit est inséré vide et le curseur se place dans le premier champ.
- **Guidage visuel** : un bouton colore légèrement le fond des formules pour guider le regard.
- **Alignement des « = »** : un bouton aligne les signes « = » des lignes sélectionnées (résolution d'équations).

## Prérequis

- Windows 11 (fonctionne aussi sous Linux/macOS), LibreOffice **7.4 ou plus récent** avec Writer.
- Aucun autre logiciel à installer pour l'élève.

## Installation (élève)

1. Télécharger `plugin-maths.oxt` depuis la page [Releases](https://github.com/aifedespaix/plugin-maths/releases/latest) (section « Assets »).
2. Fermer LibreOffice, puis double-cliquer sur le fichier `.oxt` (ou, dans LibreOffice : Outils > Gestionnaire d'extensions > Ajouter…). Accepter la licence et choisir « Pour moi seulement ».
3. Redémarrer LibreOffice et ouvrir un document Writer.
4. Ouvrir la barre latérale (Affichage > Barre latérale, ou Ctrl+F5) et cliquer sur l'icône « Maths ».

### Installation silencieuse (Windows)

```powershell
./scripts/install.ps1                      # dernière release GitHub (ou dist/plugin-maths.oxt s'il existe)
./scripts/install.ps1 -Oxt C:\chemin\plugin-maths.oxt
./scripts/install.ps1 -UserOnly            # sans droits administrateur
./scripts/install.ps1 -CloseLibreOffice    # ferme LibreOffice avant d'installer
./scripts/uninstall.ps1                    # désinstalle (fr.aifedespaix.plugin-maths)
```

Le script repère `unopkg` dans `Program Files\LibreOffice\program`, refuse de continuer si LibreOffice est ouvert, installe pour tous les utilisateurs (`unopkg add --shared -f`, auto-élévation administrateur) et se replie sur l'utilisateur courant (`unopkg add -f`) en cas d'échec.

Pour désinstaller : Outils > Gestionnaire d'extensions > « Maths facile pour Writer » > Supprimer.

Les mises à jour sont proposées automatiquement par LibreOffice (voir plus bas).

## Configuration

Trois profils (dossier `extension/presets/`) : **Simple** (essentiels), **Standard**, **Complet** (tout). Le bouton « ⚙ Réglages » du panneau ouvre une fenêtre non modale avec les onglets Profil, Gabarits (activer/désactiver chaque bouton), Raccourcis (changer la séquence tapée, conflits signalés), Affichage (thème clair/doux/contraste, échelle 80 % à 160 %, hauteur des boutons, couleur du guidage).

Les réglages sont enregistrés dans `plugin-maths.json` du profil utilisateur LibreOffice (repli : `%APPDATA%\plugin-maths\config.json`, ou `~/.config`). Ordre de résolution : profil < réglages personnels. Un fichier absent ou corrompu est ignoré (valeurs par défaut). Le panneau se met à jour dès l'enregistrement.

```json
{"preset": "standard", "overrides": {"enabled": {"matrix": true},
  "shortcuts": {"fraction": {"type": "seq", "value": "//"}},
  "ui": {"scale": 1.0, "theme": "doux", "button_height": 44, "guide_color": "#FFF3C4"}}, "guide": false}
```

## Raccourcis

| Tapé | Résultat | Tapé | Résultat |
|---|---|---|---|
| `//` | fraction | `+-` | ± |
| `sqrt` | racine | `<=` | ≤ |
| `^^` | puissance | `>=` | ≥ |
| `__` | indice | `!=` | ≠ |
| `vec` | vecteur | `~=` | ≈ |

`sqrt` et `vec` ne se déclenchent qu'après un caractère qui n'est pas une lettre (« avec » reste « avec »).

- Ctrl+Alt+G : guidage visuel des formules
- Ctrl+Alt+E : aligner les « = » des paragraphes sélectionnés

- Ctrl+Alt+Entrée : étape d'équation (nouvelle ligne alignée sur le « = » précédent)

Les séquences ci-dessus sont les valeurs par défaut et se changent dans les réglages. Les autres actions se font par clic dans le panneau, qui propose un bouton pour chaque action.

Dans une formule : Tab / Maj+Tab = champ suivant / précédent, Échap ou Ctrl+Entrée = sortir de la formule et continuer le texte. Chaque insertion s'annule en un seul Ctrl+Z.

## Modèles de documents

Squelettes aérés insérés au curseur, sans fenêtre : résoudre une équation, problème (données / inconnue / calcul / conclusion), géométrie (énoncé / figure / propriété / démonstration / conclusion), tableau de valeurs d'une fonction, calcul littéral, propriété (propriété / exemple / à retenir).

## Vérifier une équation

Sélectionner une équation (« 2x+1 = 7 »), saisir la variable et sa valeur dans la section « Vérifier » du panneau, puis cliquer : le résultat s'affiche (✓ juste / ✗ faux). Le calcul est fait par un évaluateur sûr (jamais d'`eval`), avec multiplication implicite, fractions et décimaux à virgule.

## Développement

Sources dans `extension/` (Python/UNO, modules plats, point d'entrée `main.py`). Pour tester : construire l'oxt puis l'installer dans LibreOffice.

## Build

```powershell
./build.ps1                    # produit dist/plugin-maths.oxt
./build.ps1 -Version 0.2.0     # estampille la version (copie de staging, sources intactes)
```

Fonctionne avec PowerShell 5.1 et 7 (Windows, Linux, macOS via `pwsh`). Les entrées du zip utilisent des `/`, indispensable pour un oxt valide.

## Publier une release

Automatique : chaque push sur `main` (si les tests passent) publie une release GitHub avec `plugin-maths.oxt`.

- Version : celle de `extension/description.xml` si son tag n'existe pas encore (pour un saut mineur/majeur, changez-la à la main) ; sinon dernier tag `vX.Y.Z` avec le patch + 1.
- Le workflow `release.yml` met ensuite à jour `update.xml` et `description.xml` sur `main` (commit `[skip ci]`, sans relancer de release).
- Tests : `python3 -m unittest discover -s tests -v` (logique pure, sans LibreOffice).

## Mise à jour automatique

`description.xml` pointe vers `update.xml` (sur `main`, via raw.githubusercontent.com). LibreOffice le consulte et propose la nouvelle version dès qu'une release est publiée (l'utilisateur confirme ; ce n'est pas silencieux).

Les notes de la release GitHub sont extraites de la section de la version dans `CHANGELOG.md` (à mettre à jour avant de poser le tag) ; `update.xml` reçoit aussi le lien vers cette page (`<release-notes>`), affiché par LibreOffice lors d'une mise à jour.

La CI (`ci.yml`) valide les XML, compile le Python, construit l'oxt et le publie comme artefact.

## Licence

MIT
