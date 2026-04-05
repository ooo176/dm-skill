# dm-skill

面向 **达梦（DM / Dameng）** 数据库的 **Cursor / Agent Skill**：在对话中通过校验后的 **只读 SQL** 探查数据与元数据，**不支持**插入、更新、删除或 DDL。

## 功能

- 自定义 **SELECT / WITH / EXPLAIN / SHOW / DESC / DESCRIBE** 类查询
- 脚本层 **关键字与首词校验**，拦截 `INSERT`、`UPDATE`、`DELETE`、`MERGE`、DDL、`CALL`/`EXEC` 等
- 查询结果以 **JSON** 输出，便于 Agent 解析与汇总
- 默认限制返回行数，降低大结果集风险

## 仓库结构

```
dm-skill/
├── SKILL.md              # Agent 主指令（必读）
├── reference.md          # 退出码、JSON 字段、校验说明
├── README.md             # 本文件
├── requirements.txt      # Python 依赖
└── scripts/
    └── dm_query.py       # 只读查询 CLI
```

## 环境要求

- Python 3.9+（建议与运行 Agent 终端一致）
- [dmPython](https://pypi.org/project/dmpython/)（版本尽量与 DM 服务器匹配；无法 `pip` 安装时，请使用达梦官方安装包中的 whl）

```bash
pip install -r requirements.txt
```

## 连接配置

在运行脚本的 shell 中配置（**勿**把密码写入仓库或提交 Git）。

**分项变量：**

```bash
export DM_USER="SYSDBA"
export DM_PASSWORD="你的密码"
export DM_HOST="127.0.0.1"
export DM_PORT="5236"
# 可选
export DM_SCHEMA="YOUR_SCHEMA"
export DM_MAX_ROWS="500"
```

**或 DSN：**

```bash
export DM_DSN="SYSDBA/your_password@localhost:5236/SCH1"
```

生产环境建议使用 **仅 SELECT 权限** 的账号。

## 命令行用法

将 `{ROOT}` 换为本仓库根目录（含 `SKILL.md` 的目录）。

```bash
# 执行查询（stdout 为 JSON）
python3 {ROOT}/scripts/dm_query.py --sql "SELECT * FROM DUAL" --max-rows 100

# 从文件读取 SQL
python3 {ROOT}/scripts/dm_query.py --file ./query.sql --max-rows 500

# 仅校验 SQL，不连库
python3 {ROOT}/scripts/dm_query.py --validate-only --sql "SELECT 1 FROM DUAL"
```

## 作为 Cursor Skill 安装

将本仓库（或复制后的目录）放到个人或项目 skills 目录，并保证 **`SKILL.md` 位于该 skill 目录的根一级**，例如：

- 个人：`~/.cursor/skills/dm-database-readonly/SKILL.md`
- 项目：`<repo>/.cursor/skills/dm-database-readonly/SKILL.md`

安装后，在对话中提到「达梦 / DM / 只读查询」等，Agent 可按 `SKILL.md` 调用 `scripts/dm_query.py`。

若使用 Claude Code 且已设置 `CLAUDE_SKILL_DIR`，路径可写为 `"${CLAUDE_SKILL_DIR}/scripts/dm_query.py"`（以你的实际目录名为准）。

## SQL 规则摘要

详细列表以 `SKILL.md` 与 `scripts/dm_query.py` 为准。

- 允许：以 `SELECT`、`WITH`、`EXPLAIN`、`SHOW`、`DESC`、`DESCRIBE` 开头
- 禁止：写操作相关关键字、`CALL`/`EXEC`、事务控制、多语句等
- 大表请用 `WHERE`、分页或字典表缩小范围；注意 `fetchall` 对极大结果集的内存占用

## 安全提示

- 凭证只放在环境变量或私密配置中
- 对用户提供的 SQL 仍需谨慎（性能与敏感列脱敏）
- 本工具为 **只读辅助**，不能替代数据库审计与权限治理

## 更多信息

- Agent 行为与流程： [SKILL.md](SKILL.md)
- 输出与边界说明： [reference.md](reference.md)
