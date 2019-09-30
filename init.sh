#!/bin/bash
echo "--------------------------------------------"
echo "Customized Pacman Core Software"
echo "--------------------------------------------"
echo ""
echo "Synchronising packages..."
echo "Synchronizing programing languages..."
sudo pacman --needed -S jdk11-openjdk python php
echo "Synchronizing administration tools..."
sudo pacman --needed -S htop tree git base-devel yay make gcc cmake
echo "Synchronizing office tools..."
sudo pacman --needed -S chromium gimp
echo "Synchronizing communication tools..."
yay pacman --needed -S slack-desktop skypeforlinux-stable-bin
echo "Synchronizing development tools..."
echo "Synchronizing visualization tools..."
sudo pacman --needed -S dia
echo "Synchronizing IDE's..."
sudo pacman --needed -S eclipse-java dia atom
echo "Installing atom packages..."
apm install -c \
	atom-ide-ui\
	ide-bash\
	ide-python\
	ide-c-cpp\
	ide-java\
	ide-yaml\
	atom-autocomplete-php\
	es6-snippets\
	javascript-snippets\
	emmet\
	git-blame\
	git-plus\
	script\
	ask-stack\
	atom-beautify\
	highlight-selected\
	autocomplete-paths\
	todo-show\
	docblockr\
npm i -g bash-language-server #Needed by atom-package ide-bash
echo "Synchronizing containerization tools..."
sudo pacman --needed -S docker
echo "Synchronizing orchestration tools..."
sudo pacman --needed -S ansible
echo "Add current user($USER) to user group docker..."
usermod -a -G docker $USER
echo "Synchronizing games..."
sudo pacman --needed -S 0ad warzone2100
#yay pacman --needed -S emulationstation
echo "More game recomendations you will find here: https://wiki.archlinux.org/index.php/List_of_games..."
echo "More software recomendations you will find here: https://wiki.archlinux.org/index.php/list_of_applications"
