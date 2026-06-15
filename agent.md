# Log de l'agent — AirTux One

## [Objectif Général]

Développer un démon Linux (AirTux One) qui intercepte les entrées d'un TurtleBeach VelocityOne Flightstick via `evdev` et les traduit vers **deux manettes Xbox 360 virtuelles** distinctes via `uinput`. Objectif : permettre à Google Chrome et GeForce NOW de recevoir l'ensemble des axes analogiques (quadrant des gaz + manche) pour jouer à Flight Simulator sans perte de précision.

## [Architecture Validée]

```
airtuxone/
├── .cursorrules          # Règles agent Cursor
├── agent.md              # Ce journal
├── config.toml           # Mapping TOML (virtual_controller_1 et 2)
├── requirements.txt      # evdev, tomli (Python < 3.11)
├── setup.sh              # Script d'installation Linux Mint
├── .gitignore
├── README.md
└── airtux_one/
    ├── __init__.py
    ├── core.py           # Démon, boucle evdev, signaux SIGTERM/SIGINT
    ├── devices.py        # Détection source, 2× uinput Xbox 360
    └── mapper.py         # Chargement TOML, lookup O(1), transformations
```

- Mapping 100 % externe via `config.toml` (aucun code en dur).
- Lookup O(1) : dictionnaires inversés au démarrage dans `mapper.py`.
- Permissions Linux : groupes `input` et `uinput`, module noyau `uinput`.

## [Tâches Réalisées]

- [x] Initialisation du plan d'implémentation
- [x] Création de `.cursorrules` et `agent.md`
- [x] Scaffolding : `.gitignore`, `requirements.txt`, `setup.sh`, `__init__.py`
- [x] `config.toml` avec schéma virtual_controller_1/2 (placeholders evtest)
- [x] `mapper.py` : chargement TOML, inversion dict O(1), transformations invert/deadzone
- [x] `devices.py` : détection source, 2× UInput Xbox 360, grab/ungrab
- [x] `core.py` : boucle evdev avec select (arrêt réactif), signaux SIGTERM/SIGINT
- [x] `README.md` : installation, config, systemd, dépannage
- [x] Vérification syntaxe Python et chargement config (10 mappings)

## [Tâches Restantes]

- [ ] Validation matérielle via `evtest` sur VelocityOne réel
- [ ] Ajustement des codes source dans `config.toml` selon le matériel
- [ ] Test Chrome / GeForce NOW avec deux manettes détectées

## [Journal des Modifications]

| Date | Action |
|------|--------|
| 2026-06-14 | Initialisation du projet et plan validé |
| 2026-06-14 | Ajout du script `setup.sh` au plan |
| 2026-06-14 | Début de l'implémentation — création `.cursorrules` et `agent.md` |
| 2026-06-15 | config.toml : mapping complet VelocityOne PC (table utilisateur) |
