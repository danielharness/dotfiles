# Set oh-my-zsh install directory
export ZSH=$HOME/.oh-my-zsh

# Set homebrew environment
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
# Add homebrew completion functions
FPATH="$(brew --prefix)/share/zsh/site-functions:${FPATH}"

# Hyphen-insensitive completion, makes '_' and '-'' interchangeable
HYPHEN_INSENSITIVE="true"

# Update oh-my-zsh automatically every 14 days
zstyle ':omz:update' mode auto
zstyle ':omz:update' frequency 14

# Plugins
plugins=(
    alias-finder
    fzf
    git
    starship
)

# Configure plugins
zstyle ':omz:plugins:alias-finder' autoload yes
zstyle ':omz:plugins:alias-finder' longer yes
zstyle ':omz:plugins:alias-finder' exact yes
zstyle ':omz:plugins:alias-finder' cheaper yes

# Load oh-my-zsh
source $ZSH/oh-my-zsh.sh


# ----------------------------
# ---- User configuration ----
# ----------------------------

# Run `zellij` if not inside it already
if [[ -z "$ZELLIJ" ]]; then
    # If there is a running session but it's in use, create a new session
    if [[ $(ps -eo command | rg -x 'zellij.*') ]]; then
        zellij
    # Otherwise try to attach to a running session, or create a new session if one does not exist
    else
        zellij attach -c
    fi
    # Exit when closed
    exit
fi
# Update `zellij` tab name on directory change
zellij_tab_name_update() {
    if [[ -n $ZELLIJ ]]; then
        tab_name=''
        if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            tab_name+=$(basename "$(git rev-parse --show-toplevel)")/
            tab_name+=$(git rev-parse --show-prefix)
            tab_name=${tab_name%/}
        else
            tab_name=$PWD
            if [[ $tab_name == $HOME ]]; then
                tab_name="~"
            else
                tab_name=${tab_name##*/}
            fi
        fi
        command nohup zellij action rename-tab $tab_name >/dev/null 2>&1
    fi
}
zellij_tab_name_update
chpwd_functions+=(zellij_tab_name_update)

# Use `bat` instead of `cat`
alias cat=bat
# Use `bat` to display man pages
export MANPAGER="sh -c 'col -bx | bat -l man -p'"
# Use `bat` to color --help of every command
alias -g -- --help='--help 2>&1 | bat --language=help --style=plain --paging=never'

# Use `eza` instead of `ls`
alias ls="eza --git --icons --classify --group-directories-first --time-style=long-iso --color-scale"
alias l="ls --long --all --header"
alias ll="l"
alias la="l"
alias llm="l --sort=modified"
alias tree="eza --tree"

# Use `dust` instead of `du`
alias du="dust"

# Use `python3` as the default
alias python="python3"
alias ipython="ipython3"


# -------------------
# ---- Keep last ----
# -------------------

# Source `zsh` plugins which aren't provided with oh-my-zsh
source "$(brew --prefix)/share/zsh-autosuggestions/zsh-autosuggestions.zsh"
source "$(brew --prefix)/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
