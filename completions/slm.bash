# Bash completion for slm command
# Source this file or copy to /usr/local/etc/bash_completion.d/

_slm_completions() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Main commands
    local main_commands="remember recall list status context profile graph patterns reset help version"

    # Profile subcommands
    local profile_commands="list create switch delete current"

    # Graph subcommands
    local graph_commands="build stats"

    # Pattern subcommands
    local pattern_commands="update list context"

    # Reset subcommands
    local reset_commands="soft hard layer"

    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${main_commands}" -- ${cur}) )
        return 0
    fi

    case "${COMP_WORDS[1]}" in
        profile)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                COMPREPLY=( $(compgen -W "${profile_commands}" -- ${cur}) )
            fi
            return 0
            ;;
        graph)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                COMPREPLY=( $(compgen -W "${graph_commands}" -- ${cur}) )
            fi
            return 0
            ;;
        patterns)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                COMPREPLY=( $(compgen -W "${pattern_commands}" -- ${cur}) )
            fi
            return 0
            ;;
        reset)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                COMPREPLY=( $(compgen -W "${reset_commands}" -- ${cur}) )
            fi
            return 0
            ;;
    esac
}

complete -F _slm_completions slm
