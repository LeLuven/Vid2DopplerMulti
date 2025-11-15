#!/bin/bash
# =============================================================================
#
#  Setup-Skript für Vid2DopplerMulti auf Ubuntu 24.04 LTS (Noble Numbat)
#  Speziell angepasst für Intel Lunar Lake (Arc) GPUs (Level Zero)
#
#  VERSION 2 (Nur Anwendung):
#  Dieses Skript geht davon aus, dass die Intel Compute-Treiber
#  (libze_intel_gpu.so) bereits manuell kompiliert und installiert wurden.
#
#  Dieses Skript muss evtl. mehrmals ausgeführt werden (Kernel-Check, Miniconda).
#
# =============================================================================

set -e

# --- Globale Variablen ---
ENV_NAME="vid2dop39"
REPO_URL="https://github.com/LeLuven/Vid2DopplerMulti.git"
REPO_DIR="Vid2DopplerMulti"
export DEBIAN_FRONTEND=noninteractive

# --- Hilfsfunktion für Echo-Nachrichten ---
info() {
    echo " "
    echo "================================================================="
    echo " $1"
    echo "================================================================="
    echo " "
}

# =============================================================================
# PHASE 1: KERNEL-CHECK UND SYSTEM-VORBEREITUNG
# =============================================================================
info "PHASE 1: Überprüfe System und Kernel..."

# Aktiviere 'sudo' am Anfang
sudo -v

# Überprüfe, ob der OEM-Kernel bereits läuft.
if ! uname -r | grep -q 'oem'; then
    info "FEHLER: OEM-Kernel ist nicht aktiv (aktuell: $(uname -r))."
    echo "Lunar Lake benötigt einen neueren Kernel als den Standard-LTS-Kernel."
    echo "Installiere 'linux-oem-24.04'..."
    sudo apt-get update
    sudo apt-get install -y linux-oem-24.04
    
    info "KERNEL-INSTALLATION ABGESCHLOSSEN."
    echo "!!! BITTE STARTE DEINEN COMPUTER JETZT NEU !!!"
    echo "Führe dieses Skript nach dem Neustart einfach erneut aus."
    exit 1
else
    echo "OEM-Kernel ist aktiv ($(uname -r))."
fi

# =============================================================================
# PHASE 2: SYSTEM-VORAUSSETZUNGEN
# =============================================================================
info "PHASE 2: Installiere APT-Abhängigkeiten (Projekt & Tools)..."

# --- 2a. Intel oneAPI Repo hinzufügen (für 'intel-basekit') ---
# Wird benötigt, um setvars.sh und sycl-ls zu erhalten.
if [ ! -f "/etc/apt/sources.list.d/oneAPI.list" ]; then
    info "Füge Intel oneAPI Tools Repository hinzu..."
    wget -O- https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB | \
      gpg --dearmor | sudo tee /usr/share/keyrings/oneapi-archive-keyring.gpg > /dev/null
    echo "deb [signed-by=/usr/share/keyrings/oneapi-archive-keyring.gpg] https://apt.repos.intel.com/oneapi all main" | \
      sudo tee /etc/apt/sources.list.d/oneAPI.list
else
    echo "Intel oneAPI Repository bereits vorhanden."
fi

# --- 2b. APT-Abhängigkeiten installieren ---
info "Installiere alle APT-Pakete (Build-Tools, Git-LFS, Boost)..."
sudo apt-get update
sudo apt-get install -y \
  build-essential \
  git \
  git-lfs \
  cmake \
  pkg-config \
  python3-dev \
  libboost-dev \
  intel-basekit # Für 'sycl-ls' und '/opt/intel/oneapi/setvars.sh'

# =============================================================================
# PHASE 3: TREIBER- UND BERECHTIGUNGS-CHECK
# =============================================================================
info "PHASE 3: Überprüfe Treiber-Installation und Berechtigungen..."

# Prüfe, ob die 'render'-Gruppe aktiv ist
if ! groups | grep -q -w "render"; then
    info "FEHLER: Du bist noch nicht Mitglied der 'render'-Gruppe."
    echo "Bitte füge dich hinzu (sudo gpasswd -a $USER render) und starte den PC neu."
    echo "!!! BITTE STARTE DEINEN COMPUTER JETZT NEU !!!"
    echo "Führe dieses Skript nach dem Neustart einfach erneut aus."
    exit 1
else
    echo "'render'-Gruppe ist aktiv. Sehr gut."
fi

# =============================================================================
# PHASE 4: MINICONDA INSTALLIEREN
# =============================================================================
info "PHASE 4: Miniconda installieren..."

# Prüfe, ob Miniconda schon installiert ist
if [ -d "$HOME/miniconda3" ]; then
    echo "Miniconda-Verzeichnis bereits gefunden. Überspringe Installation."
else
    echo "Lade Miniconda-Installer herunter..."
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
    echo "Installiere Miniconda (im Batch-Modus)..."
    bash /tmp/miniconda.sh -b -p $HOME/miniconda3
    rm /tmp/miniconda.sh
    echo "Initialisiere Conda für Bash..."
    $HOME/miniconda3/bin/conda init bash
    
    info "MINICONDA-INSTALLATION ABGESCHLOSSEN."
    echo "!!! BITTE SCHLIESSE DIESES TERMINAL UND ÖFFNE EIN NEUES !!!"
    echo "Conda muss deine Shell neu initialisieren."
    echo "Führe dieses Skript danach einfach erneut aus."
    exit 1
fi

# =============================================================================
# PHASE 5: PROJEKT & PYTHON-UMGEBUNG (Vid2Doppler)
# =============================================================================
info "PHASE 5: Richte Vid2Doppler-Projekt und Conda-Umgebung ein..."

# Conda-Pfad für diese Sitzung aktivieren
source $HOME/miniconda3/bin/activate

# Prüfe, ob die Conda-Umgebung schon existiert
if conda env list | grep -q -w "$ENV_NAME"; then
    echo "Conda-Umgebung '$ENV_NAME' existiert bereits. Überspringe Erstellung."
    conda activate $ENV_NAME
else
    echo "Erstelle Conda-Umgebung '$ENV_NAME' mit Python 3.9..."
    conda create -n $ENV_NAME python=3.9 -y
    conda activate $ENV_NAME
    
    echo "Installiere ffmpeg/libiconv via Conda..."
    conda install -c conda-forge ffmpeg libiconv -y
    conda update -c conda-forge libstdcxx-ng -y
fi

# Klonen und LFS
if [ ! -d "$REPO_DIR" ]; then
    echo "Führe 'git lfs pull' aus..."
    git lfs pull
else
    echo "Repository bereits geklont."
    cd $REPO_DIR
fi

# Pip-Abhängigkeiten installieren (Intel-optimiert)
info "Installiere pip-Abhängigkeiten (Intel-optimiert)..."
echo "Installiere Abhängigkeiten aus requirements.txt (ohne torch/tensorflow)..."
grep -vE 'torch|tensorflow' requirements.txt | pip install -r /dev/stdin

echo "Installiere Intel-optimiertes PyTorch (IPEX)..."
# oneAPI-Variablen laden, damit pip die GPU erkennt
source /opt/intel/oneapi/setvars.sh
pip install torch torchvision torchaudio --index-url https://developer.intel.com/ipex-whl-stable-xpu

echo "Installiere Intel-optimiertes TensorFlow (ITEX)..."
pip install tensorflow==2.15.1
pip install intel-extension-for-tensorflow[xpu]

# =============================================================================
# PHASE 6: MESH-SUBMODUL BAUEN
# =============================================================================
info "PHASE 6: Baue 'mesh'-Modul..."

if [ -f "mesh/lib/libmesh.so" ]; then
    echo "'libmesh.so' existiert bereits. Überspringe 'make all'."
else
    cd mesh
    echo "Führe 'make all' im mesh-Verzeichnis aus..."
    # libboost-dev ist bereits installiert, kein BOOST_INCLUDE_DIRS nötig
    make all
    cd ..
fi

echo "Kopiere angepassten meshviewer.py..."
cp meshviewer.py $CONDA_PREFIX/lib/python3.9/site-packages/psbody/mesh/meshviewer.py

# =============================================================================
# ABSCHLUSS
# =============================================================================
info "SETUP ABGESCHLOSSEN!"
echo " "
echo "Dein System ist (hoffentlich) voll einsatzbereit."
echo "Du kannst jetzt die Tests ausführen:"
echo " "
echo "1. Aktiviere die Umgebung: conda activate $ENV_NAME"
echo "2. Lade die Treiber:     source /opt/intel/oneapi/setvars.sh"
echo "3. Teste PyTorch:        python -c \"import torch; import intel_extension_for_pytorch as ipex; print(f'PyTorch XPU verfügbar: {torch.xpu.is_available()}')\""
echo "4. Teste TensorFlow:     python -c \"import tensorflow as tf; print(f'TF-Geräte: {tf.config.experimental.list_physical_devices()}'')\""
echo " "
echo "Viel Erfolg!"