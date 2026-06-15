# Guide de Mapping : VelocityOne Flightstick vers Manette Xbox (MSFS)

Ce document récapitule le mapping optimal pour transformer votre Turtle Beach VelocityOne Flightstick en manette Xbox virtuelle spécialement configurée pour Microsoft Flight Simulator (MSFS).

## Tableau de Synthèse du Mapping

| Élément physique (VelocityOne) | Code evdev source | Touche émulée (Xbox) | Fonction MSFS recommandée | Type de contrôle |
| :--- | :--- | :--- | :--- | :--- |
| **Inclinaison Stick (Axe X)** | `ABS_X` | Stick Gauche - Horizontal | **Ailerons** (Roulis) | Analogique |
| **Inclinaison Stick (Axe Y)** | `ABS_Y` | Stick Gauche - Vertical | **Profondeur** (Tangage) | Analogique |
| **Torsion du Stick (Axe Z)** | `ABS_Z` | Gâchettes LT / RT *(Axe combiné)* | **Palonnier** (Direction / Taxis) | Analogique |
| **Manette des gaz (Levier gauche)** | `ABS_RZ` | Stick Droit - Vertical | **Poussée** (Gaz) | Analogique |
| **Mini-stick (Tête du joystick)** | `ABS_RX` | Stick Droit - Horizontal | **Regard Horizontal** (Vue libre) | Analogique |
| **Chapeau chinois (POV - H1)** | `ABS_HAT0X/Y` | Croix directionnelle (D-Pad) | **Regard vertical / Menus** | Numérique |
| **Molette de Trim** | `BTN_TOP2` / `BTN_PINKIE` (B5/B6) | RB + D-Pad Haut/Bas *(maintenu)* | **Trim pitch** | Numérique |
| **Bouton A** | `BTN_TRIGGER` | Bouton A | **Freins de roues** | Numérique |
| **Bouton B** | `BTN_THUMB` | Bouton B | *(libre)* | Numérique |
| **Bouton X** | `BTN_THUMB2` | Bouton X | **Train d'atterrissage** | Numérique |
| **Bouton Y** | `BTN_TOP` | Bouton Y | **Changer de vue** | Numérique |
| **Clic du Mini-stick** | `BTN_TOP2` | Bouton RS (Right Stick Click) | **Réinitialiser la vue** | Numérique |
| **Bouton B1 (Base gauche)** | `BTN_BASE` | Bouton LB | **Rentrer les volets** | Numérique |
| **Bouton B2 (Base gauche)** | `BTN_BASE2` | Bouton RB | **Sortir les volets** | Numérique |

## Notes importantes de configuration

1. **Gestion des axes combinés (Z-Axis / Torsion) :** AirTux One applique le mode `split_triggers` (LT/RT, neutre = relâché). Ajustez `deadzone` dans `config.toml` si le palonnier dérive.
2. **Trim pitch :** Maintenez **B5** (`BTN_TOP2`) ou **B6** (`BTN_PINKIE`) — le démon envoie **RB + D-Pad** tant que le bouton est enfoncé. Inverser `hat_value` dans `config.toml` si le sens est mauvais.
3. **Courbes de sensibilité :** Dans MSFS, réduisez la réactivité (courbes de sensibilité) entre **-20% et -35%** pour les axes de roulis et de tangage afin de compenser la course longue du joystick par rapport aux petits sticks d'une manette classique.

## Implémentation AirTux One

Ce mapping est appliqué dans `config.toml` (contrôleur virtuel 2, onglet 3 dans gamepad-tester).

| Mode TOML | Usage |
| :--- | :--- |
| `centered` | Manche, mini-stick |
| `split_triggers` | Torsion → LT/RT |
| `linear_positive` | Levier de gaz |
| `dpad_hold` | Trim B5/B6 → RB + D-Pad maintenu |
| `passthrough` | POV / D-Pad |
