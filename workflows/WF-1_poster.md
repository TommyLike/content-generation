# WF-1 海报子工作流 — 节点级规格

> 设计文档 v3.2，第 2.3 节 + 第 3A/3A-post 层

## 基本信息

| 属性 | 值 |
|------|-----|
| Workflow 名称 | WF-1 海报子工作流 |
| 触发方式 | HTTP Webhook（被 WF-0 调用） |
| 运行时长 | ~2min |
| 超时设置 | 5min（硬上限） |
| Error Workflow | WF-9 |

## 节点清单

```
[Webhook Trigger] 接收 WF-0 调用
  ├─ HTTP Method: POST
  ├─ Webhook URL Path: /wf1-poster
  ├─ Authentication: Header Auth（X-Internal-Token）
  ├─ Response Mode: Respond Immediately (200)  ← 关键：秒返，不解耦
  └─ 输出: run_id, record_id, content_version, is_regen, fields
          ↓
[节点1] 飞书 Node — 获取活动数据
  ├─ 从 fields 中取: 活动名称, 活动时间(格式化为"2026年7月15日 14:00"), 一句话简介, 视觉风格
  ├─ 海报模板类型 = fields.海报模板 (event_preview | event_review | guest_poster)
  └─ 再生成意见 = fields.再生成意见 || ""
          ↓
[节点2] Set Node — 组装 AI 底图 Prompt
  ├─ 读取 prompts/ai_image_prompt.md 模板
  ├─ 视觉风格 → 展开为详细描述 (科技蓝: "深蓝到亮蓝渐变，几何线条，未来感，粒子光效")
  ├─ 品牌主色调 → 从 brand_config.json color_check.palette 取主色
  ├─ {再生成意见} → 替换 (首次为空)
  └─ 输出: full_prompt
          ↓
[节点3] HTTP Node — 调通义万相 AI 底图生成
  ├─ URL: POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis
  ├─ Headers: Authorization: Bearer ${TONGYI_WANXIANG_API_KEY}
  ├─ Body: { model: "wanx-v1", input: { prompt: full_prompt }, parameters: { size: "1080*1920", n: 1 } }
  ├─ Timeout: 60s, Retry: 3次(指数退避5s/15s/45s)
  ├─ 响应处理: 取 output.results[0].url → bg_image_url
  └─ (如需轮询: 走 2.4 轮询模式，查询 task_id 状态直到完成或超时)
          ↓
[节点4] HTTP Node — 生成二维码（可选）
  ├─ IF 海报模板需要 QR 码:
  │   用 n8n QR Code 节点或第三方 API
  │   输出: qr_image_url
  └─ ELSE: 跳过
          ↓
[节点5] HTTP Node — 稿定模板 autofill 渲染
  ├─ URL: POST https://openapi.gaoding.com/api/v1/template/render (实际路径以 API 文档为准)
  ├─ Headers: Authorization + API Key/Secret
  ├─ Body: {
  │    template_id: brand_config.gaoding_templates[海报模板类型].template_id,
  │    variables: {
  │      bg_image: bg_image_url,
  │      title: fields.活动名称,
  │      date: 格式化后的活动时间,
  │      subtitle: fields.一句话简介,
  │      qr: qr_image_url (可选),
  │      guest_photo: (嘉宾海报时使用),
  │      guest_name: (嘉宾海报时使用),
  │      guest_title: (嘉宾海报时使用)
  │    }
  │  }
  ├─ Timeout: 30s, Retry: 2次
  ├─ 如稿定返回异步任务: 走 2.4 轮询模式(15s间隔)
  └─ 响应: poster_image_url
          ↓
[节点6] Code Node — 写入隐式标识元数据
  ├─ 语言: Python
  ├─ 脚本: scripts/write_metadata.py
  ├─ 输入: poster_image_url, run_id
  ├─ 写入内容 (PNG iTXt/XMP):
  │   ├─ 生成合成标签: "AIGC"
  │   ├─ 生成合成服务提供者: "通义万相 + XX开源社区"
  │   └─ 内容制作编号: run_id
  └─ 输出: poster_image_with_metadata_url
          ↓
[节点7] Code Node — 色彩校验 (IMG-BRAND-003, 🟡)
  ├─ 采样底图主色（取 5 个色块）
  ├─ 与 brand_config.json color_check.palette 比较
  ├─ IF 偏离 > tolerance(15):
  │   → 标记 IMG-BRAND-003 = warn, 附详情
  └─ ELSE: 通过
          ↓
[节点8] 自动检查 (调用检查器子流程)
  ├─ 图片类规则: IMG-BRAND-001,002,003 / IMG-TEXT-001,002,003,004 / IMG-MAP-001~004 / IMG-CONTENT-001,002 / IMG-COMPLY-001 / IMG-QUALITY-001,002
  ├─ 按 review_rules.json 注册表执行
  ├─ 确定性检查先跑（🔴 阻断项）, 概率检查后跑（🟡）
  └─ 产出检查报告: { blocking: N, warning: M, pass: K, details: [...] }
          ↓
[节点9] IF Node — 路由
  ├─ IF 检查报告 blocking > 0:
  │   → [节点9a] 飞书回写: 海报状态 = 失败(附阻断详情)
  │   → [节点9b] 飞书通知运营: 自动驳回原因 + 修改建议
  │   → [节点9c] 写台账(失败)
  │   → 停止
  ├─ IF 涉及地图 === 是 AND IMG-MAP-001~004 任一项未明确通过:
  │   → 强制标记 🟡 地图项为 warn (确保人一定看到)
  └─ ELSE:
      → [节点10] 飞书回写: 海报状态 = 待审, 海报预览 = poster_image_url, 检查报告 = report
      → [节点11] 飞书消息卡片推送给设计师（含预览 + 检查报告 + 通过/修改/驳回按钮）
      → [节点12] 写台账(成功)
          ↓
[Webhook Response] 200 OK (已在触发时立即返回)
```

## 关键细节

- **稿定模板内已固化**: Logo、字体(思源黑体)、装饰、AI 标识层("AI生成"文字)、排版——这些不需要代码处理
- **唯一代码点**: 节点6的隐式元数据写入(PNG iTXt/XMP)，配一次后不动
- **再生成**: 再生成意见拼入节点2的 prompt 组装
- **色彩策略**: 不强行 remap（会把图弄脏），仅校验 + 标 🟡 警告
