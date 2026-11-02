# plugin-maths

Extension LibreOffice Writer pour écrire les maths facilement (niveau 3e) : panneau latéral avec boutons, raccourcis clavier tapés au vol, guidage visuel des formules et alignement des « = ».

Nécessite LibreOffice 7.4 ou plus récent.

## Installation (élève)

1. Télécharger `plugin-maths.oxt` depuis la page [Releases](https://github.com/aifedespaix/plugin-maths/releases/latest).
2. Double-cliquer sur le fichier (ou Outils > Gestionnaire d'extensions > Ajouter), accepter, puis redémarrer LibreOffice.
3. Ouvrir un document Writer : le panneau « Maths » est dans la barre latérale (Affichage > Barre latérale).

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
