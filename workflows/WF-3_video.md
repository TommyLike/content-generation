# WF-3 视频子工作流 — 节点级规格（可选模块）

> 设计文档 v3.2，第 2.3 节 + 第 3C 层

## 基本信息

| 属性 | 值 |
|------|-----|
| Workflow 名称 | WF-3 视频子工作流 |
| 触发方式 | HTTP Webhook（被 WF-0 调用，仅「生成视频=是」时触发） |
| 运行时长 | ~5min |
| 超时设置 | 12min（硬上限） |
| Error Workflow | WF-9 |

## 节点清单

```
[Webhook Trigger] 接收 WF-0 调用
  ├─ HTTP Method: POST
  ├─ Webhook URL Path: /wf3-video
  ├─ Authentication: Header Auth (X-Internal-Token)
  ├─ Response Mode: Respond Immediately (200)
  └─ 输出: run_id, record_id, content_version, fields
          ↓
[节点1] Set Node — 确定视频参数
  ├─ 视频类型 = fields.视频类型 (活动预热短视频 | 嘉宾金句切片 | 科普动画)
  ├─ 视频时长 = fields.视频时长 (15s | 30s | 60s)
  ├─ 旁白风格 = fields.视频旁白风格 (专业沉稳 | 活力轻快 | 科技未来感)
  └─ 输出: video_type, duration, narration_style
          ↓
[节点2] HTTP Node — 提交 AI 视频生成任务 (即梦/可灵)
  ├─ URL: POST https://api.jimeng.ai/... (实际路径以 API 文档为准)
  ├─ Headers: Authorization + API Key
  ├─ Body: { prompt: 从活动信息拼装, duration, style, ... }
  ├─ Timeout: 30s, Retry: 2次
  └─ 响应: task_id
          ↓
[节点3→3a→3b] 轮询循环 (详见 2.4 轮询模式)
  ├─ Wait Node: 30s
  ├─ HTTP Node: GET task_status
  ├─ IF completed → 取视频 URL
  ├─ IF failed → 状态「生成超时失败」+ 回写 + 告警
  └─ IF pending + 次数 < 20 → 回到 Wait
          ↓
(视频产出后)
          ↓
[节点4] 视频品牌固化 (模板套用)
  ├─ 片头: brand-assets/video/intro_3s.mp4 (品牌动画)
  ├─ LUT 调色: brand-assets/video/lut_brand.cube
  ├─ Logo 角标: brand-assets/video/logo_overlay.png (右下角全程)
  ├─ 片尾 CTA: brand-assets/video/outro_3s.mp4 (品牌定格 + 行动号召)
  └─ (可通过 FFmpeg 节点或第三方 API 完成)
          ↓
[节点5] Code Node — 写入 AI 显式 + 隐式标识
  ├─ 显式: 片尾(持续显示) + 底部(全片) "AI生成"
  ├─ 隐式: MP4 metadata 五要素 1-3
  │   ├─ 生成合成标签: "AIGC"
  │   ├─ 生成合成服务提供者: "即梦/可灵 + XX开源社区"
  │   └─ 内容制作编号: run_id
  └─ 输出: video_with_metadata_url
          ↓
[节点6] 自动检查
  ├─ 视频类规则: VID-BRAND-001~005 / VID-TEXT-001 / VID-AUDIO-001,002 / VID-COMPLY-001 / VID-MAP-001 / VID-QUALITY-001
  └─ 产出检查报告
          ↓
[节点7] IF Node — 路由
  ├─ IF blocking > 0:
  │   → 状态=失败, 通知, 台账
  └─ ELSE:
      → 状态=待审, 通知设计师, 台账
```

## 注意事项

- 本模块为**可选**，团队按需启用
- 视频 API 调用成本高，建议 Phase 1 以后启动
- AI 视频文字渲染容易出错 → VID-TEXT-001 强制 OCR + 人审
- 轮询 20 次 × 30s = 最大 10min，配合 12min 硬上限
