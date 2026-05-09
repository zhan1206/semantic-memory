# Semantic Memory — Fish Shell 自动补全
# 安装方法:
#   cp shell/semantic-memory.fish ~/.config/fish/completions/
complete -c semantic-memory -f -a "add search recall list get tag importance edit delete stats forget clear encrypt unlock kb import import-dir config metrics"

complete -c semantic-memory -n "__fish_seen_subcommand_from kb" -f -a "create list add query delete"
complete -c semantic-memory -n "__fish_seen_subcommand_from config" -f -a "get set reset"

# 选项补全
complete -c semantic-memory -l tags -d "标签，逗号分隔"
complete -c semantic-memory -l importance -d "重要性 0.0-1.0"
complete -c semantic-memory -l top-k -d "返回结果数量"
complete -c semantic-memory -l tag -d "按标签过滤"
complete -c semantic-memory -l kb -d "知识库名称"
complete -c semantic-memory -l max-chars -d "上下文最大字符数"
complete -c semantic-memory -l limit -d "限制数量"
complete -c semantic-memory -l sort -d "排序方式 (timestamp|importance)"
complete -c semantic-memory -l confirm -d "确认操作"
complete -c semantic-memory -l apply -d "实际执行遗忘"
complete -c semantic-memory -l desc -d "知识库描述"

# 文件路径补全（用于 import）
complete -c semantic-memory -n "__fish_seen_subcommand_from import; or __fish_seen_subcommand_from import-dir; or __fish_seen_subcommand_from add" -f -a "(__fish_complete_readable)"
