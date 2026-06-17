# WF-2 推文子工作流 — 节点级规格

> 设计文档 v3.2，第 2.3 节 + 第 3B 层

## 基本信息

| 属性 | 值 |
|------|-----|
| Workflow 名称 | WF-2 推文子工作流 |
| 触发方式 | HTTP Webhook（被 WF-0 调用） |
| 运行时长 | ~3min |
| 超时设置 | 5min |
| Error Workflow | WF-9 |

## 节点清单

```
[Webhook Trigger] 接收 WF-0 调用
  ├─ HTTP Method: POST
  ├─ Webhook URL Path: /wf2-article
  ├─ Authentication: Header Auth (X-Internal-Token)
  ├─ Response Mode: Respond Immediately (200)
  └─ 输出: run_id, record_id, content_version, is_regen, fields
          ↓
[节点1] Set Node — 确定 Dify prompt 模板
  ├─ 推文类型 = fields.推文类型 (活动招募 → recruit | 活动回顾 → review | 嘉宾访谈 → interview)
  ├─ Dify API Key → 按类型选择 (DIFY_API_KEY_ARTICLE_RECRUIT / REVIEW / INTERVIEW)
  ├─ 再生成意见 = fields.再生成意见 || ""
  └─ 输出: dify_api_key, template_type, regen_opinion
          ↓
[节点2] HTTP Node — 调 Dify 生成推文
  ├─ URL: POST ${DIFY_API_URL}/v1/workflows/run
  ├─ Headers: Authorization: Bearer ${dify_api_key}
  ├─ Body: {
  │    inputs: {
  │      活动名称: fields.活动名称,
  │      活动时间: 格式化后时间,
  │      一句话简介: fields.一句话简介,
  │      活动详情: fields.活动详情,
  │      推文类型: template_type,
  │      再生成意见: regen_opinion
  │    },
  │    response_mode: "blocking",
  │    user: "n8n-wf2"
  │  }
  ├─ Timeout: 120s, Retry: 2次
  └─ 响应: { 标题备选: [...], 正文: "...", 事实核查标注: [...] }
          ↓
[节点3] Code Node — 事实核查提取
  ├─ 从 Dify 响应中提取所有 ❓ 标记的语句
  ├─ 生成事实核查清单: [{ statement, context, reason }]
  └─ 输出: fact_check_items (用于审核报告)
          ↓
[节点4] Code Node — 追加 AI 显式标识
  ├─ IF 正文末尾无 "本内容由 AI 辅助生成":
  │   → 正文 += "\n\n本内容由 AI 辅助生成"
  └─ 输出: final_text
          ↓
[节点5] Code Node — 写入隐式标识随附元数据
  ├─ 生成 JSON 元数据文件:
  │   {
  │     "生成合成标签": "AIGC",
  │     "生成合成服务提供者": "Dify + XX开源社区",
  │     "内容制作编号": run_id
  │   }
  └─ (发布时间附进推文或存为伴随记录)
          ↓
[节点6] 自动检查 (调用检查器子流程)
  ├─ 文案类规则: TXT-BRAND-001,002,003 / TXT-TEXT-001,002,003,004 / TXT-FACT-001,002 / TXT-COMPLY-001,002,003 / TXT-STRUCT-001,002
  ├─ 确定性检查先跑：
  │   ├─ TXT-BRAND-002: 正则匹配 banned_words.txt
  │   ├─ TXT-TEXT-001: 日期正则提取比对表单
  │   ├─ TXT-TEXT-002: URL HTTP HEAD 验证
  │   └─ TXT-COMPLY-001: "本内容由 AI 辅助生成" 存在性校验
  ├─ 概率检查后跑：
  │   ├─ TXT-BRAND-001: LLM Tone 打分
  │   ├─ TXT-COMPLY-002: 敏感词匹配
  │   └─ ...
  └─ 产出检查报告: { blocking: N, warning: M, pass: K, details: [...] }
          ↓
[节点7] IF Node — 路由
  ├─ IF blocking > 0:
  │   → 飞书回写: 推文状态 = 失败(附阻断详情)
  │   → 飞书通知运营: 阻断原因 + 修改建议
  │   → 写台账(失败)
  └─ ELSE:
      → 飞书回写: 推文状态 = 待审, 推文预览 = final_text, 检查报告 = report
      → 飞书消息卡片推送给运营（含推文预览 + 检查报告 + 通过/修改/驳回按钮）
      → 写台账(成功)
```

## 关键细节

- **Dify 内部已处理**: RAG 检索、Few-shot 匹配、Prompt 组装——均在工作流内完成
- **事实核查标记**: ❓ 标在不确定性语句上，审核人只需关注标记项
- **再生成**: 意见通过 Dify inputs 传入，prompt 模板内部处理拼接
