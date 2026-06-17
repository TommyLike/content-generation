#!/usr/bin/env python3
"""通过 n8n REST API 创建活动内容生产工作流"""

import requests, json, uuid, sys

BASE = "http://127.0.0.1:8080"
N8N_URL = "http://tommylike.me:8080"

s = requests.Session()
resp = s.post(f"{BASE}/rest/login", json={"email": "admin@tommylike.me", "password": "Admin123!@#"})
if resp.status_code != 200:
    print(f"Login failed: {resp.text}")
    sys.exit(1)
print("✓ Logged in")


def wf(name, nodes, connections, active=False):
    """创建或更新 workflow"""
    # 先查是否有同名 workflow
    existing = s.get(f"{BASE}/rest/workflows").json().get("data", [])
    for w in existing:
        if w["name"] == name:
            # 删除旧的
            s.delete(f"{BASE}/rest/workflows/{w['id']}")
            print(f"  ⚡ Replaced old {name}")

    body = {"name": name, "nodes": nodes, "connections": connections, "active": active, "settings": {}}
    resp = s.post(f"{BASE}/rest/workflows", json=body)
    if resp.status_code != 200:
        print(f"  ✗ {name}: {resp.status_code} {resp.text[:300]}")
        return None
    d = resp.json()["data"]
    print(f"  ✓ {name}  [{d['id']}]")
    return d


# ============================================================
# WF-9: 错误处理工作流
# ============================================================
print("\n── WF-9 错误处理 ──")
wf9 = wf("WF-9 错误处理", [
    {"id": str(uuid.uuid4()), "name": "ErrorTrigger", "type": "n8n-nodes-base.errorTrigger", "position": [250, 300], "parameters": {}},
    {"id": str(uuid.uuid4()), "name": "NoOp", "type": "n8n-nodes-base.noOp", "position": [500, 300],
     "parameters": {"comment": "Placeholder: 解析错误 → 飞书回写失败状态 → 飞书告警工具封装者"}},
], {"ErrorTrigger": {"main": [[{"node": "NoOp", "type": "main", "index": 0}]]}})

# ============================================================
# WF-1: 海报子工作流
# ============================================================
print("\n── WF-1 海报子工作流 ──")
wf1 = wf("WF-1 海报子工作流", [
    {"id": str(uuid.uuid4()), "name": "Webhook", "type": "n8n-nodes-base.webhook",
     "position": [250, 300],
     "parameters": {"httpMethod": "POST", "path": "wf1-poster", "responseMode": "responseNode",
                    "options": {"responseData": "firstEntryJson"}}},
    {"id": str(uuid.uuid4()), "name": "ParseInput", "type": "n8n-nodes-base.set",
     "position": [500, 300],
     "parameters": {"values": {"string": [
         {"name": "run_id", "value": "={{ $json.body.run_id }}"},
         {"name": "record_id", "value": "={{ $json.body.record_id }}"},
         {"name": "活动名称", "value": "={{ $json.body.fields['活动名称'] }}"},
         {"name": "视觉风格", "value": "={{ $json.body.fields['视觉风格'] }}"},
         {"name": "海报模板", "value": "={{ $json.body.fields['海报模板'] }}"},
     ]}}},
    {"id": str(uuid.uuid4()), "name": "GenImage", "type": "n8n-nodes-base.noOp",
     "position": [750, 200],
     "parameters": {"comment": "⏳ Placeholder: HTTP Request → 通义万相 API 出底图。需 TONGYI_WANXIANG_API_KEY"}},
    {"id": str(uuid.uuid4()), "name": "GaodingRender", "type": "n8n-nodes-base.noOp",
     "position": [750, 400],
     "parameters": {"comment": "⏳ Placeholder: HTTP Request → 稿定 autofill API。需 GAODING_API_KEY"}},
    {"id": str(uuid.uuid4()), "name": "ComplianceWriteback", "type": "n8n-nodes-base.noOp",
     "position": [1000, 300],
     "parameters": {"comment": "⏳ Placeholder: Code(Python)→写PNG隐式元数据 → 自动检查 → 飞书回写「待审」"}},
], {"Webhook": {"main": [[{"node": "ParseInput", "type": "main", "index": 0}]]},
    "ParseInput": {"main": [[{"node": "GenImage", "type": "main", "index": 0}]]},
    "GenImage": {"main": [[{"node": "GaodingRender", "type": "main", "index": 0}]]},
    "GaodingRender": {"main": [[{"node": "ComplianceWriteback", "type": "main", "index": 0}]]},
})

# ============================================================
# WF-2: 推文子工作流
# ============================================================
print("\n── WF-2 推文子工作流 ──")
wf2 = wf("WF-2 推文子工作流", [
    {"id": str(uuid.uuid4()), "name": "Webhook", "type": "n8n-nodes-base.webhook",
     "position": [250, 300],
     "parameters": {"httpMethod": "POST", "path": "wf2-article", "responseMode": "responseNode"}},
    {"id": str(uuid.uuid4()), "name": "ParseInput", "type": "n8n-nodes-base.set",
     "position": [500, 300],
     "parameters": {"values": {"string": [
         {"name": "run_id", "value": "={{ $json.body.run_id }}"},
         {"name": "record_id", "value": "={{ $json.body.record_id }}"},
         {"name": "活动名称", "value": "={{ $json.body.fields['活动名称'] }}"},
         {"name": "活动详情", "value": "={{ $json.body.fields['活动详情'] }}"},
         {"name": "推文类型", "value": "={{ $json.body.fields['推文类型'] }}"},
     ]}}},
    {"id": str(uuid.uuid4()), "name": "DifyGenerate", "type": "n8n-nodes-base.noOp",
     "position": [750, 300],
     "parameters": {"comment": "⏳ Placeholder: HTTP Request → Dify workflow API。需部署 Dify + 配置 API Key"}},
    {"id": str(uuid.uuid4()), "name": "CheckWriteback", "type": "n8n-nodes-base.noOp",
     "position": [1000, 300],
     "parameters": {"comment": "⏳ Placeholder: 事实核查→追加AI标识→自动检查→飞书回写「待审」"}},
], {"Webhook": {"main": [[{"node": "ParseInput", "type": "main", "index": 0}]]},
    "ParseInput": {"main": [[{"node": "DifyGenerate", "type": "main", "index": 0}]]},
    "DifyGenerate": {"main": [[{"node": "CheckWriteback", "type": "main", "index": 0}]]},
})

# ============================================================
# WF-0: 派发器 (核心!)
# ============================================================
print("\n── WF-0 派发器 ──")
wf0 = wf("WF-0 派发器", [
    {"id": str(uuid.uuid4()), "name": "FeishuWebhook", "type": "n8n-nodes-base.webhook",
     "position": [250, 300],
     "parameters": {"httpMethod": "POST", "path": "wf0-dispatcher", "responseMode": "responseNode",
                    "options": {"responseData": "firstEntryJson"}}},
    {"id": str(uuid.uuid4()), "name": "GenRunId", "type": "n8n-nodes-base.set",
     "position": [500, 300],
     "parameters": {"values": {"string": [
         {"name": "run_id", "value": "={{ $json.body.record_id + '-' + $now.format('X') }}"},
         {"name": "record_id", "value": "={{ $json.body.record_id }}"},
         {"name": "content_version", "value": 1},
     ]}}},
    {"id": str(uuid.uuid4()), "name": "Validate", "type": "n8n-nodes-base.set",
     "position": [750, 300],
     "parameters": {"values": {"boolean": [
         {"name": "hasName", "value": "={{ !!$json.body.fields['活动名称'] }}"},
         {"name": "hasTime", "value": "={{ !!$json.body.fields['活动时间'] }}"},
         {"name": "hasIntro", "value": "={{ !!$json.body.fields['一句话简介'] }}"},
         {"name": "hasDetail", "value": "={{ !!$json.body.fields['活动详情'] }}"},
         {"name": "valid", "value": "={{ !!$json.body.fields['活动名称'] && !!$json.body.fields['活动时间'] && !!$json.body.fields['一句话简介'] && !!$json.body.fields['活动详情'] }}"},
     ]}}},
    # Fire-and-forget HTTP calls to sub-workflows
    {"id": str(uuid.uuid4()), "name": "CallWF1", "type": "n8n-nodes-base.httpRequest",
     "position": [1000, 150],
     "parameters": {"method": "POST", "url": f"{N8N_URL}/webhook/wf1-poster",
                    "sendBody": True, "bodyParameters": {"parameters": [
                        {"name": "run_id", "value": "={{ $json.run_id }}"},
                        {"name": "record_id", "value": "={{ $json.record_id }}"},
                        {"name": "content_version", "value": "={{ $json.content_version }}"},
                        {"name": "fields", "value": "={{ $json.body.fields }}"},
                    ]},
                    "options": {"timeout": 10000, "retryOnFail": True, "maxTries": 3}}},
    {"id": str(uuid.uuid4()), "name": "CallWF2", "type": "n8n-nodes-base.httpRequest",
     "position": [1000, 350],
     "parameters": {"method": "POST", "url": f"{N8N_URL}/webhook/wf2-article",
                    "sendBody": True, "bodyParameters": {"parameters": [
                        {"name": "run_id", "value": "={{ $json.run_id }}"},
                        {"name": "record_id", "value": "={{ $json.record_id }}"},
                        {"name": "content_version", "value": "={{ $json.content_version }}"},
                        {"name": "fields", "value": "={{ $json.body.fields }}"},
                    ]},
                    "options": {"timeout": 10000, "retryOnFail": True, "maxTries": 3}}},
    {"id": str(uuid.uuid4()), "name": "FeishuWriteback", "type": "n8n-nodes-base.noOp",
     "position": [1000, 550],
     "parameters": {"comment": "⏳ Placeholder: 飞书 PUT 记录 → 海报状态=生成中, 推文状态=生成中。需 FEISHU_APP_ID/SECRET"}},
], {"FeishuWebhook": {"main": [[{"node": "GenRunId", "type": "main", "index": 0}]]},
    "GenRunId": {"main": [[{"node": "Validate", "type": "main", "index": 0}]]},
    "Validate": {"main": [[{"node": "FeishuWriteback", "type": "main", "index": 0},
                          {"node": "CallWF1", "type": "main", "index": 0},
                          {"node": "CallWF2", "type": "main", "index": 0}]]},
})

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
print("✅ All workflows created!")
print("=" * 60)
print(f"""
访问: {N8N_URL}

Webhook URLs:
  WF-0 派发器:        {N8N_URL}/webhook/wf0-dispatcher
  WF-1 海报子工作流:  {N8N_URL}/webhook/wf1-poster
  WF-2 推文子工作流:  {N8N_URL}/webhook/wf2-article

测试:
  curl -X POST {N8N_URL}/webhook/wf0-dispatcher \\
    -H 'Content-Type: application/json' \\
    -d '{{"record_id":"r001","fields":{{"活动名称":"测试","活动时间":"2026-07-15","一句话简介":"test","活动详情":"详情"}}}}'
""")
