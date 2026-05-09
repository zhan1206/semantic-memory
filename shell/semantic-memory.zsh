#compdef semantic-memory python run.py

# Semantic Memory — Zsh 自动补全
# 安装方法:
#   cp shell/semantic-memory.zsh ~/.zsh/completions/_semantic-memory
#   autoload -U compinit && compinit
# 或
#   fpath=(~/.zsh/completions $fpath)
#   autoload -U compinit && compinit

_semantic_memory() {
    local -a commands kb_commands config_commands options

    commands=(
        "add:添加记忆"
        "search:语义搜索"
        "recall:语义召回"
        "list:列出记忆"
        "get:获取单条"
        "tag:添加标签"
        "importance:设置重要性"
        "edit:编辑内容"
        "delete:删除"
        "stats:统计信息"
        "forget:自动遗忘"
        "clear:清空"
        "encrypt:加密"
        "unlock:解锁"
        "kb:知识库操作"
        "import:导入文件"
        "import-dir:批量导入"
        "config:配置管理"
        "metrics:性能指标"
    )

    kb_commands=(
        "create:创建知识库"
        "list:列出知识库"
        "add:添加文档"
        "query:查询知识库"
        "delete:删除知识库"
    )

    config_commands=(
        "get:获取配置"
        "set:设置配置"
        "reset:重置配置"
    )

    options=(
        "--tags:标签"
        "--importance:重要性"
        "--top-k:结果数量"
        "--tag:按标签过滤"
        "--kb:知识库名"
        "--max-chars:最大字符数"
        "--limit:限制数量"
        "--sort:排序方式"
        "--confirm:确认操作"
        "--apply:实际执行"
        "--desc:描述"
    )

    _describe 'command' commands
    _describe 'kb-command' kb_commands
    _describe 'config-command' config_commands
    _describe 'option' options

    case "$words[1]" in
        kb)
            _describe 'kb-command' kb_commands
            ;;
        config)
            _describe 'config-command' config_commands
            ;;
    esac
}

# 文件路径补全
_semantic_memory_files() {
    _files
}

compdef _semantic_memory_files semantic-memory
compdef _semantic_memory_files run.py
compdef _semantic_memory_files python

# import 命令的文件补全
_semantic_memory_import() {
    local -a commands
    commands=("add" "import" "import-dir")
    if [[ "${words[1]}" == "import" || "${words[1]}" == "import-dir" ]]; then
        _files
    else
        _describe 'command' commands
    fi
}
compdef _semantic_memory_import semantic-memory
compdef _semantic_memory_import run.py
compdef _semantic_memory_import python
