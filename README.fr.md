<p align="center">
  <img src="airtuxone_logo.png" alt="AirTux One" width="240">
</p>

<p align="center">
  <a href="README.md">English</a> | <strong>Français</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License: GPL v3"></a>
</p>

# AirTux One

Démon Linux qui lit un **Turtle Beach VelocityOne Flightstick** via `evdev` et émet vers une **manette Xbox 360 virtuelle** via `uinput`. Conçu pour Google Chrome et GeForce NOW afin de piloter Microsoft Flight Simulator avec le manche et les boutons du stick.

## Installation rapide

```bash
git clone https://github.com/Denis-lab-911/airtuxone.git
cd airtuxone
chmod +x setup.sh airtuxone.sh
./setup.sh
```

Le script `setup.sh` automatise :

- installation des paquets système (`python3-venv`, `evtest`, …)
- création du venv `.venv/` et installation des dépendances Python
- chargement persistant du module noyau `uinput`
- ajout de l'utilisateur aux groupes `input` et `uinput`
- installation optionnelle des règles udev pour le VelocityOne

**Important :** si les groupes ont été modifiés, déconnectez-vous et reconnectez-vous (ou redémarrez) avant de lancer le démon.

### Diagnostics

```bash
./setup.sh --check
```

### Ignorer l'installation apt

Si le Gestionnaire de mises à jour Mint (`aptk`) bloque apt :

```bash
./setup.sh --skip-apt
```

Si `apt-get update` échoue à cause d'un **dépôt tiers** (`NO_PUBKEY`) :

```bash
sudo apt install python3-venv python3-pip evtest
./setup.sh --skip-apt
```

### Ignorer les règles udev

```bash
./setup.sh --skip-udev
```

## Installation manuelle

```bash
sudo apt install python3-venv python3-pip evtest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sudo modprobe uinput
echo uinput | sudo tee /etc/modules-load.d/uinput.conf
sudo usermod -aG input,uinput $USER
# Reconnexion requise après modification des groupes
```

## Configuration

Tout le mapping est défini dans [`config.toml`](config.toml). **Aucun axe ou bouton n'est codé en dur dans le Python.**

| Section | Rôle |
|---------|------|
| `[source_device]` | Critères de détection du flightstick (nom, vendor, product) |
| `[daemon]` | Options du démon (`grab_source`, `log_level`) |
| `[virtual_controller_1]` | Manette leurre technique (Chrome) — sans mapping |
| `[virtual_controller_2]` | Manette virtuelle **AirTux One** — mapping complet |

Le mapping MSFS est documenté dans [`docs/fr/mapping_velocityone_xbox.md`](docs/fr/mapping_velocityone_xbox.md).

### Mode PC obligatoire

Le VelocityOne démarre en **mode Xbox** par défaut. Sous Linux, le pilote **`xpad`** expose les leviers de gaz en valeurs discrètes seulement (`0`, `1`, `32768`). **Passez en mode PC** sur l'OLED du stick (Configurator → Input Mode → PC), puis vérifiez avec `./setup.sh --check` et `evtest`.

### Découvrir les codes evdev

```bash
source .venv/bin/activate
python -m airtux_one.discover
```

Assistant de mapping avec manette Xbox physique :

```bash
python -m airtux_one.learn
```

Chemin alternatif de configuration :

```bash
export AIRTUX_CONFIG=/chemin/vers/config.toml
```

## Lancement

```bash
./airtuxone.sh
```

**Deux manettes (expérimental, Firefox) :** leviers de gaz sur une seconde manette Xbox virtuelle. Ne remplace pas le profil par défaut.

```bash
./airtuxone-dual.sh
```

Manettes attendues : **AirTux One** (manche) et **AirTux One - Throttle** (levier gauche → stick gauche Y, levier droit → stick droit Y). Config : [`config.dual.toml`](config.dual.toml).

Dans MSFS : filtrer sur **AirTux One - Throttle** avant d’assigner (sinon « mauvais périphérique »). Effacer l’axe **Throttle** combiné, puis **Throttle 1** / **Throttle 2** chacun sur un levier. Ne pas laisser de binding vol (roulis / tangage / regard) sur cette manette.

Ou manuellement :

```bash
source .venv/bin/activate
python -m airtux_one.core
```

Arrêt propre : `Ctrl+C` ou `kill -TERM <pid>`.

**Ordre GeForce NOW :** lancez le démon **avant** d'ouvrir Chrome / GeForce NOW.

## Service systemd (utilisateur)

Créez `~/.config/systemd/user/airtux-one.service` :

```ini
[Unit]
Description=AirTux One flight stick mapper
After=graphical-session.target

[Service]
ExecStart=/chemin/vers/airtuxone/.venv/bin/python -m airtux_one.core
WorkingDirectory=/chemin/vers/airtuxone
Restart=on-failure
Environment=AIRTUX_CONFIG=/chemin/vers/airtuxone/config.toml

[Install]
WantedBy=default.target
```

## Vérification

### Manette virtuelle (evtest / jstest)

```bash
evtest    # choisir « AirTux One »
jstest /dev/input/jsN
```

### Navigateur (GeForce NOW / Chrome)

1. Démon lancé en premier
2. **Google Chrome** (pas Chromium/Brave)
3. Sélectionner **AirTux One** (`vendor 045e`, `product 02a1`) dans le testeur ou MSFS

## Dépannage

| Problème | Solution |
|----------|----------|
| `Device or resource busy` au démarrage | Fermer jstest/evtest et les onglets Chrome (gamepad-tester, GFN) ; relancer `./airtuxone.sh` |
| `Permission denied` sur `/dev/input/*` | `./setup.sh` ou `sudo usermod -aG input $USER` + reconnexion |
| `Permission denied` sur `/dev/uinput` | `./setup.sh` + reconnexion |
| Device source introuvable | Brancher le VelocityOne ; `./setup.sh --check` ; mode **PC** sur le stick |
| Gaz sans précision (evtest : 0, 1, 32768) | Mode Xbox actif — passer en **mode PC** |
| Mauvaise manette dans le navigateur | Choisir **AirTux One** (`045e:02a1`) |
| Codes d'axes incorrects | `python -m airtux_one.discover` puis mettre à jour `config.toml` |

## Sécurité

- Ne **pas** lancer le démon en root.
- Utiliser les groupes `input` et `uinput`.
- Le grab exclusif (`grab_source`) bloque les autres lecteurs du stick physique.

## Arborescence

```
airtuxone/
├── airtuxone_logo.png
├── airtuxone.sh
├── airtuxone-dual.sh
├── config.toml
├── config.dual.toml
├── CONTRIBUTING.md
├── docs/
│   ├── en/mapping_velocityone_xbox.md
│   └── fr/mapping_velocityone_xbox.md
├── LICENSE
├── README.md
├── README.fr.md
├── requirements.txt
├── setup.sh
└── airtux_one/
    ├── core.py
    ├── devices.py
    ├── discover.py
    ├── learn.py
    └── mapper.py
```

## Licence

Ce projet est publié sous [GNU General Public License v3.0](LICENSE) (GPL-3.0).

## Contribution

Voir [CONTRIBUTING.md](CONTRIBUTING.md).
