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

## 接入 Cursor

1. **放置目录**：把整个 `dm-skill` 仓库（或复制后的文件夹）放进 Cursor 的 skills 目录，使 **`SKILL.md` 与 `scripts/` 在同一层**，即该 skill 的根目录下直接可见 `SKILL.md`。
   - **个人（全局）**：`~/.cursor/skills/<任意目录名>/`（Windows：`%USERPROFILE%\.cursor\skills\<任意目录名>\`）
   - **仅当前项目**：`<你的项目>/.cursor/skills/<任意目录名>/`
2. **依赖与连接**：Agent 执行脚本时用的是**集成终端**里的环境，请在该终端（或 shell 配置）里已能成功 `pip install` **dmPython**，并导出 [连接配置](#连接配置) 中的 `DM_*` 变量（或 `DM_DSN`）。若为 **ARM 架构**，请阅上文 [CPU 架构](#cpu-架构arm-与-dmpython)；连库查询需 x86_64 或改用 JDBC。
3. **使用方式**：在对话里提到「达梦 / DM / 只读查询」等，Agent 会按 `SKILL.md` 用 `Read` 读说明、用终端运行 `python3 .../scripts/dm_query.py`。若 Agent 找不到脚本，把本仓库绝对路径写进对话或项目规则中即可。

## 接入 Claude Code

1. **放置目录**：同样保持仓库结构不变，**skill 根目录** = 含有 `SKILL.md` 的那一层（与 `scripts/` 同级）。将这一层目录放到 Claude Code 要求的 skills 位置（以你当前 Claude Code 版本的文档为准：个人目录或项目内 `.claude` / skills 约定）。
2. **环境变量 `CLAUDE_SKILL_DIR`（推荐）**：指向上述 **skill 根目录**，这样在说明或脚本里可统一写：
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/dm_query.py" --sql "SELECT * FROM DUAL"
   ```
   Windows PowerShell 示例：
   ```powershell
   $env:CLAUDE_SKILL_DIR = "D:\path\to\dm-skill"
   python "$env:CLAUDE_SKILL_DIR\scripts\dm_query.py" --sql "SELECT * FROM DUAL"
   ```
3. **依赖与连接**：在 Claude Code 执行命令的终端环境中安装 **dmPython**，并配置与上文相同的 `DM_USER` / `DM_PASSWORD` / `DM_HOST` / `DM_PORT` / `DM_SCHEMA`（或 `DM_DSN`）。**ARM 环境**下连库规则见 [CPU 架构](#cpu-架构arm-与-dmpython)。
4. **与 SKILL.md 的对应关系**：`SKILL.md` 里声明的 `allowed-tools`（如 `Read`、`Bash`）需与 Claude Code 侧实际可用的工具一致；执行查询即通过终端调用 `dm_query.py`。

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
