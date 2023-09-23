# Set oh-my-zsh install directory
export ZSH=$HOME/.oh-my-zsh

# Set homebrew environment
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

# Hyphen-insensitive completion, makes '_' and '-'' interchangeable
HYPHEN_INSENSITIVE="true"

# Update oh-my-zsh automatically every 14 days
zstyle ':omz:update' mode auto
zstyle ':omz:update' frequency 14

# Display dots while waiting for completion
COMPLETION_WAITING_DOTS="true"

# Plugins
plugins=(
    fzf
    git
    starship
)

# Load oh-my-zsh
source $ZSH/oh-my-zsh.sh


# --- User configuration ---



