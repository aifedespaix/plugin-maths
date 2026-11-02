# plugin-maths

Extension LibreOffice Writer pour écrire les maths facilement (niveau 3e) : panneau latéral avec boutons, raccourcis clavier tapés au vol, guidage visuel des formules et alignement des « = ».

## Pourquoi ce projet

Conçu sur mesure pour un élève de 3ᵉ avec un Trouble du Spectre de l'Autisme (TSA). Il remplace la saisie StarMath de LibreOffice (code à taper, fenêtre séparée) par une interface sans surcharge cognitive : on écrit les maths directement dans le texte, comme sur papier.

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

Pour désinstaller : Outils > Gestionnaire d'extensions > « Maths facile pour Writer » > Supprimer.

Les mises à jour sont proposées automatiquement par LibreOffice (voir plus bas).

Les mises à jour sont proposées automatiquement par LibreOffice (voir plus bas).

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

Les autres actions (angle, triangle, sin, cos...) se font par clic dans le panneau.

## Développement

Sources dans `extension/` (Python/UNO, modules plats, point d'entrée `main.py`). Pour tester : construire l'oxt puis l'installer dans LibreOffice.

## Build

```powershell
./build.ps1                    # produit dist/plugin-maths.oxt
./build.ps1 -Version 0.2.0     # estampille la version (copie de staging, sources intactes)
```

Fonctionne avec PowerShell 5.1 et 7 (Windows, Linux, macOS via `pwsh`). Les entrées du zip utilisent des `/`, indispensable pour un oxt valide.

## Publier une release

```bash
git tag v0.2.0 && git push --tags
```

Le workflow `release.yml` construit l'oxt avec la version du tag, crée la release GitHub avec `plugin-maths.oxt`, puis met à jour `update.xml` (version et URL) sur `main`.

## Mise à jour automatique

`description.xml` pointe vers `update.xml` (sur `main`, via raw.githubusercontent.com). LibreOffice le consulte, et propose la nouvelle version dès qu'une release est publiée.

La CI (`ci.yml`) valide les XML, compile le Python, construit l'oxt et le publie comme artefact.

## Licence

MIT
