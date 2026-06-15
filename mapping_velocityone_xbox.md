# Guide de Mapping : VelocityOne Flightstick vers Manette Xbox (MSFS)

Ce document récapitule le mapping pour transformer votre Turtle Beach VelocityOne Flightstick en manette Xbox virtuelle pour Microsoft Flight Simulator (MSFS) via GeForce NOW.

## Tableau de Synthèse du Mapping

### Axes

| Élément physique (VelocityOne) | Code evdev source | Touche émulée (Xbox) | Fonction MSFS recommandée | Type |
| :--- | :--- | :--- | :--- | :--- |
| **Inclinaison Stick (Axe X)** | `ABS_X` | Stick Gauche - Horizontal | **Ailerons** (Roulis) | Analogique |
| **Inclinaison Stick (Axe Y)** | `ABS_Y` | Stick Gauche - Vertical | **Profondeur** (Tangage) | Analogique |
| **Torsion du Stick (Axe Z)** | `ABS_Z` | Gâchettes LT / RT | **Palonnier** (Direction / Taxis) | Analogique |
| **Manette des gaz (Levier gauche)** | `ABS_RZ` | Stick Droit - Vertical | **Poussée** (Gaz) | Analogique |
| **Mini-stick (Tête du joystick)** | `ABS_RX` | Stick Droit - Horizontal | **Regard Horizontal** | Analogique |
| **Chapeau chinois (POV - H1)** | `ABS_HAT0X/Y` | Croix directionnelle (D-Pad) | **Regard vertical / Menus** | Numérique |

### Axes non mappés (volontaire)

| Élément | Code evdev | Raison |
| :--- | :--- | :--- |
| Mini-stick H2 vertical | `ABS_RY` | Conflit avec le gaz sur RS Y — regard vertical via POV |
| Levier gaz droit | `ABS_THROTTLE` | MSFS gamepad n'expose qu'un axe gaz |
| Molette trim | `ABS_RUDDER` | Trim pitch via boutons B5/B6 |

### Boutons

| Élément physique (VelocityOne) | Code evdev source | Touche émulée (Xbox) | Fonction MSFS recommandée | Type |
| :--- | :--- | :--- | :--- | :--- |
| **Bouton A** | `BTN_TRIGGER` | Bouton A | **Freins de roues** | Numérique |
| **Gâchette** | `BTN_TRIGGER_HAPPY2` | Bouton A | **Freins de roues** | Numérique |
| **Bouton B** | `BTN_THUMB` | Bouton B | *(libre)* | Numérique |
| **Bouton X** | `BTN_THUMB2` | Bouton X | **Train d'atterrissage** | Numérique |
| **Bouton Y** | `BTN_TOP` | Bouton Y | **Changer de vue** | Numérique |
| **Trim pitch haut (B5)** | `BTN_TOP2` | RB + D-Pad Haut *(maintenu)* | **Trim pitch** nose up | Numérique |
| **Trim pitch bas (B6)** | `BTN_PINKIE` | RB + D-Pad Bas *(maintenu)* | **Trim pitch** nose down | Numérique |
| **B7 (Base manche)** | `BTN_BASE` | Bouton LB | **Rentrer les volets** | Numérique |
| **B8 (Base manche)** | `BTN_BASE2` | Bouton B | **Sortir les volets** | Numérique |
| **Bas gauche** | `BTN_TRIGGER_HAPPY5` | LS Click | **Réinitialiser la vue** | Numérique |
| **Bas milieu** | `BTN_TRIGGER_HAPPY6` | Start | **Menu pause** | Numérique |
| **Bas droit** | `BTN_TRIGGER_HAPPY7` | RS Click | *(libre)* | Numérique |
| **Bouton Xbox** | `BTN_TRIGGER_HAPPY4` | Guide (Mode) | Caméra / guide | Numérique |
| **B16** | `BTN_DEAD` | Select | Menu / sélection | Numérique |

## Règles anti-conflit

1. **RB** n'est utilisé que comme modificateur du trim (B5/B6) — jamais en appui direct. Les volets sortants passent par **B** (B8 partage la touche avec le bouton B face).
2. **RS Y** est réservé au gaz — le mini-stick vertical (`ABS_RY`) n'est pas mappé.
3. **D-Pad** : POV libre ; pendant le trim (B5/B6), le démon impose D-Pad Haut/Bas tant que le bouton est maintenu.

## Notes importantes de configuration

1. **Torsion / palonnier :** mode `split_triggers` (LT/RT, neutre = relâché). Ajustez `deadzone` dans `config.toml` si le palonnier dérive.
2. **Trim pitch :** maintenez **B5** ou **B6** — le démon envoie **RB + D-Pad** tant que le bouton est enfoncé. Inverser `hat_value` dans `config.toml` si le sens est mauvais.
3. **Volets :** dans MSFS, assignez **Diminuer volets** à **LB** et **Augmenter volets** à **B**.
4. **Courbes de sensibilité :** réduisez la réactivité entre **-20 % et -35 %** sur roulis et tangage.

## Bindings MSFS (GeForce NOW)

| Action | Touche Xbox |
| :--- | :--- |
| Ailerons / profondeur | LS |
| Palonnier | LT / RT |
| Gaz | RS Y |
| Regard horizontal | RS X |
| Regard vertical / menus | D-Pad |
| Trim pitch ↑ / ↓ | RB + D-Pad Haut / Bas |
| Freins roues | A |
| Train | X |
| Changer vue | Y |
| Volets − | LB |
| Volets + | B |

## Implémentation AirTux One

Ce mapping est appliqué dans [`config.toml`](config.toml), section `[virtual_controller_2]` (manette virtuelle **AirTux One**).

| Mode TOML | Usage |
| :--- | :--- |
| `centered` | Manche, mini-stick |
| `split_triggers` | Torsion → LT/RT |
| `linear_positive` | Levier de gaz |
| `dpad_hold` | Trim B5/B6 → RB + D-Pad maintenu |
| `passthrough` | POV / D-Pad |
