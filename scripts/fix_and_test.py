#!/usr/bin/env python3
"""Fix workflows: remove Respond nodes, use lastNode mode, test WF-0"""
import requests, json, uuid, subprocess, time

BASE = 'http://127.0.0.1:8080'
N8N_URL = 'http://tommylike.me:8080'
s = requests.Session()
s.post(f'{BASE}/rest/login', json={'email':'admin@tommylike.me','password':'Admin123!@#'})

for w in s.get(f'{BASE}/rest/workflows').json()['data']:
    if 'TEST' in w['name'] or 'WF-9' in w['name']:
        continue

    wid = w['id']
    full = s.get(f'{BASE}/rest/workflows/{wid}').json()['data']
    name = full['name']

    # Remove RespondToWebhook nodes
    full['nodes'] = [n for n in full['nodes']
                     if n['type'] != 'n8n-nodes-base.respondToWebhook']

    # Set webhook to lastNode mode
    for node in full['nodes']:
        if node['type'] == 'n8n-nodes-base.webhook':
            node['parameters']['responseMode'] = 'lastNode'
            if 'webhookId' not in node:
                node['webhookId'] = str(uuid.uuid4())
            print(f'  fixed: {name}')

    # Clean connections
    node_names = {n['name'] for n in full['nodes']}
    for src_name in list(full['connections'].keys()):
        if src_name not in node_names:
            del full['connections'][src_name]
            continue
        main_conns = full['connections'][src_name].get('main', [])
        new_conns = []
        for branch in main_conns:
            new_branch = [c for c in branch if c['node'] in node_names]
            if new_branch:
                new_conns.append(new_branch)
        full['connections'][src_name]['main'] = new_conns

    patch = {'versionId': full['versionId'], 'name': full['name'],
             'nodes': full['nodes'], 'connections': full['connections'],
             'settings': full.get('settings', {}), 'active': True}
    resp = s.patch(f'{BASE}/rest/workflows/{wid}', json=patch)
    print(f'  PATCH {resp.status_code}: {name}')

# Restart n8n
print('\nRestarting n8n...')
subprocess.run(['docker', 'compose', 'stop', 'n8n'],
               cwd='/home/tommylikehu/workspace/content-generation/deploy')
time.sleep(3)
subprocess.run(['docker', 'compose', 'start', 'n8n'],
               cwd='/home/tommylikehu/workspace/content-generation/deploy')
time.sleep(15)

# Test WF-0
print('\n=== Test WF-0 ===')
payload = json.dumps({
    "record_id": "r006",
    "fields": {
        "活动名称": "终测", "活动时间": "2026-07-15",
        "一句话简介": "端到端测试", "活动详情": "详情",
        "视觉风格": "科技蓝", "海报模板": "event_preview",
        "推文类型": "活动招募"
    }
})
r = subprocess.run(['curl', '-s', '-w', '\nHTTP:%{http_code}', '-X', 'POST',
                    f'{N8N_URL}/webhook/wf0-dispatcher',
                    '-H', 'Content-Type: application/json', '-d', payload],
                   capture_output=True, text=True)
print(f'Response: {r.stdout}')

time.sleep(5)

print('\n=== Executions ===')
rr = s.get(f'{BASE}/rest/executions', params={'limit': 12})
for e in rr.json()['data']['results']:
    st = e['status']
    nm = e.get('workflowName', '?')
    t = e.get('startedAt', '')[:19]
    print(f'  [{st:8s}] {nm:25s} {t}')
