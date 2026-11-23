#!/bin/bash
# Runs ON the VM (Ubuntu 22.04): install OpenFOAM (ESI) + python, matching the paper's v2112 if available.
set -euo pipefail
sudo apt-get update -qq
curl -s https://dl.openfoam.com/add-debian-repo.sh | sudo bash
sudo apt-get install -y -qq openfoam2112-default python3-numpy || sudo apt-get install -y -qq openfoam2306-default python3-numpy
ls /usr/lib/openfoam/
echo SETUP_DONE
