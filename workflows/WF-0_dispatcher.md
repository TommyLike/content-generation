# WF-0 派发器 — 节点级规格

> 设计文档 v3.2，第 2.2 节

## 基本信息

| 属性 | 值 |
|------|-----|
| Workflow 名称 | WF-0 派发器 |
| 触发方式 | 飞书 Webhook（多维表格自动化 → HTTP POST） |
| 运行时长 | < 10s（秒返） |
| 超时设置 | 30s |
| Error Workflow | WF-9 错误工作流 |

## 节点清单

```
[节点1] Webhook Trigger (飞书)
  ├─ HTTP Method: POST
  ├─ Webhook URL Path: /wf0-dispatcher
  ├─ Authentication: Header Auth（校验 X-Internal-Token）
  ├─ Response Mode: Last Node
  └─ 输出: body.record_id + body.fields (全部表单字段)
          ↓
[节点2] Set Node — 生成 run_id 与 content_version
  ├─ run_id = `${record_id}-${Date.now()}`
  ├─ content_version = body.regen ? getExistingVersion(record_id) + 1 : 1
  ├─ is_regen = body.regen || false
  └─ 输出: run_id, content_version, is_regen, fields
          ↓
[节点3] IF Node — 幂等检查
  ├─ 调飞书 API: GET 该 record_id 的当前「海报状态」「推文状态」「视频状态」
  ├─ IF (任一状态 ∈ {生成中, 待审, 已定稿}) AND is_regen === false:
  │   → 停止 + 飞书通知 "该行已在处理中"
  └─ ELSE: 继续
          ↓
[节点4] IF Node — 参数校验
  ├─ 必填字段检查: 活动名称, 活动时间, 一句话简介, 活动详情, 视觉风格, 海报模板, 推文类型
  │   → 缺失则飞书通知 + 状态置「校验失败」+ 停止
  ├─ 枚举值检查: 视觉风格 ∈ {科技蓝, 开源绿, 社区红}; 海报模板 ∈ {活动预告, 活动回顾, 嘉宾海报}; 推文类型 ∈ {活动招募, 活动回顾, 嘉宾访谈}
  │   → 不匹配则飞书通知 + 状态置「校验失败」+ 停止
  └─ IF 生成视频 === 是:
      → 视频类型, 视频时长, 视频旁白风格 三项必填检查
          ↓
[节点5] 飞书 Node — 登记初始状态
  ├─ PUT 飞书多维表格记录: record_id
  ├─ 海报状态 = 生成中
  ├─ 推文状态 = 生成中
  ├─ 视频状态 = (生成视频=是 ? 生成中 : 不适用)
  ├─ run_id = run_id
  ├─ content_version = content_version
  └─ 触发时间 = now
          ↓
[节点6] 并行 HTTP Request (3 路 fire-and-forget, 互不等待)
  ├─ HTTP Node A: POST {WF-1 webhook URL}
  │   ├─ URL: https://{N8N_HOST}/webhook/wf1-poster
  │   ├─ Body: { run_id, record_id, content_version, is_regen, fields, _auth: INTERNAL_TOKEN }
  │   ├─ Timeout: 10s, Retry: 3次 (仅调不通)
  │   └─ 不等待业务结果
  ├─ HTTP Node B: POST {WF-2 webhook URL}
  │   ├─ URL: https://{N8N_HOST}/webhook/wf2-article
  │   ├─ Body: { run_id, record_id, content_version, is_regen, fields, _auth: INTERNAL_TOKEN }
  │   ├─ Timeout: 10s, Retry: 3次
  │   └─ 不等待业务结果
  └─ HTTP Node C: IF 生成视频=是 → POST {WF-3 webhook URL}
      ├─ URL: https://{N8N_HOST}/webhook/wf3-video
      ├─ Body: { run_id, record_id, content_version, is_regen, fields, _auth: INTERNAL_TOKEN }
      ├─ Timeout: 10s, Retry: 3次
      └─ 不等待业务结果
          ↓
[节点7] Respond to Webhook
  └─ 返回 200: { status: "dispatched", run_id, content_version }
```

## n8n 配置要点

1. **Webhook 鉴权**：在 Webhook Trigger 中添加 Header 校验，`X-Internal-Token` 必须与 `.env` 中 `INTERNAL_WEBHOOK_TOKEN` 一致
2. **并行 HTTP Request**：节点 6 的三个 HTTP Request 在 n8n 中设为并行执行（非串行）
3. **Error Trigger**：绑定 WF-9 错误工作流，确保未捕获异常被接住
4. **时区**：所有 Date.now() 使用 `Asia/Shanghai`
