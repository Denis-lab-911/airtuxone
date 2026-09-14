<p align="center">
  <img src="airtuxone_logo.png" alt="AirTuxOne" width="240">
</p>

<p align="center">
  <a href="README.md">English</a> | <strong>Français</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License: GPL v3"></a>
</p>

# AirTuxOne

AirTuxOne est un démon Linux qui transpose un joystick **Turtle Beach VelocityOne Flightstick** vers une ou plusieurs **manette(s) Xbox 360 virtuelle(s)**. Conçu pour piloter dans Microsoft Flight Simulator avec le manche, les boutons et les manettes de gaz du stick, même depuis un vieux PC sous Linux, en s'appuyant par exemple sur le service de cloud gaming Geforce Now et un navigateur Firefox.

## Pourquoi AirTuxOne ?

AirTuxOne a été pensé pour répondre à la difficulté suivante : comment jouer à Flight Simulator 2020 ou 2024 à partir d'un PC relativement ancien (qui ne dispose donc pas de la puissance nécessaire à faire tourner le jeu), sous un système Linux, tout en bénéficiant du confort de jeu d'un joystick ?
La 1ère réponse a été d'utiliser un service de cloud gaming : cela permet de fournir la puissance nécessaire à un jeu comme Flight Simulator tout en streamant le rendu graphique vers un PC qui n'aura qu'à afficher le flux streamé. Avec un telle solution, il est facile de jouer à ce simulateur avec clavier + souris ou une manette standard Xbox, à la fois reconnue par le service de streaming et par le jeu. Mais il restait frustrant de ne pas pouvoir jouer avec un joystick plus adapté à un simulateur de vol !

La seconde réponse a donc consisté à faire passer le joystick pour une ou plusieurs manettes Xbox virtuelles, pour pouvoir ensuite configurer l'utilisation des différents boutons, axes et manettes de gaz directement dans le jeu de simulation.

Attention :
- le navigateur Firefox et le service Geforce Now sont des solutions tierces. Le concepteur d'AirTuxOne n'est pas responsable de leur bon fonctionnement.
- le service Geforce Now nécessite une souscription payante à souscrire séparemment.

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
- ajout de l'utilisateur aux groupes dédiés `airtux-input` et `uinput`
- installation optionnelle des règles udev pour le VelocityOne

**Important :** si les groupes ont été modifiés, déconnectez-vous et reconnectez-vous (ou redémarrez) avant de lancer le démon.

### Diagnostics

```bash
./setup.sh --check
```

### Ignorer l'installation apt

Si le Gestionnaire de mises à jour APT (`aptk`) bloque apt :

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
sudo usermod -aG airtux-input,uinput $USER
# Reconnexion requise après modification des groupes
```

## Configuration

Le mapping de base permet de faire la correspondance entre le joystick, les boutons associés et une unique manette Xbox virtuelle. Dans cette configuration, les manettes de gaz associés au joystick ne peuvent pas être mappés. Le mapping de base est défini dans [`config.toml`](config.toml). **Note : aucun axe ou bouton n'est codé en dur dans le code Python.**

Pour pouvoir utiliser les manettes des gaz associées au joystick, utilisez les profils spécialisés selon le type d'avion :

- [`config.dual.toml`](config.dual.toml): profil recommandé pour un pilotage où une seule manette des gaz suffit. Ce profil crée :
    - une manette pour mapper l'axe principal du joystick et ses principaux boutons;
    - une seconde manette virtuelle pour la gestion des gaz.
- [`config.triple.toml`](config.triple.toml): profil pour monomoteurs / bimoteurs / hélicos, avec une manette virtuelle distincte par manette de gaz, permettant d'utiliser 2 manettes de gaz.

| Section | Rôle |
|---------|------|
| `[source_device]` | Critères de détection du flightstick (nom, vendor, product) |
| `[daemon]` | Options du démon (`grab_source`, `log_level`) |
| `[virtual_controller_1]` | Première manette virtuelle ; son rôle dépend du profil choisi |
| `[virtual_controller_2]` | Seconde manette virtuelle ; son rôle dépend du profil choisi |
| `[virtual_controller_3]` | Troisième manette facultative du profil triple |

| Profil | Disposition des manettes |
|---------|--------------------------|
| Base (`config.toml`) | 1 : manche **AirTuxOne** |
| Dual (`config.dual.toml`) | 1 : manche **AirTuxOne** ; 2 : **AirTuxOne - Throttle** |
| Triple (`config.triple.toml`) | 1 : manche **AirTuxOne** ; 2 : **Throttle 1** ; 3 : **Throttle 2** |

### Vue d'ensemble du profil triple

```text
                               AIRTUX ONE TRIPLE (MAPPING)

   +---------------------------------------+
   |   TURTLE BEACH VELOCITYONE (PC Mode)  |
   +---------------------------------------+
                      |
                      | (evdev)
                      v
   +---------------------------------------+
   |           AIRTUX ONE DAEMON           |
   +---------------------------------------+
                      |
                      | (uinput)
        +-------------+-------------+
        |             |             |
        v             v             v
  [Manette 1]   [Manette 2]   [Manette 3]
```

### Vue détaillée du mapping

```text
========================================================================================
SOURCE : JOYSTICK PHYSICAL LAYOUT               MANETTES VIRTUELLES XBOX CIBLES
========================================================================================

--- TÊTE DU MANCHE (STICK HEAD) ---
┌───────────────────────────────────────┐
│ [H1 Hat] Chapeau chinois              │───────► Manette 1 : Croix directionnelle (D-Pad)
│ [H2 Stick] Mini-stick analogique      │───────► Manette 1 : Stick Droit (Look / Caméra)
│                                       │
│ [B1] Gâchette principale              │───────► Manette 1 : Bouton A
│ [B2] Bouton pouce gauche              │───────► Manette 1 : Bouton B
│ [B3] Bouton pouce droit               │───────► Manette 1 : Bouton X
│ [B4] Bouton sommet                    │───────► Manette 1 : Bouton Y
│                                       │
│ [B5] Bouton supérieur haut            │───────► Manette 1 : Combo [LB + A]
│ [B6] Bouton supérieur bas             │───────► Manette 1 : Combo [LB + B]
│ [B7] Bouton latéral haut              │───────► Manette 1 : Combo [LB + X]
│ [B8] Bouton latéral bas               │───────► Manette 1 : Combo [LB + Y]
│ [Gâchette sec.]                       │───────► Manette 1 : Bouton RB
└───────────────────────────────────────┘

--- CORPS & BASE (AXES & BOUTONS) ---
┌───────────────────────────────────────┐
│ Axe X (Axe horizontal du manche)      │───────► Manette 1 : Stick Gauche X (Roll)
│ Axe Y (Axe vertical du manche)        │───────► Manette 1 : Stick Gauche Y (Pitch)
│ Axe Z (Torsion du manche)             │───────► Manette 1 : Gâchettes LT / RT (Rudder)
│                                       │
│ [B16] Bouton base                     │───────► Manette 1 : Bouton LB (Modifier)
│ [Bas-Gauche] Bouton base              │───────► Manette 1 : Bouton Back / Select
│ [Bas-Centre] Bouton base              │───────► Manette 1 : Bouton L3 (Thumb L)
│ [Bas-Droite] Bouton base              │───────► Manette 1 : Bouton Start
│ [Logo Xbox] Bouton central            │───────► Manette 1 : Bouton Guide / Xbox
└───────────────────────────────────────┘

--- BLOC MANETTES DE GAZ (THROTTLE QUADRANT) ---
┌───────────────────────────────────────┐
│ Levier 1 (Axe RZ)                     │───────► Manette 2 : Stick Gauche Y (Throttle 1)
│ Levier 2 (Axe Throttle)               │───────► Manette 3 : Stick Droit Y (Throttle 2)
└───────────────────────────────────────┘
```

Le mapping MSFS est documenté dans [`docs/fr/mapping_velocityone_xbox.md`](docs/fr/mapping_velocityone_xbox.md).

### Mode PC obligatoire

Le joystick VelocityOne démarre en **mode Xbox** par défaut. Sous Linux, le pilote **`xpad`** expose les leviers de gaz en valeurs discrètes seulement (`0`, `1`, `32768`). **Passez en mode PC** sur l'OLED du stick (Configurator → Input Mode → PC), puis vérifiez avec `./setup.sh --check` et `evtest`.

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

Il est conseillé de suivre la procédure de lancement suivant, dans l'ordre :

1) Ouvrir un terminal
2) Lancement du script AirTuxOne (avec au choix profils 1 manette, 2 manettes ou 3 manettes)
3) Lancement de votre navigateur (pour accès au service de streaming et au jeu)
4) Lancement du service de streaming puis du jeu

**Commande pour lancer le profil "1 manette virtuelle" :**

```bash
./airtuxone.sh
```

**Commande pour lancer le profil _dual_ "2 manettes virtuelles"** (1 levier de gaz sur une seconde manette Xbox virtuelle) :

```bash
./airtuxone-dual.sh
```

Attention : Firefox est le navigateur recommandé pour les profils multi-manettes.

Note : les profils multi-manettes (dual ou triple) sont conçus et testés pour **Firefox + GeForce NOW**. Ils ne sont pas fiables sous **Chrome** pour cette configuration particulière, où les manettes virtuelles supplémentaires ne sont pas toujours exposées correctement. Les profils n'ont pas été testés avec d'autres navigateurs, d'autres services de streaming, ou d'autres jeux.



**Commande pour lancer le profil _triple_ 3 manettes (2 leviers de gaz séparés sur une manette Xbox virtuelle distincte) :**

```bash
./airtuxone-triple.sh
```

**Note importante :** l'utilisation du profil _triple_ est nécessaire pour que GeForce NOW et MSFS voient des périphériques distincts pour **Throttle 1** et **Throttle 2**. Cela permet d'utiliser réellement les 2 manettes de gaz analogiques du joystick.

## Arrêt du démon

Arrêt propre : `Ctrl+C` ou `kill -TERM <pid>` dans le terminal où tourne le démon.

## Utilisation des manettes virtuelles dans MSFS

Dans MSFS, agir sur les différents axes ou boutons permettra au jeu de détecter les différentes manettes virtuelles (par exemple, "Manette 1", "Manette 2", "Manette 3" si vous utilisez le profil _triple_).


## Vérification

### Manette virtuelle (evtest / jstest)

```bash
evtest    # choisir « AirTuxOne »
jstest /dev/input/jsN
```

### Navigateur (GeForce NOW / Firefox)

1. Démon lancé en premier
2. **Firefox**
3. Sélectionner **AirTuxOne** (`vendor 045e`, `product 02a1`) dans le testeur (par exemple : https://hardwaretester.com/gamepad) ou MSFS

## Dépannage

| Problème | Solution |
|----------|----------|
| `Device or resource busy` au démarrage | Fermer jstest/evtest et les onglets Firefox ; relancer `./airtuxone.sh` ou ses variantes dual et triple |
| `Permission denied` sur `/dev/input/*` | `./setup.sh` ou `sudo usermod -aG airtux-input $USER` + reconnexion |
| `Permission denied` sur `/dev/uinput` | `./setup.sh` + reconnexion |
| Device source introuvable | Brancher le VelocityOne ; `./setup.sh --check` ; mode **PC** sur le stick |
| Gaz sans précision (evtest : 0, 1, 32768) | Mode Xbox actif — passer en **mode PC** |
| Mauvaise manette dans le navigateur | Choisir **AirTuxOne** (`045e:02a1`) |
| Codes d'axes incorrects | `python -m airtux_one.discover` puis mettre à jour `config.toml` |

## Sécurité

- Ne **pas** lancer le démon en root.
- Utiliser uniquement les groupes dédiés `airtux-input` et `uinput` installés par `./setup.sh`.
- `airtux-input` est limité au VelocityOne ; ne pas ajouter d'utilisateur au groupe global `input` pour AirTuxOne. Un membre existant peut le quitter avec `sudo gpasswd -d $USER input` seulement après avoir vérifié qu'aucun autre logiciel ne l'utilise.
- Le grab exclusif (`grab_source`) bloque les autres lecteurs du stick physique.

## Arborescence

```
airtuxone/
├── airtuxone_logo.png
├── airtuxone.sh
├── airtuxone-dual.sh
├── airtuxone-triple.sh
├── config.toml
├── config.dual.toml
├── config.triple.toml
├── CONTRIBUTING.md
├── docs/
│   ├── en/mapping_velocityone_xbox.md
│   └── fr/mapping_velocityone_xbox.md
├── LICENSE
├── README.md
├── README.fr.md
├── requirements.txt
├── setup.sh
├── install-desktop.sh
├── install-desktop-dual.sh
├── install-desktop-triple.sh
└── airtux_one/
    ├── core.py
    ├── devices.py
    ├── discover.py
    ├── learn.py
    └── mapper.py
```

## Utilisateur avancé

Cette configuration est optionnelle et vise à permettre le démarrage automatique du script AirTuxOne au lancement d'une session. Elle ne sélectionne pas un profil à elle seule : il faut pointer vers la configuration correspondant au profil choisi (`config.toml`, `config.dual.toml` ou `config.triple.toml`).

### Démarrage automatique avec systemd

Créez `~/.config/systemd/user/airtux-one.service` :

```ini
[Unit]
Description=AirTuxOne flight stick mapper
After=graphical-session.target

[Service]
ExecStart=/chemin/vers/airtuxone/.venv/bin/python -m airtux_one.core
WorkingDirectory=/chemin/vers/airtuxone
Restart=on-failure
Environment=AIRTUX_CONFIG=/chemin/vers/airtuxone/config.toml

[Install]
WantedBy=default.target
```

Pour un profil dual ou triple, remplacez `config.toml` par `config.dual.toml` ou `config.triple.toml` dans la variable `Environment`, puis activez le service avec :

```bash
systemctl --user daemon-reload
systemctl --user enable --now airtux-one.service
```

## Licence

Ce projet est publié sous [GNU General Public License v3.0](LICENSE) (GPL-3.0).

## Contribution

Voir [CONTRIBUTING.md](CONTRIBUTING.md).