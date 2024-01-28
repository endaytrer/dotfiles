#!/usr/bin/env python3
import sys
import os
import subprocess
from typing import Literal, Optional, NamedTuple

Distro = Literal['archlinux', 'debian', 'ubuntu', 'fedora', 'fedora-asahi-remix', 'unknown']
# update = None means no need to update

assert len(sys.argv) == 2 and sys.argv[1] in ['archlinux', 'debian', 'ubuntu', 'fedora', 'fedora-asahi-remix'] 
distro: Distro = sys.argv[1]

print(f"Hello, {distro} from python!")

# allow multiple package managers, like `pacman`/`yay` for archlinux and `apt`/`snap` for ubuntu

PMName = Literal['pacman', 'yay', 'apt', 'snap', 'dnf']
PackageManager = NamedTuple('PackageManager', [('base', str), ('install', list[str]), ('update', Optional[list[str]])])

pms: dict[PMName, PackageManager] = {
    'pacman': PackageManager('pacman', ['-S', '--needed', '--noconfirm'], ['-Syu', '--needed', '--noconfirm']),
    'yay': PackageManager('yay', ['-S', '--needed', '--noconfirm'], ['-Syu', '--needed', '--noconfirm']),
    'apt': PackageManager('apt', ['install', '-y'], ['update', '-y']),
    'snap': PackageManager('snap', ['install', '-y'], None),
    'dnf': PackageManager('dnf', ['install', '-y'], ['update', '-y']),
}

home = os.environ['HOME']

# prefer former PM
distro_pm: dict[Distro, list[str]] = {
    'archlinux': ['pacman', 'yay'],
    'debian': ['apt'],
    'ubuntu': ['apt', 'snap'],
    'fedora': ['dnf'],
    'fedora-asahi-remix': ['dnf'],
    'unknown': []
}

def exec_success(*command) -> bool:
    return subprocess.run(command).returncode == 0

def exec_failstop(*command):
    if subprocess.run(command).returncode != 0:
        print("Failed executing " + ' '.join(command))
        exit(1)

def install_pm_raw(pm: PMName, *package: list[str]):
    exec_failstop(pms[pm].base, *pms[pm].install, *package)

def git_clone_if_nonexist(url: str, path: str):
    if os.path.exists(path):
        return
    exec_failstop('git', 'clone', url, path)
    
# if archlinux, install yay before start
if distro == 'archlinux' and not exec_success('yay', '-v'):
    print("Yay does not exist, installing yay...")

    install_pm_raw('pacman', 'base-devel')
    git_clone_if_nonexist('https://aur.archlinux.org/yay.git', 'yay')
    os.chdir('yay')
    exec_failstop('makepkg', '-si')
    os.chdir(home)

# start installing packages
FromSource = NamedTuple('FromSource', [('git_repo', Optional[str]), ('install_commands', list[list[str]])])
Package = NamedTuple('Package', [('canonical_name', str), ('alt_names', dict[PMName, str]), ('available', list[PMName]), ('from_source', Optional[FromSource]), ('mandatory', bool)])

Preset = Literal['minimal', 'server', 'desktop']
required_packages: list[Package] = []
distro_specific_packages: dict[Distro, list[Package]] = {}