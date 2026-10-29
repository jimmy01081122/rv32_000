"""Finalize a fresh archive: verify bytes, share identical large payloads, add source dependencies."""
from pathlib import Path
import json,hashlib,gzip,datetime
root=Path.cwd();out=root/'docs/evidence/2026-10-29/lsu-b-complete-validation';index=out/'copy-inventory.json';data=json.loads(index.read_text());assert not (out/'SHA256SUMS').exists();sha=lambda raw:hashlib.sha256(raw).hexdigest()
for row in data['records']:
 stored=(out/row['destination']).read_bytes();assert sha(stored)==row['stored_sha256'];raw=gzip.decompress(stored) if row['encoding']=='gzip' else stored;assert sha(raw)==row['source_sha256'];assert sha((root/row['source']).read_bytes())==row['source_sha256'],row['source']
# Prefer each original final route over duplicate downstream input copies.
canonical={};changes=[]
for row in sorted(data['records'],key=lambda r:('5_1_grt.odb' not in r['destination'],r['destination'])):
 if row['stored_bytes']<1024*1024:continue
 key=(row['source_sha256'],row['encoding'])
 if key not in canonical:canonical[key]=row;continue
 prior=canonical[key]
 if row['destination']==prior['destination']:continue
 changes.append(dict(source=row['source'],removed_duplicate_payload=row['destination'],shared_payload=prior['destination'],source_sha256=row['source_sha256'],saved_bytes=row['stored_bytes']))
 row.update(destination=prior['destination'],stored_sha256=prior['stored_sha256'],stored_bytes=prior['stored_bytes'],shared_payload=True)
used={r['destination'] for r in data['records']}
for c in changes:
 if c['removed_duplicate_payload'] not in used:(out/c['removed_duplicate_payload']).unlink()
extra=['scripts/baseline_contract.py','scripts/experiment_contract.py','scripts/experiment_provenance.py','scripts/measure_post_lsu_baseline.py','scripts/measure_cpu_experiment.py','scripts/review_cpu_experiment.py','build/experiments/lsu-b-validation-v2/finalize_archive.py']
for name in extra:
 source=root/name;raw=source.read_bytes();destination=('runs/finalize_archive.py' if name.endswith('/finalize_archive.py') else 'inputs/'+name);target=out/destination;assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);data['records'].append(dict(source=name,destination=destination,encoding='copy',source_sha256=sha(raw),stored_sha256=sha(raw),source_bytes=len(raw),stored_bytes=len(raw)))
data['shared_payloads']=True;index.write_text(json.dumps(data,indent=2)+'\n');receipt=dict(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='identical source-byte payloads only; original source paths and every restored hash retained in copy inventory',saved_duplicate_bytes=sum(c['saved_bytes'] for c in changes),records=changes);(out/'payload-deduplication.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(records=len(data['records']),duplicates=len(changes),saved_bytes=receipt['saved_duplicate_bytes'])))
