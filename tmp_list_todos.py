import json
from pathlib import Path
p = Path(r'C:\Semptify\Semptify-FastAPI\tools\docs_todos.json')
data = json.loads(p.read_text(encoding='utf-8'))
for t in sorted((x for x in data if x.get('status') == 'pending'), key=lambda x: (x.get('priority','low'), x.get('target_model','')), reverse=True):
    print(f"{t['priority']} | {t.get('target_model','')} | {t['id']} | {t['file_path']} | {t['description'][:120]}")
