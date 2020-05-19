#!/bin/bash
#
# This script contains the global program variables and functions
#
# shellcheck disable=SC2034 #Deactivate checking of unused variables

REPOSITORY_PATH=$(readlink -f "$(dirname "$(readlink -f "${0}")")/../../") # Propably this can be optimized
CONFIGURATION_PATH="$REPOSITORY_PATH""/configuration/"
PACKAGE_PATH="$CONFIGURATION_PATH""packages/"
TEMPLATE_PATH="$CONFIGURATION_PATH""templates/";
HOME_TEMPLATE_PATH="$TEMPLATE_PATH""home/";
ENCRYPTED_PATH="$REPOSITORY_PATH/.encrypted";
DECRYPTED_PATH="$REPOSITORY_PATH/decrypted";
SCRIPT_PATH="$REPOSITORY_PATH/scripts/";
DATA_PATH="$DECRYPTED_PATH/data";
BACKUP_PATH="$DECRYPTED_PATH/backup";

COLOR_RED=$(tput setaf 1)
COLOR_GREEN=$(tput setaf 2)
COLOR_YELLOW=$(tput setaf 3)
COLOR_BLUE=$(tput setaf 4)
COLOR_MAGENTA=$(tput setaf 5)
COLOR_CYAN=$(tput setaf 6)
COLOR_WHITE=$(tput setaf 7)
COLOR_RESET=$(tput sgr0)

# FUNCTIONS

message(){
  echo "$1[$2]:${COLOR_RESET} $3 ";
}

question(){
  message "${COLOR_MAGENTA}" "QUESTION" "$1";
}

info(){
  message "${COLOR_BLUE}" "INFO" "$1";
}

warning(){
  message "${COLOR_YELLOW}" "WARNING" "$1";
}

success(){
  message "${COLOR_GREEN}" "SUCCESS" "$1";
}

error(){
  if [ -z "$1" ]
    then
      message="Failed."
    else
      message="$1"
  fi
  message "${COLOR_RED}" "ERROR" "$message -> Leaving program."
  if declare -f "destructor" > /dev/null
    then
      info "Calling destructor..."
      destructor
    else
      warning "No destructor defined."
      info "Can be that this script left some waste."
  fi
  exit 1;
}

HEADER(){
  echo
  echo "${COLOR_YELLOW}The"
  base64 -d <<<"ICBfX19fXyAgICAgICAgICAgICAgICBfX19fXyAgICAgICAgICAgXyAgICAgICAgICAgICAgICAgCiAvIF9fX198ICAgICAgICAgICAgICAvIF9fX198ICAgICAgICAgfCB8ICAgICAgICAgICAgICAgIAp8IHwgICAgIF9fXyAgXyBfXyBfX198IChfX18gIF8gICBfIF9fX3wgfF8gX19fIF8gX18gX19fICAKfCB8ICAgIC8gXyBcfCAnX18vIF8gXFxfX18gXHwgfCB8IC8gX198IF9fLyBfIFwgJ18gYCBfIFwgCnwgfF9fX3wgKF8pIHwgfCB8ICBfXy9fX19fKSB8IHxffCBcX18gXCB8fCAgX18vIHwgfCB8IHwgfAogXF9fX19fXF9fXy98X3wgIFxfX198X19fX18vIFxfXywgfF9fXy9cX19cX19ffF98IHxffCB8X3wKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgX18vIHwgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgfF9fXy8gICAgICAgICAgICAgICAgICAgICAgIAo="
  echo "is an administration tool designed from and for Kevin Veen-Birkenbach."
  echo
  echo "Licensed under GNU GENERAL PUBLIC LICENSE Version 3"
  echo "${COLOR_RESET}"
}

HEADER
