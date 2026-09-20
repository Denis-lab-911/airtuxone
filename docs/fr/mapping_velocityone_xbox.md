# Guide de Mapping : VelocityOne Flightstick vers Manette Xbox (MSFS)

Ce document récapitule le mapping pour transformer votre Turtle Beach VelocityOne Flightstick en manette Xbox virtuelle pour Microsoft Flight Simulator (MSFS) via GeForce NOW.

Il décrit le profil triple, [`config.triple.toml`](../../config.triple.toml). Le manche et les boutons sont exposés par la manette virtuelle 1, tandis que les deux leviers de gaz sont dirigés vers les manettes virtuelles 2 et 3 ; voir le tableau des profils dans le [README](../../README.fr.md).

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

### Axes des manettes de gaz

| Élément physique (VelocityOne) | Code evdev source | Manette virtuelle | Cible Xbox | Fonction MSFS recommandée |
| :--- | :--- | :--- | :--- | :--- |
| Levier gaz 1 | `ABS_RZ` | **Manette 2** — AirTuxOne - Throttle 1 | `ABS_Y` (stick gauche vertical, inversé) | **Poussée 1** |
| Levier gaz 2 | `ABS_THROTTLE` | **Manette 3** — AirTuxOne - Throttle 2 | `ABS_RY` (stick droit vertical, inversé) | **Poussée 2** |
| Molette trim | `ABS_RUDDER` | Aucune | Non mappée | À configurer séparément |

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
2. **B5–B8** : appui → **LB + A/B/X/Y** (combo maintenu pendant l'appui).
3. **B16** : appui → **LB** seul (usage dédié, distinct des combos B5–B8).
4. **Stick droit (RS)** : entièrement réservé au mini-stick H2 (`ABS_RX` + `ABS_RY`).

## Notes importantes de configuration

1. **H2 → stick droit :** mini-stick tête = regard horizontal + vertical dans MSFS (RS X / RS Y).
2. **Gaz :** dans le profil triple, `ABS_RZ` est envoyé vers le stick gauche vertical de la manette 2 et `ABS_THROTTLE` vers le stick droit vertical de la manette 3. Les deux axes sont inversés (`invert = true`) et utilisent le mode `linear`.
3. **Torsion / palonnier :** mode `split_triggers` (LT/RT analogiques uniquement). Ajustez `deadzone` si le palonnier dérive.
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
| B16 | LB |
| Bouton Xbox | Guide |
| Back | Select (bas gauche) |
| Start | Start (bas droit) |

## Implémentation AirTuxOne

Ce mapping est appliqué dans [`config.triple.toml`](../../config.triple.toml), avec trois périphériques virtuels :

| Section TOML | Périphérique virtuel | Mapping |
| :--- | :--- | :--- |
| `[virtual_controller_1]` | **AirTuxOne** | Manche, H1/H2 et boutons |
| `[virtual_controller_2]` | **AirTuxOne - Throttle 1** | `ABS_RZ` → `ABS_Y` (inversé) |
| `[virtual_controller_3]` | **AirTuxOne - Throttle 2** | `ABS_THROTTLE` → `ABS_RY` (inversé) |

Le mapping détaillé du manche ci-dessus concerne la section `[virtual_controller_1]`.

| Mode TOML | Usage |
| :--- | :--- |
| `centered` | Manche, mini-stick H2 |
| `split_triggers` | Torsion → LT/RT |
| `modifier_hold` | B5–B8 → LB + bouton face maintenu |
| `passthrough` | POV H1 / D-Pad |
| `linear` | Plage source complète vers un axe de stick Xbox bipolaire ; utilisé pour les deux leviers de gaz |
| `linear_positive` | Plage source complète vers un axe de stick positif |
| `linear_trigger` | Plage source complète vers une gâchette 0–255 |
| `centered_trigger` | Axe source centré vers une gâchette 0–255, neutre à 128 |
| `trim_impulse` | Mouvement d'axe émettant une impulsion D-Pad, avec modificateur optionnel |
| `trim_pulse` | Appui bouton émettant une impulsion modificateur + D-Pad configurée |
| `dpad_hold` | Maintien bouton émettant une direction D-Pad, avec modificateur optionnel |

### Paramètres TOML

Les entrées d'axe acceptent `target`, `mode`, `invert` et `deadzone`. `linear`, `linear_positive` et `linear_trigger` peuvent utiliser `input_min`/`input_max` (ou `range_min`/`range_max`) pour calibrer la plage source. `split_triggers` nécessite `target_left` et `target_right` au lieu de `target`.

Les entrées bouton contiennent normalement une chaîne de code cible. `modifier_hold` nécessite `modifier_button` et `target_button` ; `trim_pulse` et `dpad_hold` acceptent `modifier_button`, `hat` et `hat_value`. `trim_impulse` accepte `modifier_button` (optionnel), ainsi que `hat`, `hat_up`, `hat_down` et `threshold`.
