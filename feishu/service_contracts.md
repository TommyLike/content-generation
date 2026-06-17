# =============================================================================
# 服务间数据契约
# 设计文档 v3.2，第 10.6 节
# =============================================================================
# 说明：以下为字段骨架。具体 endpoint/字段名以最终选定服务商的 API 文档为准。
#       落地时补实并写进 n8n 节点配置。
# =============================================================================

## 1. WF-0 → 子工作流 Webhook（HTTP POST body）

### WF-1 海报 / WF-2 推文 / WF-3 视频 统一契约

```json
{
  "run_id": "rec_abc123-1718123456789",
  "record_id": "rec_abc123",
  "content_version": 1,
  "is_regen": false,
  "fields": {
    "活动名称": "开源之夏 2026",
    "活动时间": "2026-07-15T14:00:00+08:00",
    "一句话简介": "面向高校学生的开源项目实习计划",
    "活动详情": "本届开源之夏共设200+项目，覆盖AI/云原生/操作系统等多个领域...",
    "视觉风格": "科技蓝",
    "海报模板": "event_preview",
    "推文类型": "活动招募",
    "生成视频": false,
    "视频类型": "",
    "视频时长": "",
    "视频旁白风格": "",
    "涉及地图": false,
    "特殊要求": "",
    "再生成意见": ""
  },
  "_auth": "<X-Internal-Token>"
}
```

---

## 2. 稿定 模板设计 API

### 请求（POST）

```json
{
  "template_id": "<稿定平台模板ID>",
  "variables": {
    "bg_image": "<AI底图URL>",
    "title": "开源之夏 2026",
    "date": "2026年7月15日 14:00",
    "subtitle": "面向高校学生的开源项目实习计划",
    "qr": "<二维码图片URL>",
    "partner_logo": "<合作伙伴Logo URL | null>"
  }
}
```

### 响应（同步）

```json
{
  "code": 0,
  "data": {
    "image_url": "<渲染完成的图片URL>",
    "width": 1080,
    "height": 1920,
    "format": "png"
  }
}
```

### 响应（异步，如有）

```json
{
  "code": 0,
  "data": {
    "task_id": "<轮询用任务ID>",
    "status": "processing"
  }
}
```

---

## 3. AI 图像 API（通义万相）

### 请求（POST）

```json
{
  "model": "wanx-v1",
  "input": {
    "prompt": "<组装后的完整prompt>"
  },
  "parameters": {
    "size": "1080*1920",
    "n": 1,
    "seed": null
  }
}
```

### 响应

```json
{
  "output": {
    "task_id": "<如异步>",
    "task_status": "SUCCEEDED",
    "results": [
      {
        "url": "<底图URL>"
      }
    ]
  },
  "usage": {
    "image_count": 1
  }
}
```

---

## 4. Dify API

### 请求（POST /v1/workflows/run）

```json
{
  "inputs": {
    "活动名称": "开源之夏 2026",
    "活动时间": "2026年7月15日 14:00",
    "一句话简介": "面向高校学生的开源项目实习计划",
    "活动详情": "本届开源之夏共设200+项目...",
    "推文类型": "recruit",
    "再生成意见": ""
  },
  "response_mode": "blocking",
  "user": "n8n-wf2"
}
```

### 响应

```json
{
  "data": {
    "outputs": {
      "text": "完整的推文正文...\n\n本内容由 AI 辅助生成",
      "标题备选": ["标题1...", "标题2...", "标题3..."],
      "事实核查标注": [
        {"statement": "...", "confidence": "low", "reason": "..."}
      ]
    }
  }
}
```

---

## 5. 云内容安全 API

### 请求 — 图片审核

```json
{
  "scenes": ["porn", "terrorism", "ad", "logo"],
  "tasks": [
    {
      "url": "<海报图片URL>"
    }
  ]
}
```

### 响应

```json
{
  "data": [
    {
      "code": 200,
      "task_id": "...",
      "results": [
        {
          "scene": "ad",
          "label": "normal",
          "suggestion": "pass",
          "rate": 99.5
        }
      ]
    }
  ]
}
```
> 命中 `suggestion != pass` → 🟡 IMG-CONTENT-001 强制人审

---

## 6. 飞书 更新记录 API

```
PUT https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}

Headers:
  Authorization: Bearer <tenant_access_token>
  Content-Type: application/json

Body:
{
  "fields": {
    "海报状态": "待审",
    "海报预览": [{"link": "<图片URL>"}],
    "检查报告_海报": "{...JSON摘要...}",
    "完成时间_海报": 1718123456789
  }
}
```

---

## 7. 检查报告统一结构

```json
{
  "run_id": "rec_abc123-1718123456789",
  "product_type": "poster",
  "timestamp": 1718123456789,
  "summary": {
    "blocking": 0,
    "warning": 3,
    "pass": 11
  },
  "details": [
    {
      "rule": "IMG-BRAND-003",
      "result": "warn",
      "detail": "底图主色 #1A56DB 偏离品牌色板最近色 #C00000 距离 78 (>15)",
      "suggestion": "底图整体偏蓝，建议人工确认是否符合品牌调性"
    }
  ]
}
```

---

## 8. 运行台账记录结构

```json
{
  "run_id": "rec_abc123-1718123456789",
  "record_id": "rec_abc123",
  "content_version": 1,
  "活动名称": "开源之夏 2026",
  "产物类型": "海报",
  "触发时间": "2026-06-17T10:00:00+08:00",
  "完成时间": "2026-06-17T10:02:15+08:00",
  "耗时秒": 135,
  "结果": "成功",
  "检查_阻断数": 0,
  "检查_警告数": 2,
  "检查_通过数": 12,
  "人工审核决策": "通过",
  "是否一次通过": true,
  "备注": ""
}
```
