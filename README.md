# 活动内容生产工作流

> **一张表进去，海报+推文+视频（可选）出来**

AI 辅助活动内容生产工作流，覆盖从「运营填表」到「海报+推文+视频定稿」的完整链路。基于 n8n + Dify + 稿定开放平台 + 飞书。

---

## 快速概览

```
运营填表(飞书多维表格) → n8n 派发器 → 并行异步子工作流
  ├─ 海报: AI底图 → 稿定模板填充 → 合规标识 → 自动检查 → 审核
  ├─ 推文: Dify RAG → 事实核查 → 合规标识 → 自动检查 → 审核
  └─ 视频(可选): AI视频 → 品牌固化 → 合规标识 → 自动检查 → 审核
                                      ↓
                             飞书状态看板 → 人工审核 → 定稿发布
```

## 目录结构

```
content-generation/
├── design.md                     # 完整设计文档（v3.2）
├── README.md                     # 本文件
├── CLAUDE.md                     # Claude Code 维护指南
│
├── deploy/                       # 部署基础设施
│   ├── docker-compose.yml        # n8n + PostgreSQL + Redis + Nginx
│   ├── nginx.conf                # 反向代理 + TLS 终止
│   ├── .env.example              # 环境变量模板
│   └── setup.sh                  # 一键部署脚本
│
├── config/                       # 配置文件（git 版本管理）
│   ├── brand_config.json         # 品牌配置（稿定模板ID + 色板）
│   ├── review_rules.json         # 审核规则注册表
│   ├── banned_words.txt          # 禁用词
│   ├── sensitive_words.txt       # 敏感政治词库
│   └── term_glossary.json        # 标准术语表
│
├── workflows/                    # n8n 工作流规格与导出
│   ├── WF-0_dispatcher.md        # 派发器（节点级规格）
│   ├── WF-1_poster.md            # 海报子工作流
│   ├── WF-2_article.md           # 推文子工作流
│   ├── WF-3_video.md             # 视频子工作流（可选）
│   └── WF-9_error_handler.md     # 错误工作流
│
├── prompts/                      # Prompt 模板
│   ├── ai_image_prompt.md        # AI 底图生成
│   ├── dify_article_recruit.md   # Dify 活动招募推文
│   ├── dify_article_review.md    # Dify 活动回顾推文
│   └── dify_article_interview.md # Dify 嘉宾访谈推文
│
├── feishu/                       # 飞书配置
│   ├── table_schema.md           # 多维表格字段定义
│   ├── app_config.md             # 自建应用配置指南
│   └── card_template.json        # 审核消息卡片模板
│
├── brand-assets/                 # 品牌资产（本地留档）
│   ├── fonts/                    # 思源黑体源文件
│   ├── logos/                    # Logo 源文件
│   ├── video/                    # 视频品牌模板（片头/片尾/LUT）
│   ├── music/                    # BGM + 授权清单
│   └── map_reference/            # 官方中国地图参考
│
├── tests/                        # 测试用例
│   └── test_cases.md             # 组件冒烟 + 端到端（E1-E7）
│
├── scripts/                      # 工具脚本
│   ├── write_metadata.py         # 隐式元数据写入（iTXt/XMP）
│   └── check_metadata.py         # 元数据校验
│
└── artifacts/                    # 运行台账数据（非 git）
```

## 核心架构

### 编排层：n8n（5 个独立工作流）

| Workflow | 角色 | 触发方式 | 运行时长 |
|----------|------|----------|----------|
| `WF-0` | 派发器：监听飞书→校验→幂等检查→异步派活 | 飞书 Webhook | < 10s |
| `WF-1` | 海报：AI底图→稿定填充→检查→回写 | HTTP Webhook | ~2min |
| `WF-2` | 推文：Dify写稿→核查→检查→回写 | HTTP Webhook | ~3min |
| `WF-3` | 视频（可选）：AI视频→固化→检查→回写 | HTTP Webhook | ~5min |
| `WF-9` | 错误处理：统一捕获异常→回写失败→告警 | Error Trigger | 即时 |

**关键设计**：fire-and-forget 异步模式——WF-0 秒级返回，子工作流独立运行、独立失败、独立重跑。一个产物失败不拖垮其余。

### 关键选型

| 组件 | 选型 | 原因 |
|------|------|------|
| 编排引擎 | n8n (Docker 自部署) | 可视化编排、Webhook 原生支持、PostgreSQL 持久化 |
| 海报渲染 | 稿定开放平台 autofill API | 设计师零代码维护模板、品牌更改不改代码 |
| 推文生成 | Dify 社区版 + RAG | 知识库增强、Prompt 版本管理、国产替代 LangChain |
| AI 底图 | 通义万相 / 文心一格 | 国内合规、API 调用 |
| AI 视频(可选) | 即梦 / 可灵 | 视频生成、API 异步轮询 |
| 协作平台 | 飞书多维表格 | 表单入口 + 状态看板 + 消息通知 |
| AI 字体 | 思源黑体 (SIL OFL) | 开源可商用，避免微软雅黑版权风险 |

### 合规体系（GB 45438-2025）

**显式标识**（画面/文本可见）：
- 海报：底边文字 "AI生成"
- 推文：末尾行 "本内容由 AI 辅助生成"
- 视频：片尾 + 底部持续标识

**隐式标识**（文件元数据）：
- PNG iTXt/XMP / MP4 metadata 五要素（生成标签/服务提供者/制作编号）

**审核分级**：
- 🔴 阻断：仅确定性高精度检查（正则、元数据存在性、HTTP 404）
- 🟡 强制人审：所有概率性检测器（AI 分类、OCR、LLM 打分）
- 🟢 通过

## 快速开始

### 前置条件

1. **服务器**：2 vCPU / 4GB / 40GB + 公网 IP + 域名 + TLS 证书
2. **外部服务账号**（见下方清单）
3. **Docker** 20.10+ & **Docker Compose** 2.0+

### 外部服务依赖清单

| 服务 | 用途 | 获取方式 |
|------|------|----------|
| 飞书自建应用 | 多维表格读写 + 消息通知 | [飞书开放平台](https://open.feishu.cn/) |
| 稿定开放平台 | 海报模板渲染 API | [稿定开放平台](https://open.gaoding.com/) |
| 通义万相 API | AI 底图生成 | [阿里云百炼](https://bailian.console.aliyun.com/) |
| Dify | 推文生成（可自部署） | [Dify](https://dify.ai/) |
| 云内容安全 API | 敏感内容检测 | 阿里云/腾讯云 |
| 即梦/可灵 API (可选) | AI 视频生成 | 各自开放平台 |

### 部署步骤

```bash
# 1. 克隆仓库
git clone <repo-url> content-generation && cd content-generation

# 2. 配置环境变量
cp deploy/.env.example deploy/.env
# 编辑 deploy/.env，填入真实密钥

# 3. 准备 TLS 证书
mkdir -p deploy/certs
# 将 fullchain.pem 和 privkey.pem 放入 deploy/certs/

# 4. 修改 Nginx 域名
# 将 deploy/nginx.conf 中的 ${N8N_HOST} 替换为实际域名

# 5. 启动服务
cd deploy && docker compose up -d

# 6. 验证
curl https://your-domain.com/webhook/test
# 应返回 n8n webhook 响应

# 7. 导入工作流
# 登录 n8n 管理界面 → Import → 选择 workflows/ 目录下的 JSON 文件
```

### 初始配置

1. **飞书多维表格**：按 `feishu/table_schema.md` 创建字段
2. **飞书自动化**：配置「新增记录 → HTTP POST 到 WF-0 webhook」
3. **稿定模板**：在稿定界面创建模板，填入 `brand_config.json` 的 template_id
4. **Dify 知识库**：上传历史推文、活动资料
5. **n8n 凭证**：录入所有 API key

## 角色与职责

| 角色 | 日常投入 | 关键任务 |
|------|----------|----------|
| **运营人员** | ~15min/次 | 填表、审核推文、维护禁用词/敏感词/术语表 |
| **设计师** | ~15-25min/次 + ~2h/月 | 审核海报、维护稿定模板（零代码）、维护检查规则 |
| **工具封装者** | ~3-5h/周（日常） | 维护 n8n/Dify/隐式元数据脚本、监控告警 |

## Phase 0 验收标准

| # | 指标 | 通过线 |
|---|------|--------|
| G1 | 设计师海报一次通过率 | ≥ 60% |
| G2 | 运营推文改稿幅度 | < 40% |
| G3 | 端到端耗时 | < 人工基线的 70% |
| G4 | 检查准确率 | 🔴 0 漏报 + 误报 < 10% |
| G5 | 健壮性 | 单产物失败不影响其余；幂等；再生成可用 |

## 版本

- **v3.2** (2026-06-17) — 新增第十章「自部署与实施细则」
- **v3.1** (2026-06-16) — 海报渲染切换为稿定模板方案
- **v3.0** (2026-06-15) — 编排重构、合规标识、审核分级

## 相关文档

- [完整设计文档](design.md) — 体系化设计方案（v3.2）
- [CLAUDE.md](CLAUDE.md) — Claude Code 维护指南
