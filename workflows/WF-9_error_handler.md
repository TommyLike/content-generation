# WF-9 错误工作流 — 节点级规格

> 设计文档 v3.2，第 2.5 节

## 基本信息

| 属性 | 值 |
|------|-----|
| Workflow 名称 | WF-9 错误工作流 |
| 触发方式 | n8n Error Trigger（任一 workflow 未捕获异常） |
| 运行时长 | < 5s |
| Error Workflow | 无（自身不设 Error Trigger，避免无限递归） |

## 节点清单

```
[Error Trigger] 捕获异常
  ├─ 输入: 失败 workflow 的执行上下文
  │   ├─ error.message / error.stack
  │   ├─ workflow_id (WF-0/1/2/3)
  │   ├─ workflow 节点的输入数据（含 run_id, record_id, 产物类型）
  │   └─ timestamp
  └─ 输出: 原始错误信息
          ↓
[节点1] Set Node — 解析错误并归类
  ├─ 尝试从 workflow 输入数据中提取: run_id, record_id, content_version
  ├─ 确定产物类型:
  │   ├─ WF-1 → 海报
  │   ├─ WF-2 → 推文
  │   ├─ WF-3 → 视频
  │   └─ 未知 → "系统"
  ├─ 错误分类:
  │   ├─ Timeout → "超时失败"
  │   ├─ HTTP 4xx → "接口参数错误"
  │   ├─ HTTP 5xx → "外部服务异常"
  │   ├─ Network Error → "网络不可达"
  │   └─ 其他 → "系统错误"
  └─ 输出: parsed_error (含 run_id, record_id, 产物类型, 错误分类, 错误摘要)
          ↓
[节点2] IF Node — 是否为已知未捕获异常
  ├─ IF run_id 为空 (上下文丢失):
  │   → 走最小告警路径 (仅通知，不回写)
  └─ ELSE:
      → 正常路径
          ↓
[节点3] 飞书 Node — 回写失败状态
  ├─ 条件: run_id 存在
  ├─ PUT 飞书多维表格记录: record_id
  ├─ 对应产物状态 = 错误分类 (如 "系统错误" / "超时失败")
  ├─ 备注 = 错误摘要 (前 200 字符)
  └─ timestamp
          ↓
[节点4] 写运行台账
  ├─ 追加失败记录: run_id, record_id, 产物类型, 错误分类, 耗时, 错误摘要
  └─ 结果 = 失败
          ↓
[节点5] 飞书 Node — 告警推送
  ├─ 发送到「工具封装者」飞书消息
  ├─ 内容:
  │   ## 🚨 工作流异常
  │   - **Run ID**: {run_id}
  │   - **活动名称**: {活动名称}
  │   - **产物类型**: {产物类型}
  │   - **错误分类**: {错误分类}
  │   - **时间**: {timestamp}
  │   - **错误摘要**: {前 200 字符}
  │   - **堆栈**: {前 500 字符}
  └─ @ 工具封装者
          ↓
[节点6] （可选）IF Node — 按错误严重度升级
  ├─ IF 同类错误 30min 内 > 5 次:
  │   → @ 团队 Leader + 电话通知
  └─ ELSE: 不升级
```

## 告警群 Webhook

在飞书群机器人中配置 Incoming Webhook URL，填入 n8n 的「飞书通知」节点。

## 避免无限递归

WF-9 **自身不设 Error Trigger**。如果 WF-9 崩溃（极端情况），通过：
- n8n 自身的健康检查告警
- Docker 容器监控
