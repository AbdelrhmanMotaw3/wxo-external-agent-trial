"""Print native control metadata only, excluding model reasoning and content."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from ibm_watsonx_orchestrate.client.utils import instantiate_client
from ibm_watsonx_orchestrate.client.observability.traces.traces_client import TracesClient

client = instantiate_client(TracesClient)
now = datetime.now(timezone.utc)
raw = client._get(client.base_endpoint+'/observations', params={
    'traceId':sys.argv[1], 'page':1, 'limit':100,
    'fromStartTime':(now-timedelta(hours=2)).isoformat(), 'toStartTime':now.isoformat()})
rows = []
for item in raw.get('data',raw.get('observations',[])):
    if item.get('name') != 'controls.execute':
        continue
    attrs = item.get('metadata',{}).get('attributes',{})
    rows.append({'name':item['name'], 'attributes':{
        k:v for k,v in attrs.items() if k.startswith('controls.')}})
path = Path('runtime')/('controls-'+sys.argv[1]+'.json')
path.parent.mkdir(exist_ok=True)
path.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False,indent=2))
