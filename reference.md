# 达梦只读 Skill — 参考

## 脚本退出码

| 码 | 含义 |
|----|------|
| 0 | 成功 |
| 1 | 参数错误（如未提供 `--sql`/`--file`） |
| 2 | 缺少依赖或未配置连接 |
| 3 | 执行期数据库/驱动错误 |

## JSON 输出字段

成功时大致结构：

```json
{
  "ok": true,
  "sql": "规范化后的 SQL",
  "columns": ["COL1", "COL2"],
  "rows": [{"COL1": 1, "COL2": "a"}],
  "row_count": 1,
  "returned": 1,
  "truncated": false
}
```

失败时：

```json
{ "ok": false, "error": "原因说明" }
```

## 校验局限

- 注释移除采用简单正则，**字符串字面量内**若含与注释冲突的子串，可能导致误判；复杂场景可让用户去掉注释重试。
- 仅基于关键字与首词判断只读，**无法**防御所有逻辑侧风险（例如极重查询）；应用侧请使用只读账号与资源限制。

## 与 colleague-skill 的对齐方式

本 Skill 同样采用：

- YAML frontmatter（`name` / `description` / `version` / `user-invocable` / `allowed-tools`）
- 明确的「触发条件 + 工具表 + Bash 调用脚本」结构
- 环境变量配置密钥，不写入仓库

便于放入 `.cursor/skills/`、`~/.cursor/skills/` 或 Claude Code 的 skills 目录使用。
