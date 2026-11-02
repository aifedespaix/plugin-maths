# Changelog

Toutes les évolutions notables de ce projet sont consignées ici.
Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versions selon [SemVer](https://semver.org/lang/fr/).

## [0.2.0] - 2026-11-02

### Ajouté
- Profils prêts à l'emploi (Simple, Standard, Complet) et écran de réglages non modal : choix des gabarits actifs, raccourcis, thème, taille des boutons, couleur du guidage. Configuration enregistrée dans le profil LibreOffice, le panneau se met à jour seul.
- Raccourcis tapés configurables, avec détection des conflits (doublons, préfixes).
- Nouveaux gabarits : système d'équations, intégrale, somme, limite, matrice 2x2, notation scientifique, intervalle.
- Ensembles et fonctions : ∈, ∪, ∩, ℝ, ℕ, ℤ.
- Modèles de documents : résoudre une équation, problème, géométrie, tableau de valeurs d'une fonction, calcul littéral, propriété.
- Étape d'équation (Ctrl+Alt+Entrée) : nouvelle ligne alignée sur le « = » de la précédente, prête à continuer.
- Vérification d'une équation pour une valeur donnée (✓ juste / ✗ faux).
- Rangée « Récents » dans le panneau.
- Navigation au clavier dans les formules : Tab / Maj+Tab pour passer d'un champ à l'autre, Échap ou Ctrl+Entrée pour reprendre le texte.
- Chaque insertion s'annule en une seule étape (Ctrl+Z).
- Icône de l'extension et du panneau latéral (y compris contraste élevé).
- Scripts `scripts/install.ps1` et `scripts/uninstall.ps1` : installation et désinstallation silencieuses.
- Notes de mise à jour affichées par LibreOffice (lien vers la page de la release).

### Modifié
- Les notes de chaque release GitHub sont tirées de ce fichier.
- Correction du script de build et du workflow de release : l'URL de téléchargement de `update.xml` est bien réécrite à chaque version.

## [0.1.0]

### Ajouté
- Panneau latéral Maths pour Writer, raccourcis tapés (`//`, `sqrt`, `^^`, `__`, `vec`, `+-`, `<=`, `>=`, `!=`, `~=`).
- Guidage visuel des formules (Ctrl+Alt+G) et alignement des « = » (Ctrl+Alt+E).
- Mise à jour automatique via `update.xml`.
