# CLAUDE.md — 活动内容生产工作流 维护指南

## 项目定位

本仓库是一套 **AI 辅助活动内容生产工作流** 的完整工程实现。核心链路：运营填飞书表格 → n8n 编排 → 海报（稿定模板）+ 推文（Dify）+ 视频（可选）→ 自动检查 → 人工审核 → 定稿。

## 架构地图

```
┌── 设计层 ─────────────────────────────────────────────┐
│  design.md              — 完整设计方案（权威真相源）      │
│  README.md              — 项目概览与快速开始              │
└───────────────────────────────────────────────────────┘
┌── 编排层 (n8n) ───────────────────────────────────────┐
│  workflows/WF-0_dispatcher.md    — 派发器              │
│  workflows/WF-1_poster.md        — 海报子工作流         │
│  workflows/WF-2_article.md       — 推文子工作流         │
│  workflows/WF-3_video.md         — 视频子工作流         │
│  workflows/WF-9_error_handler.md — 错误处理工作流       │
└───────────────────────────────────────────────────────┘
┌── 配置层 ─────────────────────────────────────────────┐
│  config/brand_config.json  — 品牌配置（稿定模板ID+色板）│
│  config/review_rules.json  — 审核规则注册表             │
│  config/banned_words.txt   — 禁用词                    │
│  config/sensitive_words.txt— 敏感词                    │
│  config/term_glossary.json — 标准术语                   │
└───────────────────────────────────────────────────────┘
┌── 提示词层 ───────────────────────────────────────────┐
│  prompts/ai_image_prompt.md     — AI 底图生成           │
│  prompts/dify_article_*.md     — 推文生成（3 种类型）    │
└───────────────────────────────────────────────────────┘
┌── 部署层 ─────────────────────────────────────────────┐
│  deploy/docker-compose.yml  — n8n+PG+Redis+Nginx       │
│  deploy/nginx.conf          — 反向代理（仅暴露webhook）  │
│  deploy/.env.example        — 环境变量模板               │
└───────────────────────────────────────────────────────┘
┌── 集成层 ─────────────────────────────────────────────┐
│  feishu/table_schema.md     — 飞书多维表格字段定义       │
│  feishu/app_config.md       — 飞书自建应用配置指南       │
│  feishu/card_template.json  — 审核消息卡片              │
│  tests/test_cases.md        — 测试用例（E1-E7）         │
│  scripts/write_metadata.py  — PNG 隐式元数据写入         │
└───────────────────────────────────────────────────────┘
```

## 关键文件索引

### 权威设计文档

`design.md` —— 任何关于"为什么这样做"的问题，先查这里。

关键章节速查：
- 第一章：工作流全景图
- 第二章：n8n 编排层（WF-0/1/2/3/9 节点级规格）
- 第三章：逐层拆解（3A AI底图 / 3A-post 稿定模板 / 3B Dify / 3C 视频）
- 第四章：审核体系（3.1-3.8 含再生成回环）
- 第六章：前置依赖清单 P0-P19
- 第七章：Phase 0 先行验证范围与验收标准
- 第九章：风险提示
- 第十章：自部署与实施细则

### 权威配置

| 文件 | 修改者 | 修改时机 |
|------|--------|----------|
| `config/brand_config.json` | 设计师 + 工具封装者 | 新增稿定模板/改色板 |
| `config/review_rules.json` | 工具封装者 | 新增/调整检查规则 |
| `config/banned_words.txt` | 运营 | 发现新禁用词 |
| `config/sensitive_words.txt` | 运营 | 每月 Review 更新 |
| `config/term_glossary.json` | 运营 | 术语变更 |

## 日常维护操作指南

### 1. 运营新增禁用词/敏感词

```bash
# 编辑 config/banned_words.txt 或 config/sensitive_words.txt
# 一行一个词，# 开头为注释
# 提交 → n8n 下次执行自动生效（Code 节点读文件）
git add config/banned_words.txt
git commit -m "chore: 新增禁用词 XXX"
git push
```

### 2. 设计师新增海报模板

```bash
# 1. 在稿定图形界面创建新模板、标注变量槽位
# 2. 更新 brand_config.json 的 gaoding_templates
# 3. 如新模板需要新检查规则，更新 review_rules.json
# 4. 在飞书表单「海报模板」下拉选项中新增选项
git add config/brand_config.json config/review_rules.json
git commit -m "feat: 新增 XX 海报模板"
git push
```

### 3. 新增检查规则

```bash
# 1. 在 review_rules.json 注册（注意 deterministic 与 severity 约束）
# 2. 在 n8n 的 WF-1/2/3 中新增对应的 Code 节点（或复用函数）
# 3. 测试 → 上线
```

约束：`severity=blocking` 必须 `deterministic=true`；`deterministic=false` 只能 `severity=warning`。

### 4. 修改 n8n 工作流

`workflows/` 目录下的 `.md` 文件是 **节点级规格说明书**（node-by-node specification），不是 n8n 导出 JSON。实际修改流程：

1. 在 n8n 管理界面修改工作流
2. 导出 JSON → 覆盖 `workflows/` 对应文件
3. 同步更新对应的 `.md` 规格文件（保持文档与实现一致）
4. `git commit` 提交

### 5. 部署更新

```bash
cd deploy

# 更新 n8n/Dify 版本前先备份
docker compose down
cp -r /var/lib/docker/volumes/cg_* backups/$(date +%Y%m%d)/

# 修改 docker-compose.yml 中的镜像版本号
# 然后拉起
docker compose up -d

# 验证 webhook 可用
curl https://your-domain.com/webhook/test
```

## 硬性约束（不可省略）

下列约束来自 `design.md`，标注为 `⟦实施约束⟧`，任何修改不得违反：

1. **工作流拆分**：必须保持 5 个独立 workflow 架构（WF-0/1/2/3/9），禁止合并为单体
2. **异步 fire-and-forget**：WF-0 通过 HTTP Webhook 调用子工作流（Respond Immediately），禁止用 Execute Workflow 节点
3. **审核分级**：概率性检测器一律 🟡 强制人审，不得设 🔴 自动驳回；`deterministic=false` 的规则 severity 只能是 `warning`
4. **合规标识**：AI 内容必须同时具有显式标识（画面可见）+ 隐式标识（文件元数据五要素 1-3），在生成阶段写入，不在事后补
5. **地图安全网**：表单「涉及地图=是」为权威触发器，强制人工审核
6. **字体**：海报/视频中文字使用思源黑体（SIL OFL），禁止微软雅黑（版权原因）
7. **公网入口**：仅暴露 n8n webhook 路径到公网（`/webhook/`），管理界面/数据库/Dify 限内网
8. **密钥管理**：所有密钥进 n8n 凭证/.env，不入 git；`.env` 必须 `.gitignore`

## 外部服务依赖

修改涉及以下服务时，注意对应 API 限制：

| 服务 | 关键限制 | 监控 |
|------|----------|------|
| 飞书 OpenAPI | tenant_access_token 有效期 2h，需缓存刷新 | token 过期日志 |
| 稿定 API | 按调用量计费，企业订阅 | 配额 + 限流 429 |
| 通义万相 API | 任务制异步，qps 限制 | 超时 + 错误率 |
| Dify API | 自部署，按 LLM Token 计费 | 响应延迟 |
| 云内容安全 | 图片/文本审核 qps | 超时降级为 🟡 |
| 即梦/可灵 API | 异步轮询，生成队列 | 超时 12min 上限 |

## 测试

### 组件冒烟（每次部署后执行）

1. 飞书 webhook 可达性
2. n8n token 刷新 + 回写飞书
3. 稿定模板渲染
4. AI 底图生成
5. Dify 推文生成
6. 隐式元数据写入/读取校验

### 端到端用例（Phase 0 必过）

E1: Happy path（全链路通过）
E2: 部分失败注入（推文失败 → 海报仍待审）
E3: 重复触发拦截（幂等）
E4: 再生成回环（content_version+1）
E5: 阻断项（日期格式错 → 🔴 驳回）
E6: 强制人审（涉及地图=是 → 必进人审）
E7: 超时（视频超时 → 标失败+告警）

详见 `tests/test_cases.md`

## 运行台账

台账表（飞书独立表格）记录每次 run 的数据：

```
run_id | record_id | content_version | 产物类型 | 耗时 |
触发时间 | 结果 | 检查_阻断数/警告数/通过数 | 审核决策 | 是否一次通过
```

每月 Review 依据台账统计：一次通过率趋势、各检查项触发率、🔴 误报率、🟡 漏报率、端到端耗时 P50/P95

## 常见故障排查

| 症状 | 可能原因 | 排查路径 |
|------|----------|----------|
| 飞书填表不触发 | webhook 不通/域名过期 | `curl https://域名/webhook/...` |
| 海报生成失败 | 稿定 API 额度/计费 | n8n 执行日志 + 稿定后台 |
| 推文质量差 | prompt 退化/RAG 知识库过期 | Dify 后台看 LLM 调用日志 |
| 子工作流被中止 | 用了 Execute Workflow 节点 | 必须改用 Webhook 模式 |
| Wait 节点不恢复 | SQLite/未用 PostgreSQL | 检查 DB_TYPE=postgresdb |
| 旧任务覆盖新结果 | content_version 未正确比对 | 检查回写节点 version 比较逻辑 |
| 🔴 误报过多 | 确定性规则设得太严 | 调整参数或降为 🟡 |
| 🟡 漏报（尤其地图） | 概率检测器未命中 | 确保「涉及地图」表单字段有效触发 |
