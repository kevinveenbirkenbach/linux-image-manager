#!/bin/bash
#
# Pushs all repositories
# @param $1 git command which should be executed instead of default pull
# @author Kevin Veen-Birkenbach [aka. Frantz]
source "$(dirname "$(readlink -f "${0}")")/../base.sh" || (echo "Loading base.sh failed." && exit 1)
if [ $# -eq 1 ]
  then
    git_command=$1
  else
    git_command="push"
fi
find $LOCAL_REPOSITORIES_PATH -maxdepth 1 -mindepth 1 -type d -exec bash -c "(cd {} && echo 'In directory: {}' && git status && echo 'Executes git $git_command' && git $git_command --all)" \;
