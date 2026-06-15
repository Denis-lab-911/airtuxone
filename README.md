# AirTux One

Démon Linux qui lit un **TurtleBeach VelocityOne Flightstick** via `evdev` et émet vers une **manette Xbox 360 virtuelle** via `uinput`. Conçu pour Google Chrome et GeForce NOW afin de piloter Microsoft Flight Simulator avec le manche, les gaz et les boutons du stick.

## Installation rapide

```bash
git clone https://github.com/Denis-lab-911/airtuxone.git
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

Si `apt-get update` échoue à cause d'un **dépôt tiers** (`NO_PUBKEY`), ce n'est pas lié à AirTux One. Le script tente d'abord l'installation **sans** `apt update`. Sinon :

```bash
sudo apt install python3-venv python3-pip evtest
./setup.sh --skip-apt
```

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
| `[virtual_controller_2]` | Manette virtuelle **AirTux One** — mapping complet (axes, boutons) |

Le mapping MSFS validé est documenté dans [`mapping_velocityone_xbox.md`](mapping_velocityone_xbox.md).

### Mode PC obligatoire (axes des gaz)

Le VelocityOne démarre en **mode Xbox** par défaut. Sous Linux, le noyau charge alors le pilote **`xpad`** et le stick apparaît comme **`Generic X-Box pad`**.

Dans ce mode, les leviers de gaz sont mappés sur les **gâchettes Xbox** (`ABS_Z`, `ABS_RZ`) et ne reportent que des valeurs discrètes :

| Position du levier | Valeurs evtest typiques |
|--------------------|-------------------------|
| Repos / milieu     | `0` (aucun événement intermédiaire) |
| Léger déplacement  | `1`, `2` |
| À fond             | `32768` |

C'est le comportement que vous observez : **evtest ne réagit qu'aux extrêmes**, pas en analogique continu. AirTux One ne peut pas reconstruire une précision que le noyau ne fournit pas.

**Passer en mode PC** (mémorisé sur le stick) :

1. Brancher le stick en USB
2. **Tourner** la molette Configurator (OLED)
3. **Clic droit** sur la molette → **Input Mode**
4. **Tourner** pour sélectionner **PC**
5. **Clic** sur la molette pour confirmer

Vérifier ensuite :

```bash
./setup.sh --check
evtest
```

En mode PC, le device ne devrait **plus** s'appeler « Generic X-Box pad » et les leviers de gaz devraient produire une plage continue (ex. `-32768` … `32767`) sur leurs axes `ABS_*`.

### Découvrir le device et les codes evdev

**Outil recommandé — assistant de découverte AirTux One :**

```bash
source .venv/bin/activate
python -m airtux_one.discover
```

Fermez `evtest` avant de lancer l'outil (un seul lecteur à la fois).

L'outil affiche :
- la liste des axes/boutons disponibles au démarrage ;
- en direct chaque `[AXE]` ou `[BTN]` quand vous actionnez un contrôle ;
- à la fin (Ctrl+C) un **résumé** avec plages min/max et un extrait `config.toml` suggéré.

**Méthode manuelle avec evtest :**

Le VelocityOne est identifié par **vendor `10f5`** et **product `7055`**. Sous Linux Mint, il apparaît souvent comme **`Generic X-Box pad`** (pilote xpad ou Steam Input), pas sous son nom commercial.

**Étape 1 — Trouver le numéro `event*` :**

```bash
# Méthode interactive (recommandée)
evtest
# Choisir l'entrée « Generic X-Box pad » ou vendor 10f5:7055 dans la liste

# Ou lister tous les devices avec leur nom
grep -H . /sys/class/input/event*/device/name

# Ou repérer le VelocityOne par vendor/product
for d in /sys/class/input/event*/device/id_vendor; do
  v=$(cat "$d"); p=$(cat "${d%/*}/id_product")
  [[ "${v,,}" == "10f5" && "${p,,}" == "7055" ]] && \
    echo "/dev/input/$(basename $(dirname $(dirname $d)))  $(cat ${d%/*}/name)"
done
```

**Étape 2 — Tester avec le chemin réel** (remplacez `21` par votre numéro) :

```bash
evtest /dev/input/event21
```

Ne pas taper littéralement `eventN` — `N` est un placeholder pour le numéro affiché à l'étape 1.

**Étape 3 — Calibrer le mapping**

Déplacez le manche, le throttle et appuyez sur les boutons. Notez les codes `ABS_*` et `BTN_*` affichés, puis mettez à jour `config.toml`.

### Détection dans `config.toml`

Par défaut, seuls `vendor_id` et `product_id` sont utilisés (`name = ""`). Pour filtrer aussi par nom :

```toml
[source_device]
name = "Generic X-Box pad"
vendor_id = 0x10F5
product_id = 0x7055
```

Exemple d'entrée d'axe :

```toml
[virtual_controller_2.mapping.axes]
ABS_X = { target = "ABS_X", invert = false, deadzone = 4096, mode = "centered" }
```

Exemple d'entrée bouton :

```toml
[virtual_controller_2.mapping.buttons]
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

### 1. Manette virtuelle créée (evtest)

Après avoir lancé le démon (`python -m airtux_one.core`) :

```bash
evtest
# Choisir « AirTux One »
```

Ou lister les devices :

```bash
grep -H . /sys/class/input/event*/device/name | grep -i airtux
```

### 2. Test dans le navigateur (GeForce NOW / Chrome)

`chrome://gamepad-internals/` n'est **pas toujours accessible** (Chromium, Brave, certaines versions de Chrome). Alternatives :

| Méthode | Comment |
|---------|---------|
| **Testeur web** | [gamepad-tester.com](https://gamepad-tester.com/) — appuyez sur un bouton pour activer la détection |
| **jstest-gtk** | `sudo apt install jstest-gtk` → interface graphique |
| **jstest** | `jstest /dev/input/jsN` (numéro du device virtuel) |

Sur le testeur web : sélectionnez l'entrée **« AirTux One »** (souvent la 3ᵉ manette listée sous Chrome/Linux, après le stick physique).

**Repérer la bonne manette :**

| Indice | Nom typique | Utilisation |
|--------|-------------|-------------|
| 1 | Stick physique | Ne réagit pas (grab evdev) — normal |
| 2–3 | Autres entrées | **Choisir « AirTux One »** (`vendor 045e`, `product 02a1`) |

**Masquer js0** (optionnel, réduit la confusion avec le stick physique) :

```bash
./setup.sh --skip-apt    # règle udev TAG-=uaccess
# Débranchez/rebranchez le VelocityOne
```

Le démon lit toujours le stick via **evdev** (`event21`), pas via `js0`.

**Dépannage général :**

1. **Google Chrome** (pas Chromium/Brave) — le Gamepad API y est le plus fiable sous Linux
2. **Onglet actif** : cliquez dans la page, puis **bougez le manche physique** ou appuyez sur un bouton du VelocityOne (les manettes virtuelles ne bougent que via le démon)
3. **Démon lancé** : `python -m airtux_one.core` doit tourner dans un terminal
4. **Test local d'abord** :
   ```bash
   jstest /dev/input/js2   # ou le jsN d'AirTux One — Ctrl+C pour quitter
   ```
   Si `jstest` réagit au manche physique mais pas le navigateur, fermez et rouvrez l'onglet du testeur après avoir bougé le stick
5. **Chrome Flatpak** : accès `/dev/input` parfois bloqué — préférez le `.deb` officiel

### 3. Test GeForce NOW

1. Démon AirTux One lancé **avant** d'ouvrir GeForce NOW
2. Ouvrir GeForce NOW dans **Google Chrome** (recommandé pour le Gamepad API)
3. Lancer un jeu compatible manette
4. Dans les réglages du jeu / GeForce NOW, sélectionner la manette **AirTux One**

### 4. Mapping axe par axe

```bash
evtest /dev/input/eventN   # N = numéro de la manette virtuelle AirTux One
```

Bouger le manche physique → observer les axes sur la bonne manette virtuelle.

## Dépannage

| Problème | Solution |
|----------|----------|
| `Permission denied` sur `/dev/input/*` | `./setup.sh` ou `sudo usermod -aG input $USER` + reconnexion |
| `Permission denied` sur `/dev/uinput` | `./setup.sh` (crée le groupe `uinput` + udev) ou reconnexion après setup |
| Groupe `uinput` inexistant | Normal sur Mint — `./setup.sh` le crée automatiquement |
| Device source introuvable | Brancher le VelocityOne ; `./setup.sh --check` ; vérifier `vendor_id`/`product_id` dans `config.toml` |
| Gaz / throttle sans précision (evtest : 0, 1, 32768) | Stick en **mode Xbox** — passer en **mode PC** (section ci-dessus) |
| Stick vu comme « Generic X-Box pad » | Mode Xbox actif — passer en mode PC sur l'OLED du stick |
| Position vide / mauvaise manette dans le navigateur | Choisir **AirTux One** (`045e:02a1`) ; `./setup.sh --skip-apt` puis replug USB pour masquer js0 |
| gamepad-tester ne réagit pas | Chrome (pas Brave) ; onglet actif ; démon lancé ; `jstest` sur le js virtuel |
| Double entrée / conflit Steam | `grab_source = true` dans `[daemon]` (valeur par défaut) |
| Codes d'axes incorrects | `python -m airtux_one.discover` puis mettre à jour `config.toml` |
| `apt` lock / `aptk` en cours | Fermer le Gestionnaire de mises à jour Mint, attendre, ou `./setup.sh --skip-apt` |
| `apt-get update` / `NO_PUBKEY` (dépôt tiers) | Relancer `./setup.sh` (installe sans update) ou `./setup.sh --skip-apt` |

## Sécurité

- Ne **pas** lancer le démon en root.
- Utiliser les groupes `input` et `uinput` comme prévu.
- Le grab exclusif (`grab_source`) empêche les autres apps de lire le flightstick physique pendant que le démon tourne.

## Arborescence

```
airtuxone/
├── agent.md
├── config.toml
├── mapping_velocityone_xbox.md
├── requirements.txt
├── setup.sh
├── README.md
└── airtux_one/
    ├── __init__.py
    ├── core.py
    ├── devices.py
    ├── discover.py
    └── mapper.py
```

## Licence

Usage personnel — projet AirTux One.
