#!/bin/bash

clear
echo -e "\033[94;1m" '
    _            _      _                                                             _                               _     
 \_|_)          | |  o |/                /                o    |                     | |                             | |    
   |     __     | |    |     _  o _  _|_ _    __             __|   __    _  _  _|_   | |  _      _   _           _   | |  _ 
  _|    /  |    |/  /| |/ \_|/  /  |  | |/   /  | /|   |  | /  |  /  |  / |/ |  |    |/  |/    |/ \_|/  |   |  |/ \__|/  |/ 
\(/\___/\_/|_  /|__/ |_/\_/ |__/   |_ |_|__  \_/|/  \_/|_/|_\_/|_/\_/|_/  |  |_ |_  /|__/|__   |__/ |__/ \_/|_/|__/  |__/|__
                                               /|                                             /|              /|            
                                               \|                                             \|              \|            
' "\033[0m"

echo -e "\033[1mDaniel Gu dotfiles\033[0m"

# Testing distro
echo -n "Testing distro..." 

DISTRO_NAME=`cat /etc/os-release | grep -E '^NAME="(.*)"$' | sed 's/^NAME="\(.*\)"$/\1/'`

echo ${DISTRO_NAME}

# Supporting arch, debian and ubuntu

if [ "${DISTRO_NAME}" = 'Arch Linux' ]; then
    DISTRO="archlinux"
    PACKAGE_MANAGER="pacman"
    PM_UPDATE="-Syu --noconfirm"
    PM_INSTALL="-S --noconfirm"
elif [ "${DISTRO_NAME}" = 'Debian GNU/Linux' ]; then
    DISTRO="debian"
    PACKAGE_MANAGER="apt"
    PM_UPDATE="update -y"
    PM_INSTALL="install -y"
elif [ "${DISTRO_NAME}" = 'Ubuntu' ]; then
    DISTRO="ubuntu"
    PACKAGE_MANAGER="apt"
    PM_UPDATE="update -y"
    PM_INSTALL="install -y"
elif [ "${DISTRO_NAME}" = 'Fedora Linux' ]; then
    DISTRO="fedora"
    PACKAGE_MANAGER="dnf"
    PM_UPDATE="update -y"
    PM_INSTALL="install -y"
elif [ "${DISTRO_NAME}" = "Fedora Linux Asahi Remix" ]; then
    DISTRO="fedora-asahi-remix"
    PACKAGE_MANAGER="dnf"
    PM_UPDATE="update -y"
    PM_INSTALL="install -y"
else
    DISTRO="unknown"
fi

if [ $DISTRO = 'unknown' ]; then
    echo "Cannot determine your operating system! "
    read -p "You have to download dependencies manually. Continue? (yN) " confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] || exit 1
fi
# Test sudo and privilege
echo -n "Testing whether you have sudo privileges..."
if sudo -V > /dev/null; then
    if sudo -v > /dev/null; then
        echo "yes"
    else
        echo "You don't have sudo privileges. Please acquire it and continue."
        exit 1
    fi
else
    echo "You don't have sudo installed. Please contact your supervisor to install it."
    exit 1
fi
NEED_INSTALL=""
echo -n "Testing if python3 is present..."
# install python first so that I don't have to suffer from bash if python3 -V > /dev/null; then echo "yes"
if python3 -V > /dev/null; then
    echo "yes"
else
    echo "no"
    NEED_INSTALL="$NEED_INSTALL python3"
fi

# should have curl after running this script, but test anyway.
echo -n "Testing if curl is present..."
if curl -V > /dev/null; then
    echo "yes"
else
    echo "no"
    NEED_INSTALL="$NEED_INSTALL curl"
fi
echo -n "Testing if git is present..."
if git -v > /dev/null; then
    echo "yes"
else
    echo "no"
    NEED_INSTALL="$NEED_INSTALL git"
fi
echo "updating package manager..."
sudo $PACKAGE_MANAGER $PM_UPDATE

if [ "$NEED_INSTALL" != "" ]; then
    echo "install missing dependencies..."
    sudo $PACKAGE_MANAGER $PM_INSTALL $NEED_INSTALL
fi

cd $HOME

# no changing branch by default, make sure to merge branch to main
if [ ! -d "$HOME/dotfiles" ]; then
    git clone https://github.com/endaytrer/dotfiles.git "$HOME/dotfiles"
fi

python3 $HOME/dotfiles/scripts/main.py $DISTRO
