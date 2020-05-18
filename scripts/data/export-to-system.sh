#!/bin/bash
# Executes the import script in reverse mode
# @author Kevin Veen-Birkenbach [aka. Frantz]
# shellcheck source=/dev/null # Deactivate SC1090
source "$(dirname "$(readlink -f "${0}")")/../base.sh" || (echo "Loading base.sh failed." && exit 1)
bash "$SCRIPT_PATH""data/import-from-system.sh" reverse
info "Setting right permissions for importet files..."
chown -R $USER:$USER ~
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_rsa
chmod 600 ~/.ssh/id_rsa.pub
