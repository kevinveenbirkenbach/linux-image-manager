#!/bin/bash
# @author Kevin Veen-Birkenbach
# shellcheck disable=SC2015  # Deactivating bool hint
# shellcheck source=/dev/null # Deactivate SC1090
# shellcheck disable=SC2005 # Deactivate wrong shellcheck interpretation
# shellcheck disable=SC2086  # Deactivating escaping warning, because it's wrong concerning pacman_packages
source "$(dirname "$(readlink -f "${0}")")/../base.sh" || (echo "Loading base.sh failed." && exit 1)

get_packages(){
  for package_collection in "$@"
  do
    echo "$(sed -e "/^#/d" -e "s/#.*//" "$PACKAGE_PATH""$package_collection.txt" | tr '\n' ' ')" || error "Loading package wasn't possible."
  done
}

install_yay_packages_if_needed(){
	info "Checking yay packages [ $1 ]..."
	for package in $1; do
		if [ "$(pacman -Qi "$package" 2> /dev/null)" ]; then
			info "Package \"$package\" is allready installed. Skipped installation."
		else
			info "Install package \"$package\" with yay..." &&
			yay -S "$package" || error "Failed to install package \"$package\"."
		fi
	done
}

info "Start setup of customized core software..."

info "Copying templates to home folder..." &&
cp -rfv "$TEMPLATE_PATH/." "$HOME" || error "Copy templates failed."

info "Update packages..." &&
sudo pacman -Syyu || error "Package syncronisation failed."

pacman_packages="$(get_packages "general" "client/pacman/general")"
info "Synchronizing pacman packages [$pacman_packages]..." &&
sudo pacman -S --needed $pacman_packages || error "Syncronisation failed."

info "Synchronizing yay packages..." &&
install_yay_packages_if_needed "$(get_packages "client/yay/general")";

FSTAB_SWAP_ENTRY="/swapfile none swap defaults 0 0"
SWAP_FILE="/swapfile"
FSTAB_FILE="/etc/fstab"
if grep -q "$FSTAB_SWAP_ENTRY" "$FSTAB_FILE"; then
	info "Skipping creation of swap partion because entry allready exists in \"$FSTAB_FILE\"!"
else
	info "Creating swap partition..." &&
	sudo fallocate -l 16G "$SWAP_FILE" &&
	sudo chmod 600 "$SWAP_FILE" &&
	sudo mkswap "$SWAP_FILE" &&
	sudo swapon "$SWAP_FILE" &&
	sudo sh -c "echo \"$FSTAB_SWAP_ENTRY\">>\"$FSTAB_FILE\"" || error "Creation of swap partition failed."
fi

info "Setup SSH key..."
ssh_key_path="$HOME/.ssh/id_rsa"
if [ ! -f "$ssh_key_path" ]; then
	info "SSH key $ssh_key_path doesn't exists!"
	if [ ! -f "./data$ssh_key_path" ]; then
		info "Importing ssh key by copying data..." &&
		bash "$SCRIPT_PATH""/data/export-to-system.sh" || error "Copying failed."
	else
		info "Generating ssh key..." &&
		ssh-keygen -t rsa -b 4096 -C "$USER@$HOSTNAME" || error "Key generation failed."
	fi
fi

info "Installing nonfree drivers..." &&
sudo mhwd -a pci nonfree 0300 || error "Failed."

info "Setup, configuration and installation of dependencies for installed software..."

if pacman -Qi "arduino" > /dev/null ; then
	info "Configurate system for arduino..." &&
	sudo usermod -a -G uucp "$USER" &&
	sudo usermod -a -G lock "$USER" || error "Couldn't add \"$USER\" to the relevant groups."
fi

if pacman -Qi "atom" > /dev/null ; then
	info "Installing atom dependencies..."
	info "Installing \"apm\" packages..." &&
	get_packages "client/apm/general" | apm install --verbose -c - || error "Failed."
	info "Installing \"npm\" packages..." &&
	sudo npm i -g bash-language-server &&
	info "Installing \"python\" packages..." &&
	python -m pip install 'python-language-server[all]' &&
	info "Installing atom dependencies was successfull."|| error " Installing atom dependencies failed."
fi

if pacman -Qi "docker" > /dev/null ; then
	info "Setting up docker..." &&
	info "Add current user \"$USER\" to user group docker..." &&
	sudo usermod -a -G docker "$USER" || error "Failed to add user."
	info "Restarting docker service..." &&
	sudo systemctl restart docker &&
	info "Disable and stop docker service..." &&
	sudo systemctl disable --now docker || error "\"systemctl\" produced an error."
	info "For performance reasons docker is not enabled. Start docker by executing \"sudo systemctl restart docker\" when you need it."
fi

if [ ! "$(pacman -Qi "virtualbox")" ] ; then
	info "Setting up virtualbox..." &&
	pamac install virtualbox "$(pacman -Qsq "^linux" | grep "^linux[0-9]*[-rt]*$" | awk '{print $1"-virtualbox-host-modules"}' ORS=' ')" &&
	sudo vboxreload &&
	pamac build virtualbox-ext-oracle &&
	sudo gpasswd -a "$USER" vboxusers || error "Failed."
	info "Keep in mind to install the guest additions in the virtualized system. See https://wiki.manjaro.org/index.php?title=VirtualBox"
fi

if [ "$XDG_SESSION_TYPE" == "x11" ]; then
	info "Synchronizing xserver tools..." &&
	sudo pacman --needed -S xbindkeys &&
	xbindkeys --poll-rc || error "Failed."
fi

install_gnome_extension(){
	info "Install GNOME extension \"$1\"..."
	extension_folder="$HOME/.local/share/gnome-shell/extensions/$1/"
	if [ -d "$extension_folder" ];
		then
			if [ -d "$extension_folder"".git" ];
				then
					warning "Found a .git repository didn't expect to find this here." &&
					info "Pulling changes from git..." &&
					(cd "$extension_folder" && git pull) || error "Failed."
			else
				info "No git repository. Extension will not be updated."
			fi
		else
			info "Install..." &&
			git clone "$2" "$extension_folder" || error "Failed."
	fi

	if [ -f "$extension_folder""Makefile" ];
		then

			tmp_extension_folder="/tmp/$1"
			mv "$extension_folder" "$tmp_extension_folder"
			info "Compilling extension.."
			(cd "$tmp_extension_folder" && make install) || error "Compilation with failed."

			info "Cleaning up tmp-extension folder..."&&
			rm -fr "$tmp_extension_folder" || error "Failed."

		else
			info "No Makefile found. Skipping compilation..."
	fi

	info "Activating GNOME extension \"$1\"..." &&
	gnome-extensions enable "$1" || error "Failed."
}

if [ "$DESKTOP_SESSION" == "gnome" ]; then
	info "Synchronizing gnome tools..." &&
	sudo pacman --needed -S gnome-shell-extensions gnome-terminal &&
	info "Setting up gnome dash favourites..." &&
	gsettings set org.gnome.shell favorite-apps "['org.gnome.Nautilus.desktop',
	'org.gnome.Terminal.desktop',
	'org.keepassxc.KeePassXC.desktop',
	'firefox.desktop',
	'chromium.desktop',
	'atom.desktop',
	'arduino.desktop',
	'eclipse.desktop',
	'vlc.desktop',
	'gimp.desktop',
	'blender.desktop',
	'rhythmbox.desktop',
	'org.gnome.Screenshot.desktop']" || error "Failed."

	info "Install GNOME extensions..." &&
	install_gnome_extension "nasa_apod@elinvention.ovh" "https://github.com/Elinvention/gnome-shell-extension-nasa-apod.git"
	install_gnome_extension "dash-to-panel@jderose9.github.com" "https://github.com/home-sweet-gnome/dash-to-panel"
	info "Deactivating \"Dash to Dock\"..." &&
	gnome-extensions disable dash-to-dock@micxgx.gmail.com || error "Failed."

fi

info "Testing if computer has more then 4GB of memory to process games..." &&
if [ "$(echo "( $(grep MemTotal /proc/meminfo | awk '{print $2}') / (1024 ^ 2) ) > 4" | bc -l)" = "1" ];
	then
		pacman_game_packages="$(get_packages "client/pacman/games")"
		yay_game_packages="$(get_packages "client/yay/games")"
		success "Ok" &&
		info "Installing games..." &&
		info "Installing yay packages [ $yay_game_packages ]..." &&
		install_yay_packages_if_needed "$yay_game_packages" &&
		info "Installing pacman packages [ $pacman_game_packages ]..." &&
		sudo pacman -S --needed "$(get_packages "client/pacman/games")" || error "Syncronisation failed.";
	else
		warning "Not enough ressources." &&
		info "Skipping game installation";
fi

info "Removing all software from user startup..."
autostart_folder="$HOME/.config/autostart/"
if [ "$(ls -A "$autostart_folder")" ]
	then
		(rm "$autostart_folder"* && info "Startups had been removed.") || error "Removing startup software failed."
	else
		info "No startup entries found. Skipped removing."
fi

info "Showing the installed Java versions..." &&
archlinux-java status &&
info "Keep in mind to set the right Java-Version if it's neccessary." ||
error "Failed."

info "Please restart the computer, so that all updates get applied."
success "Setup finished successfully :)" && exit 0
