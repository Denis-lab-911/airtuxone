# Guide de Mapping : VelocityOne Flightstick vers Manette Xbox (MSFS)

Ce document récapitule le mapping pour transformer votre Turtle Beach VelocityOne Flightstick en manette Xbox virtuelle pour Microsoft Flight Simulator (MSFS) via GeForce NOW.

## Tableau de Synthèse du Mapping

### Axes

| Élément physique (VelocityOne) | Code evdev source | Touche émulée (Xbox) | Fonction MSFS recommandée | Type |
| :--- | :--- | :--- | :--- | :--- |
| **Inclinaison Stick (Axe X)** | `ABS_X` | Stick Gauche - Horizontal | **Ailerons** (Roulis) | Analogique |
| **Inclinaison Stick (Axe Y)** | `ABS_Y` | Stick Gauche - Vertical | **Profondeur** (Tangage) | Analogique |
| **Torsion du Stick (Axe Z)** | `ABS_Z` | Gâchettes LT / RT | **Palonnier** (Direction / Taxis) | Analogique |
| **Mini-stick H2 horizontal** | `ABS_RX` | Stick Droit - Horizontal | **Regard horizontal** | Analogique |
| **Mini-stick H2 vertical** | `ABS_RY` | Stick Droit - Vertical | **Regard vertical** | Analogique |
| **Chapeau chinois (POV - H1)** | `ABS_HAT0X/Y` | Croix directionnelle (D-Pad) | **Menus / raccourcis** | Numérique |

### Axes non mappés (volontaire)

| Élément | Code evdev | Raison |
| :--- | :--- | :--- |
| Levier gaz gauche | `ABS_RZ` | Non mappé — poussée gérée autrement dans MSFS |
| Levier gaz droit | `ABS_THROTTLE` | Non mappé |
| Molette trim | `ABS_RUDDER` | Non mappé |

### Boutons face (A/B/X/Y)

Correspondance **1:1** entre les boutons du manche et la face Xbox :

| Joystick | Code evdev | Manette Xbox | MSFS suggéré |
| :--- | :--- | :--- | :--- |
| **A / B1** | `BTN_TRIGGER` | **A** | Freins de roues |
| **B / B2** | `BTN_THUMB` | **B** | *(libre)* |
| **X / B3** | `BTN_THUMB2` | **X** | Train d'atterrissage |
| **Y / B4** | `BTN_TOP` | **Y** | Changer de vue |

### Boutons B5–B8 (LB + face)

Correspondance **1:1** — le démon maintient **LB** + le bouton face tant que le bouton physique est enfoncé :

| Joystick | Code evdev | Manette Xbox | MSFS suggéré |
| :--- | :--- | :--- | :--- |
| **B5** | `BTN_TOP2` | **LB + A** | *(à assigner dans MSFS)* |
| **B6** | `BTN_PINKIE` | **LB + B** | *(à assigner dans MSFS)* |
| **B7** | `BTN_BASE` | **LB + X** | *(à assigner dans MSFS)* |
| **B8** | `BTN_BASE2` | **LB + Y** | *(à assigner dans MSFS)* |

### Autres boutons

| Joystick | Code evdev | Manette Xbox | MSFS suggéré |
| :--- | :--- | :--- | :--- |
| **Gâchette** | `BTN_TRIGGER_HAPPY2` | **RB** | *(à assigner dans MSFS)* |
| **Bouton Xbox** | `BTN_TRIGGER_HAPPY4` | **Guide (Mode)** | Bouton Xbox |
| **Bas gauche** | `BTN_TRIGGER_HAPPY5` | **Back** (Select) | Menu / retour |
| **Bas milieu** | `BTN_TRIGGER_HAPPY6` | LS Click | *(libre)* |
| **Bas droit** | `BTN_TRIGGER_HAPPY7` | **Start** | Menu pause |
| **B16** | `BTN_DEAD` | **LB** | *(à assigner dans MSFS)* |

## Règles anti-conflit

1. **B1–B4** : appui seul → A/B/X/Y (face Xbox).
2. **B5–B8** : appui → **LB + A/B/X/Y** (combo maintenu) — LB n'est jamais émis seul.
3. **Stick droit (RS)** : entièrement réservé au mini-stick H2 (`ABS_RX` + `ABS_RY`).

## Notes importantes de configuration

1. **H2 → stick droit :** mini-stick tête = regard horizontal + vertical dans MSFS (RS X / RS Y).
2. **Gaz :** leviers `ABS_RZ` / `ABS_THROTTLE` non mappés — configurez la poussée via clavier/souris ou profil MSFS sans axe gaz manette.
3. **Torsion / palonnier :** mode `split_triggers` (LT/RT). Ajustez `deadzone` si le palonnier dérive.
4. **Courbes de sensibilité :** réduisez la réactivité entre **-20 % et -35 %** sur roulis et tangage.

## Bindings MSFS (GeForce NOW)

| Action | Touche Xbox |
| :--- | :--- |
| Ailerons / profondeur | LS |
| Palonnier | LT / RT |
| Regard horizontal | RS X |
| Regard vertical | RS Y |
| Menus / raccourcis | D-Pad (H1) |
| Freins roues | A |
| Train | X |
| Changer vue | Y |
| B5 / B6 / B7 / B8 | LB+A / LB+B / LB+X / LB+Y |
| Bouton Xbox | Guide |
| Back | Select (bas gauche) |
| Start | Start (bas droit) |

## Implémentation AirTux One

Ce mapping est appliqué dans [`config.toml`](config.toml), section `[virtual_controller_2]` (manette virtuelle **AirTux One**).

| Mode TOML | Usage |
| :--- | :--- |
| `centered` | Manche, mini-stick H2 |
| `split_triggers` | Torsion → LT/RT |
| `modifier_hold` | B5–B8 → LB + bouton face maintenu |
| `passthrough` | POV H1 / D-Pad |
