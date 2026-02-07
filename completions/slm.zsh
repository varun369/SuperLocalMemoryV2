#compdef slm
# Zsh completion for slm command
# Copy to a directory in $fpath or source directly

_slm() {
    local -a main_commands profile_commands graph_commands pattern_commands reset_commands

    main_commands=(
        'remember:Save content to memory'
        'recall:Search memories'
        'list:List recent memories'
        'status:System status'
        'context:Project context'
        'profile:Manage profiles'
        'graph:Knowledge graph operations'
        'patterns:Pattern learning'
        'reset:Reset operations'
        'help:Show help'
        'version:Show version'
    )

    profile_commands=(
        'list:List all profiles'
        'create:Create new profile'
        'switch:Switch to profile'
        'delete:Delete profile'
        'current:Show current profile'
    )

    graph_commands=(
        'build:Build/rebuild knowledge graph'
        'stats:Show graph statistics'
    )

    pattern_commands=(
        'update:Learn patterns from memories'
        'list:List learned patterns'
        'context:Get coding identity context'
    )

    reset_commands=(
        'soft:Soft reset (clear memories)'
        'hard:Hard reset (nuclear option)'
        'layer:Layer-specific reset'
    )

    if (( CURRENT == 2 )); then
        _describe 'slm commands' main_commands
        return
    fi

    case "$words[2]" in
        profile)
            if (( CURRENT == 3 )); then
                _describe 'profile commands' profile_commands
            fi
            ;;
        graph)
            if (( CURRENT == 3 )); then
                _describe 'graph commands' graph_commands
            fi
            ;;
        patterns)
            if (( CURRENT == 3 )); then
                _describe 'pattern commands' pattern_commands
            fi
            ;;
        reset)
            if (( CURRENT == 3 )); then
                _describe 'reset commands' reset_commands
            fi
            ;;
    esac
}

_slm "$@"
