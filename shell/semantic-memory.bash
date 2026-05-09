#!/bin/bash
# Semantic Memory — Bash 自动补全
# 安装方法:
#   cp shell/semantic-memory.bash /etc/bash_completion.d/
#   source ~/.bashrc
# 或
#   echo 'source /path/to/shell/semantic-memory.bash' >> ~/.bashrc

_semantic_memory() {
    local cur prev words cword
    _init_completion || return

    local commands=(
        "add" "search" "recall" "list" "get"
        "tag" "importance" "edit" "delete"
        "stats" "forget" "clear"
        "encrypt" "unlock"
        "kb" "import" "import-dir"
        "config" "metrics"
    )

    local kb_commands="create list add query delete"
    local config_commands="get set reset"
    local options=(
        "--tags" "--importance" "--top-k" "--tag"
        "--kb" "--max-chars" "--limit" "--sort"
        "--confirm" "--apply" "--desc"
    )

    # 子命令补全
    if [[ ${#words[@]} -ge 2 ]]; then
        case "${words[1]}" in
            kb)
                COMPREPLY=($(compgen -W "$kb_commands" -- "$cur"))
                return
                ;;
            config)
                COMPREPLY=($(compgen -W "$config_commands" -- "$cur"))
                return
                ;;
        esac
    fi

    # 主命令补全
    if [[ $cword -eq 1 ]]; then
        COMPREPLY=($(compgen -W "${commands[*]}" -- "$cur"))
        return
    fi

    # 选项补全
    if [[ "$cur" == --* ]]; then
        COMPREPLY=($(compgen -W "${options[*]}" -- "$cur"))
        return
    fi

    # 文件路径补全（用于 import）
    if [[ "${words[1]}" == "import" || "${words[1]}" == "import-dir" || "${words[1]}" == "add" ]]; then
        _filedir
        return
    fi
}

complete -F _semantic_memory semantic-memory
complete -F _semantic_memory python
complete -F _semantic_memory run.py
