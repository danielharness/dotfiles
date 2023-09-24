### My dotfiles repository!

Managed using [yadm](https://github.com/TheLocehiliosan/yadm).

Includes an `install.py` script that endeavors to fully set up a clean ubuntu machine.

### Features:
- Installs useful packages from 4 package managers (apt, homebrew, pip, snap)
- Sets up [oh-my-zsh](https://github.com/ohmyzsh/ohmyzsh) as the default shell
- Sets up [hyper-snazzy](https://github.com/tobark/hyper-snazzy-gnome-terminal) as the terminal theme
- Sets up [zellij](https://github.com/zellij-org/zellij) as the terminal multiplexer

### Usage:
```bash
# Initial setup
yadm clone "https://github.com/danielharness/dotfiles.git"
# Install / update
yadm bootstrap
```
