#!/bin/bash
# Executes the import script in reverse mode
# @author Kevin Veen-Birkenbach [aka. Frantz]
bash "$(dirname "$(readlink -f "${0}")")/import-data-from-system.sh" reverse
