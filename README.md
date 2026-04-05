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

### CPU 架构（ARM 与 dmPython）

**ARM / AArch64（如 Apple Silicon、鲲鹏、飞腾等）上，本仓库的 Python 脚本暂不支持连接数据库**：达梦 **dmPython** 目前无官方 ARM 预编译包，`dm_query.py` 在检测到 ARM 时会拒绝连库（退出码 `2`），并提示改用 x86_64/amd64 环境或使用 **达梦 JDBC** 等 Java 客户端在 ARM 上访问。

**仍可在 ARM 上使用** `python3 scripts/dm_query.py --validate-only ...` 做 SQL 规则校验（不加载 dmPython、不连库）。

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

## Claude Code Skill

仓库克隆到 **`.claude/skills/`** 下后，目录内应直接可见 **`SKILL.md`**（与 `scripts/` 同级）。以下命令默认使用本仓库地址；若你使用 fork，请把 URL 换成自己的。

### 个人（全局）安装

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/ooo176/dm-skill.git ~/.claude/skills/dm-skill
```

### 项目内安装

在目标项目根目录执行：

```bash
mkdir -p .claude/skills
git clone https://github.com/ooo176/dm-skill.git .claude/skills/dm-skill
```

**重启 Claude Code** 后，Skill 会自动加载。

安装完成后，在运行查询的终端里安装依赖并配置 [连接配置](#连接配置)（`pip install -r .../requirements.txt`、导出 `DM_DSN` 或 `DM_USER` 等）。**ARM 架构**下 dmPython 连库限制见 [CPU 架构](#cpu-架构arm-与-dmpython)。

可选：设置环境变量 **`CLAUDE_SKILL_DIR`** 指向 Skill 根目录（例如 `~/.claude/skills/dm-skill`），便于统一书写脚本路径：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/dm_query.py" --sql "SELECT * FROM DUAL"
```

---

## Cursor Skill

将本仓库放到 **`.cursor/skills/`** 下，保证 **`SKILL.md` 位于该 Skill 目录的根一级**（与 `scripts/` 同级）。

### 个人（全局）安装

```bash
mkdir -p ~/.cursor/skills
git clone https://github.com/ooo176/dm-skill.git ~/.cursor/skills/dm-skill
```

（Windows：可将 `~` 换为 `%USERPROFILE%`，路径形如 `%USERPROFILE%\.cursor\skills\dm-skill`。）

### 项目内安装

在目标项目根目录执行：

```bash
mkdir -p .cursor/skills
git clone https://github.com/ooo176/dm-skill.git .cursor/skills/dm-skill
```

**重启 Cursor**（或执行「Developer: Reload Window」）后，Agent 即可按 Skills 规则加载；若未生效，请在 Cursor 设置中确认 Skills 目录与文档版本一致。

依赖与达梦连接：在 **集成终端** 中完成 `pip install` 与 [连接配置](#连接配置）。**ARM 架构**说明见 [CPU 架构](#cpu-架构arm-与-dmpython)。

对话中提及「达梦 / DM / 只读查询」等时，Agent 会按 `SKILL.md` 调用说明与 `scripts/dm_query.py`。

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
