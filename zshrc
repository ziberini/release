parse_git_branch() {
    git branch 2> /dev/null | sed -n -e 's/^\* \(.*\)/[\1]/p'
}

COLOR_DEF=$'\e[0m'
COLOR_USR=$'\e[38;5;243m'
COLOR_DIR=$'\e[38;5;195m'  # Light Cyan
COLOR_GIT=$'\e[38;5;39m'
NEWLINE=$'\n'

setopt PROMPT_SUBST
export PROMPT='${COLOR_DIR}%~ ${COLOR_GIT}$(parse_git_branch)${COLOR_DEF}%% '

autoload -Uz compinit && compinit
