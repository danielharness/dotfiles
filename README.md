### My dotfiles repository

Managed using [yadm](https://github.com/TheLocehiliosan/yadm).

Includes an [ansible](https://github.com/ansible/ansible) playbook that sets up a clean ubuntu machine.

### Features:
- Installs useful packages from 3 package managers (apt, homebrew, snap)
- Sets up [oh-my-zsh](https://github.com/ohmyzsh/ohmyzsh) as the default shell
- Sets up [zellij](https://github.com/zellij-org/zellij) as the terminal multiplexer
- Sets up terminal themes and fonts

### Usage:
```bash
# Set up dotfiles
yadm clone "https://github.com/danielharness/dotfiles.git"
# Install / update packages
yadm bootstrap
```
