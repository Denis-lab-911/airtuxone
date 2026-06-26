# Log de l'agent — AirTux One

## [Objectif Général]

Développer un démon Linux (AirTux One) qui intercepte les entrées d'un TurtleBeach VelocityOne Flightstick via `evdev` et les traduit vers une **manette Xbox 360 virtuelle** via `uinput`. Objectif : permettre à Google Chrome et GeForce NOW de piloter Microsoft Flight Simulator avec le manche, les gaz et les boutons du stick.

## [Architecture Validée]

```
airtuxone/
├── agent.md
├── config.toml           # Mapping TOML (section virtual_controller_2)
├── docs/
│   ├── en/mapping_velocityone_xbox.md
│   └── fr/mapping_velocityone_xbox.md
├── requirements.txt
├── setup.sh
├── README.md
└── airtux_one/
    ├── __init__.py
    ├── core.py           # Démon, boucle evdev, signaux, trim dpad_hold
    ├── devices.py        # Détection source, uinput Xbox 360
    ├── discover.py       # Assistant découverte axes/boutons
    ├── learn.py          # Assistant mapping joystick ↔ manette
    └── mapper.py         # Chargement TOML, lookup O(1), transformations
```

- Mapping 100 % externe via `config.toml` (aucun code en dur).
- Lookup O(1) : dictionnaires inversés au démarrage dans `mapper.py`.
- Permissions Linux : groupes `input` et `uinput`, module noyau `uinput`.
- Mapping MSFS : voir `docs/fr/mapping_velocityone_xbox.md`.

## [Tâches Réalisées]

- [x] Scaffolding, `setup.sh`, modules Python (`core`, `devices`, `mapper`)
- [x] `discover.py` — assistant de découverte des entrées
- [x] Mapping MSFS VelocityOne → Xbox (`config.toml`, modes `split_triggers`, `dpad_hold`, `linear_positive`)
- [x] Trim pitch via B5/B6 (`BTN_TOP2`, `BTN_PINKIE`) → RB + D-Pad maintenu
- [x] Contournement Chrome : masquage js0 physique (udev), sélection manette **AirTux One** dans le navigateur
- [x] Documentation : `README.md`, `README.fr.md`, `docs/en/`, `docs/fr/`

## [Tâches Restantes]

- [x] Résolution conflits mapping : RB réservé trim, volets B8→B, suppression BASE3/4, boutons plateau
- [ ] Test MSFS / GeForce NOW avec mapping définitif

## [Journal des Modifications]

| Date | Action |
|------|--------|
| 2026-06-14 | Initialisation du projet |
| 2026-06-15 | Mapping MSFS, discover, trim B5/B6, push GitHub |
| 2026-06-15 | Mapping : conflits RB/volets corrigés, boutons plateau ajoutés |
| 2026-06-20 | Gaz non mappé ; H2 (ABS_RX/RY) → stick droit complet |
| 2026-06-20 | Palonnier : LT/RT analogiques seuls (sans TL2/TR2), deadzone 8192, seuil pression 8 |
| 2026-06-20 | Script `airtuxone.sh` — lancement du démon (`python -m airtux_one.core`) |
| 2026-06-22 | Revert mapping gaz 2ᵉ manette (GFN/MSFS ne voit qu'une manette) |
| 2026-06-22 | Publication OSS : doc bilingue (README EN/FR, docs/en, docs/fr, CONTRIBUTING) |
| 2026-06-22 | config.toml : commentaires en anglais |
