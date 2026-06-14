# AirTux One

Démon Linux qui lit un **TurtleBeach VelocityOne Flightstick** via `evdev` et émet vers **deux manettes Xbox 360 virtuelles** via `uinput`. Conçu pour Google Chrome et GeForce NOW afin de transmettre l'ensemble des axes analogiques (manche + quadrant des gaz) à Flight Simulator sans perte de précision.

## Installation rapide

```bash
git clone <repo-url> airtuxone
cd airtuxone
chmod +x setup.sh
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

Le script attendra sinon jusqu'à 2 minutes que le verrou apt soit libéré.

Si `apt-get update` échoue à cause du dépôt **Cursor** (`NO_PUBKEY 42A1772E62E492D6`), ce n'est pas lié à AirTux One. Le script tente d'abord l'installation **sans** `apt update`. Sinon :

```bash
sudo apt install python3-venv python3-pip evtest
./setup.sh --skip-apt
```

Pour corriger le dépôt Cursor (optionnel) : désactiver temporairement `/etc/apt/sources.list.d/cursor.list` ou réimporter la clé GPG depuis la doc Cursor.

### Ignorer les règles udev

```bash
./setup.sh --skip-udev
```


## Installation manuelle

Si vous préférez ne pas utiliser le script :

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

### Structure

| Section | Rôle |
|---------|------|
| `[source_device]` | Critères de détection du flightstick (nom, vendor, product) |
| `[daemon]` | Options du démon (`grab_source`, `log_level`) |
| `[virtual_controller_1]` | Manette virtuelle 1 — manche + boutons de base |
| `[virtual_controller_2]` | Manette virtuelle 2 — quadrant des gaz |

### Découvrir les codes evdev

Les codes source du VelocityOne doivent être confirmés sur **votre** matériel :

```bash
# Lister les devices
evtest
# Ou cibler directement le VelocityOne
evtest /dev/input/eventN
```

Déplacez le manche, le throttle et appuyez sur les boutons. Notez les codes `ABS_*` et `BTN_*` affichés, puis mettez à jour `config.toml`.

Exemple d'entrée d'axe :

```toml
[virtual_controller_1.mapping.axes]
ABS_RX = { target = "ABS_X", invert = false, deadzone = 128 }
```

Exemple d'entrée bouton :

```toml
[virtual_controller_1.mapping.buttons]
BTN_TRIGGER = "BTN_SOUTH"
```

Chemin alternatif du fichier de config :

```bash
export AIRTUX_CONFIG=/chemin/vers/config.toml
```

## Lancement

```bash
source .venv/bin/activate
python -m airtux_one.core
```

Arrêt propre : `Ctrl+C` ou `kill -TERM <pid>`.

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

Activation :

```bash
systemctl --user daemon-reload
systemctl --user enable --now airtux-one.service
systemctl --user status airtux-one.service
```

## Vérification

1. **Manettes virtuelles** — après démarrage du démon :

   ```bash
   evtest
   # Deux devices « AirTux One - … » doivent apparaître
   ```

2. **Chrome** — ouvrir `chrome://gamepad-internals/` et vérifier que deux manettes Xbox 360 sont détectées.

3. **Mapping** — bouger le manche / throttle et observer les axes sur chaque manette virtuelle via `evtest`.

## Dépannage

| Problème | Solution |
|----------|----------|
| `Permission denied` sur `/dev/input/*` | `./setup.sh` ou `sudo usermod -aG input $USER` + reconnexion |
| `Permission denied` sur `/dev/uinput` | `./setup.sh` (crée le groupe `uinput` + udev) ou reconnexion après setup |
| Groupe `uinput` inexistant | Normal sur Mint — `./setup.sh` le crée automatiquement |
| Device source introuvable | Brancher le VelocityOne, lancer `./setup.sh --check` |
| Chrome ne voit qu'une manette | Vérifier les noms distincts dans `config.toml`, redémarrer le démon |
| Double entrée / conflit Steam | `grab_source = true` dans `[daemon]` (valeur par défaut) |
| Codes d'axes incorrects | Recalibrer avec `evtest`, mettre à jour `config.toml` |
| `apt` lock / `aptk` en cours | Fermer le Gestionnaire de mises à jour Mint, attendre, ou `./setup.sh --skip-apt` |
| `apt-get update` / GPG Cursor (`NO_PUBKEY`) | Erreur du dépôt Cursor, pas d'AirTux One — relancer `./setup.sh` (installe sans update) ou `./setup.sh --skip-apt` |

## Sécurité

- Ne **pas** lancer le démon en root.
- Utiliser les groupes `input` et `uinput` comme prévu.
- Le grab exclusif (`grab_source`) empêche les autres apps de lire le flightstick physique pendant que le démon tourne.

## Arborescence

```
airtuxone/
├── .cursorrules
├── agent.md
├── config.toml
├── requirements.txt
├── setup.sh
├── README.md
└── airtux_one/
    ├── __init__.py
    ├── core.py
    ├── devices.py
    └── mapper.py
```

## Licence

Usage personnel — projet AirTux One.
