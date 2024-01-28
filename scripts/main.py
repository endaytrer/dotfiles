#!/usr/bin/env python3
import sys
import os
import json
import subprocess
from typing import Literal, Optional, NamedTuple

Distro = Literal['archlinux', 'debian', 'ubuntu', 'fedora', 'fedora-asahi-remix', 'unknown']
# update = None means no need to update

assert len(sys.argv) == 2 and sys.argv[1] in ['archlinux', 'debian', 'ubuntu', 'fedora', 'fedora-asahi-remix'] 
distro: Distro = sys.argv[1]

print(f"\n\033[1mHello, {distro} from python!\033[0m")

# allow multiple package managers, like `pacman`/`yay` for archlinux and `apt`/`snap` for ubuntu

PMName = Literal['pacman', 'yay', 'apt', 'snap', 'dnf']
PackageManager = NamedTuple('PackageManager', [('base', str), ('sudo', bool), ('install', list[str]), ('update', Optional[list[str]])])

pms: dict[PMName, PackageManager] = {
    'pacman': PackageManager('pacman', True, ['-S', '--needed', '--noconfirm'], ['-Syu', '--needed', '--noconfirm']),
    'yay': PackageManager('yay', False, ['-S', '--needed', '--noconfirm'], ['-Syu', '--needed', '--noconfirm']),
    'apt': PackageManager('apt', True, ['install', '-y'], ['update', '-y']),
    'snap': PackageManager('snap', True, ['install', '-y'], None),
    'dnf': PackageManager('dnf', True, ['install', '-y'], ['update', '-y']),
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
avail_pms = distro_pm[distro]

def exec_success(*command) -> bool:
    return subprocess.run(command).returncode == 0

def exec_failstop(*command):
    if subprocess.run(command).returncode != 0:
        print("Failed executing " + ' '.join(command))
        exit(1)

def install_pm_raw(pm: PMName, *package: list[str]):
    if pms[pm].sudo:
        exec_failstop('sudo', pms[pm].base, *pms[pm].install, *package)
    else:
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
# if git repo is none, do exactly what is in install commands

FromSource = NamedTuple('FromSource', [('git_repo', Optional[str]), ('install_commands', list[list[str]])])
Package = NamedTuple('Package', [('canonical_name', str), ('alt_names', dict[PMName, str]), ('available', list[PMName]), ('from_source', Optional[FromSource]), ('mandatory', bool), ('enable_services', list[str])])

while True:
    preset = input("Enter the preset you would like to have (1 = minimal, 2 = server, 3 = desktop): ")
    if preset not in ['1', '2', '3']:
        print("Not in range!")
        continue
    break
preset = int(preset)

packages: list[Package] = []
packages_dir = os.path.join(home, "dotfiles/packages")
minimal_config = os.path.join(packages_dir, "minimal.json")
server_config = os.path.join(packages_dir, "server.json")
desktop_config = os.path.join(packages_dir, "desktop.json")

with open(minimal_config, 'r') as f:
    packages = json.load(f)
    
if preset >= 2:
    with open(server_config, 'r') as f:
        packages += json.load(f)
        
if preset >= 3:
    with open(desktop_config, 'r') as f:
        packages += json.load(f)

# first install PM packages, then build from source
pm_packages: dict[PMName, list[str]] = {}
build_packages: dict[str, FromSource] = {}
manual_packages: list[str] = []
enable_services: list[str] = []
for package in packages:
    find = False
    for pm in avail_pms:
        if pm in package["available"]:
            if pm not in pm_packages:
                pm_packages[pm] = []
            if pm in package["alt_names"]:
                pm_packages[pm].append(package["alt_names"][pm])
            else:
                pm_packages[pm].append(package["canonical_name"])
            find = True
            break # breaking out to next package
    if find:
        enable_services += package["enable_services"]
        continue
    
    if package["from_source"]:
        build_packages[package["canonical_name"]] = package["from_source"]  
        enable_services += package["enable_services"]   
           
    elif package['mandatory']:
        manual_packages.append(package["canonical_name"])

for pm in pm_packages:
    print(f"\n\033[1mInstalling {pm} managed packages: {' '.join(pm_packages[pm])}\033[0m")
    install_pm_raw(pm, *pm_packages[pm])

build_path = os.path.join(home, 'build')
if len(build_packages.keys()) != 0:
    if not os.path.exists(build_path):
        os.mkdir(build_path)
    
    print(f"\n\033[1mInstalling source code based packages: {' '.join(build_packages.keys())}\033[0m")

for name in build_packages:
    from_source = build_packages[name]
    repo = from_source['git_repo']
    repo_path = os.path.join(build_path, name)
    if repo is not None:
        git_clone_if_nonexist(repo, repo_path)
        os.chdir(repo_path)
        
    print(f"\n\033[1mBuilding {name}\033[0m")
    for command in from_source['install_commands']:
        exec_failstop(*command)
    os.chdir(home)

if len(manual_packages) != 0:
    print(f"\033[31;1mYou have to install these packages manually: {' '.join(manual_packages)}\033[0m")

# soft linking configs

print(f"\n\033[1mCreating configs\033[0m")
config_src_dir = os.path.join(home, 'dotfiles/config')
config_dst_dir = os.path.join(home, '.config')


if not os.path.exists(config_dst_dir):
    os.mkdir(config_dst_dir)

configs = os.listdir(config_src_dir)

# sorting the config into two destinations: in .config folder (in_config) and in home folder
# first element is name, second element is src path

in_config: list[tuple[str, str]] = []
in_home: list[tuple[str, str]] = []
for subp in configs:
    src_path = os.path.join(config_src_dir, subp)
    if os.path.isdir(src_path):
        in_config.append((subp, src_path))
    else:
        in_home.append((subp, src_path))
        
os.chdir(config_dst_dir)
for i in in_config:
    if os.path.exists(i[0]):
        exec_failstop("rm", i[0])
    exec_failstop("ln", "-s", i[1], i[0])

os.chdir(home)
for i in in_home:
    if os.path.exists(i[0]):
        exec_failstop("rm", i[0])
    exec_failstop("ln", "-sf", i[1], i[0])
    

print(f"\033[1mEnabling services\033[0m")
exec_failstop('sudo', 'systemctl', 'enable', *enable_services)


default_shell = '/bin/zsh'

print(f"\033[1mChanging default shell to {default_shell}\033[0m\n\033[31;1mYou need to input your password here:\033[0m")
exec_failstop('chsh', '-s', default_shell)

if (input("\n\033[32;1mDone! reboot now? (yN) \033[0m") == 'y'):
    subprocess.run(['sudo', 'reboot'])

exit(0)