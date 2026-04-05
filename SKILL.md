---
name: dm-database-readonly
description: "Queries Dameng (DM / 达梦) databases in read-only mode via validated SQL and dmPython. Supports arbitrary SELECT-style exploration, SHOW/DESC metadata, and custom SQL; blocks INSERT/UPDATE/DELETE/DDL and other writes. Use when the user mentions 达梦、DM 数据库、Dameng, read-only SQL, or querying DM."
argument-hint: "[optional SQL or question about tables]"
parameter-schema:
  type: object
  description: 达梦连接用的环境变量名；与正文「连接参数与 JDBC URL」一致。另需 DM_USER、DM_PASSWORD（或 DM_DSN）。
  required: [DM_HOST, DM_PORT, DM_SCHEMA]
  properties:
    DM_HOST:
      type: string
      description: 数据库主机。
    DM_PORT:
      type: integer
      description: 监听端口（常见 5236）。
    DM_SCHEMA:
      type: string
      description: 模式名（schema）；dmPython 连接参数与 JDBC 路径段、schema= 使用同一值。
  additionalProperties: true
version: "1.0.0"
user-invocable: true
allowed-tools: Read, Bash
---

> **语言**：用户用中文则用中文回复；用户用英文则用英文回复。

# 达梦数据库只读查询（DM Read-Only）

## 何时使用本 Skill

在以下情况启用：

- 用户要**查询达梦（DM）库**中的表、视图、统计或任意**只读**数据
- 用户给出或需要你编写**自定义 SQL**（仅限只读）
- 用户明确说**不能改库**、只要 SELECT / 分析 / 探查 schema

**禁止**：任何 **INSERT、UPDATE、DELETE、MERGE、DDL、GRANT、存储过程执行（CALL/EXEC）** 等写入或权限变更。若用户要求改数据，说明本 Skill 与脚本均不支持，请改用 DBA 工具或专用迁移流程。

---

## 工具与路径

| 任务 | 做法 |
|------|------|
| 执行只读 SQL | `Bash` → `python3` 运行本 Skill 内脚本（见下；**ARM 上 dmPython 连库不可用**，见「架构说明」） |
| 查看 Skill 说明或示例 | `Read` → 打开本仓库 `SKILL.md` 或 `reference.md` |

**脚本路径**（将 `{SKILL_ROOT}` 换成本仓库 `dm-skill` 的根目录，即包含 `SKILL.md` 的目录）：

```bash
python3 {SKILL_ROOT}/scripts/dm_query.py --sql "你的SQL"
# 或
python3 {SKILL_ROOT}/scripts/dm_query.py --file /path/to/query.sql --max-rows 500
```

在 Claude Code 且已设置 `CLAUDE_SKILL_DIR` 时，可写为：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/dm_query.py" --sql "SELECT * FROM DUAL"
```

执行前需在 shell 中导出连接信息（**二选一**）。地址与模式相关字段的**规范定义**见上文 frontmatter 中的 `parameter-schema`（`DM_HOST`、`DM_PORT`、`DM_SCHEMA`）。

### 连接参数与 JDBC URL

与 **DM_HOST / DM_PORT / DM_SCHEMA** 等价的 **JDBC 连接串**（用于 Java 等 JDBC 客户端；将占位符替换为实际值）：

```text
jdbc:dm://${DM_HOST}:${DM_PORT}/${DM_SCHEMA}?schema=${DM_SCHEMA}&zeroDateTimeBehavior=convertToNull&useUnicode=true&characterEncoding=utf-8&clobAsString=1
```

本仓库脚本使用 **dmPython**，不直接消费 JDBC URL；请在 shell 中设置同名环境变量。

**方式 A — 分项环境变量（推荐）**

```bash
export DM_USER="SYSDBA"
export DM_PASSWORD="******"
export DM_HOST="127.0.0.1"
export DM_PORT="5236"
export DM_SCHEMA="YOUR_SCHEMA"
# 可选
export DM_MAX_ROWS="500"
```

**方式 B — DSN 字符串**

```bash
export DM_DSN="SYSDBA/your_password@localhost:5236/SCH1"
```

密码与 DSN **不要**写进 Skill 文件或提交到 Git；由用户在环境中配置。

---

## 依赖

```bash
pip install -r {SKILL_ROOT}/requirements.txt
```

**国内镜像（阿里云 PyPI，常用作原淘宝镜像的替代）** 加速安装 **dmPython**：

```bash
pip install -r {SKILL_ROOT}/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

也可只装驱动：

```bash
pip install "dmPython>=2.5.0" -i https://mirrors.aliyun.com/pypi/simple/
```

若经镜像仍无法安装 **dmPython**，从达梦安装介质中安装与服务器版本匹配的 whl（以官方文档为准）。

### 架构说明（ARM / AArch64）

当前 **dmPython 无官方 ARM 预编译包**。在 **ARM 架构**（如 Apple Silicon、aarch64、arm64）上：

- **连库查询**（不带 `--validate-only`）：`dm_query.py` 会**拒绝执行**并退出码 `2`，请改用 **x86_64/amd64** 环境运行本脚本，或使用 **达梦 JDBC** 等 Java 方式在 ARM 上访问数据库。
- **仅校验 SQL**（`--validate-only`）：仍可用，不依赖 dmPython。

详见仓库 [README.md](README.md) 中的「CPU 架构」说明。

---

## Agent 执行流程

1. **确认意图**：只读查询；若用户要求写入，拒绝并说明边界。
2. **编写或确认 SQL**：优先参数化思路；避免拼接不可信输入。若 SQL 来自用户粘贴，仍须经脚本校验。
3. **先校验（可选）**：
   ```bash
   python3 {SKILL_ROOT}/scripts/dm_query.py --validate-only --sql "SELECT 1 FROM DUAL"
   ```
4. **执行查询**：
   ```bash
   python3 {SKILL_ROOT}/scripts/dm_query.py --sql "..." --max-rows 500
   ```
   若检测到 **ARM 且无法连库**，说明原因并引导用户使用 x86_64 或 JDBC（见上文「架构说明」）。
5. **解读结果**：脚本 stdout 为 **JSON**（`ok`、`columns`、`rows`、`row_count`、`truncated` 等）。向用户总结关键结论；大行集说明已截断并可缩小条件或提高 `DM_MAX_ROWS`（注意内存与性能）。

---

## SQL 规则（与脚本一致）

- 允许以 **`SELECT`、`WITH`、`EXPLAIN`、`SHOW`、`DESC`、`DESCRIBE`** 开头（大小写不敏感，可带末尾分号）。
- **禁止**语句中出现以下关键字（整词匹配，含注释 stripped 后的主体）：  
  `INSERT`、`UPDATE`、`DELETE`、`MERGE`、`REPLACE`、`DROP`、`CREATE`、`ALTER`、`TRUNCATE`、`RENAME`、`GRANT`、`REVOKE`、`COMMIT`、`ROLLBACK`、`SAVEPOINT`、`CALL`、`EXECUTE`、`EXEC`。
- **禁止**多条语句（多个 `;` 分隔的独立语句）。
- 默认最多返回 **500** 行（`--max-rows` 或 `DM_MAX_ROWS`）；超出部分不返回但 `row_count` 可反映已取总行数（取决于驱动 `fetchall` 行为，超大结果集建议在 SQL 中加 `WHERE`/分页）。

---

## 常用探查示例

```sql
-- 当前用户可见表（视版本/权限而定）
SELECT TABLE_NAME FROM USER_TABLES;

-- 表结构
SELECT COLUMN_NAME, DATA_TYPE, NULLABLE
FROM USER_TAB_COLUMNS
WHERE TABLE_NAME = 'YOUR_TABLE';

-- 采样
SELECT * FROM YOUR_SCHEMA.YOUR_TABLE WHERE ROWNUM <= 20;
```

达梦字典表名可能因版本略有差异；若报错，用 `USER_TABLES` / `ALL_TABLES` / `DBA_TABLES` 按权限切换。

---

## 安全与合规

- 不在对话中重复打印完整密码。
- 生产库查询使用**只读账号**；限制 `DM_MAX_ROWS` 与查询时间窗口。
- 用户 SQL 可能包含敏感列；输出时注意脱敏与最小必要原则。

---

## 更多说明

- 实现细节与边界案例见 [reference.md](reference.md)。
