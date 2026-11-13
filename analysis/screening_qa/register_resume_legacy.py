"""Ordered administrative registration. Does not supply scientific judgments."""
import csv, hashlib, json, shutil
from datetime import datetime, timezone
from pathlib import Path

root=Path('outputs/Medical-XR-Calibration-and-Full-Screening'); a=root/'astra'
run=root/'resume-20261112'; archive=run/'admin/legacy-before-registration'
archive.mkdir(parents=True,exist_ok=True)
def rd(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def backup(p):
    dst=archive/p.name
    if not dst.exists():shutil.copy2(p,dst)
def edit(name,old,new):
    p=a/name;backup(p);s=p.read_text(encoding='utf-8')
    if new in s:return
    assert old in s,(name,'PATCH_TARGET_MISSING')
    p.write_text(s.replace(old,new),encoding='utf-8')

backup(a/'current-artifacts.json')
edit('update_modality_status.py',' filters={}'," if who=='terra':paths += [out/who/n for n in ['B0033-recheck-v0.4.6.csv','B0033-supplemental-recheck-v0.4.6.csv','B0034-prompted-recheck-v0.4.6.csv','B0035-prompted-recheck-v0.4.6.csv'] if (out/who/n).exists()]\n filters={}")
edit('update_modality_status.py',"'B0031','B0032'))", "'B0031','B0032','B0033','B0034','B0035'))")
edit('update_type_status.py',' for p in paths:'," paths += [out/who/n for n in ['B0033-recheck-v0.4.6.csv','B0033-supplemental-recheck-v0.4.6.csv','B0034-recheck-v0.4.6.csv','B0034-prompted-recheck-v0.4.6.csv','B0035-prompted-recheck-v0.4.6.csv'] if (out/who/n).exists()]\n for p in paths:")
edit('refresh_recent_modality_audit_overlay.py',"'B0031','B0032']:","'B0031','B0032','B0033']:")
add="""requests += [('B0033_recheck_v0.4.6',f'P{i:07}') for i in [1620,1621,1624,1633,1634,1637,1641,1643,1645,1649,1650,1654,1655,1658,1660,1664]]
requests += [('B0034_recheck_v0.4.6',f'P{i:07}') for i in [1670,1674,1678,1682,1688,1689,1693,1694,1699,1700,1704,1705,1706,1709,1714]]
requests += [('B0035_recheck_v0.4.6',f'P{i:07}') for i in [1724,1725,1726,1732,1733,1735,1749,1751,1753,1754,1755,1757,1759]]
"""
edit('update_recheck_status.py','for kind,id in requests:',add+'for kind,id in requests:')
edit('update_recheck_status.py',"  if kind.startswith('B0025'):","  if kind.startswith(('B0033','B0034','B0035')):paths=list((out/who).glob(kind[:5]+'*recheck*.csv'))\n  if kind.startswith('B0025'):")
edit('update_recheck_status.py',"'B0031','B0032']:","'B0031','B0032','B0033','B0034','B0035']:")

registry=a/'date-correction-precedence.json';backup(registry)
j=json.loads(registry.read_text(encoding='utf-8'));known={e['file'] for e in j['entries']}
inventory={r['publication_id'] for r in rd(root/'shared/snapshot/provisional_publications.csv')}
receipt=[]
for who,names in [('sol',['B0034-date-source-recheck-v0.4.6.csv','B0057-date-source-v0.4.6.csv','B0058-date-source-v0.4.6.csv']),('terra',['B0034-date-recheck-v0.4.6.csv'])]:
    for name in names:
        p=root/who/name;rel=p.relative_to(root).as_posix()
        if not p.exists() or rel in known:continue
        rows=rd(p);ids=[r['publication_id'] for r in rows]
        assert ids and len(ids)==len(set(ids)) and set(ids)<=inventory
        batch={r['publication_id'] for r in rd(root/'shared/batches'/(name[:5]+'.csv'))}
        assert set(ids)<=batch
        if who=='sol':assert all(r.get('date_source') and r.get('date_basis') and r.get('date_source_status') for r in rows)
        # Raw Terra rows with inadequate date-check/extent fields remain pending;
        # registration never converts an index claim to source verification.
        entry={'reviewer':who,'precedence':max(e['precedence'] for e in j['entries'])+10,'file':rel,'sha256':sha(p),'basis':'Resume source-sidecar registration after exact frozen/batch ID, fields and hash checks. Preserve source-owned status and extent. Missing verification fields remain PENDING; no independent source verification implied.'}
        j['entries'].append(entry);known.add(rel);receipt.append(entry|{'ids':ids})
registry.write_text(json.dumps(j,indent=2),encoding='utf-8')
receipt_path=run/'admin/legacy-registration-receipt.json'
payload={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'date_entries':receipt,'B0033_order':['both original rechecks','Terra supplemental dissent','Sol focused followup PENDING'],'B0034':'Both targeted rechecks exist; raw date source extent limitations retained','B0035':'Terra targeted rechecks exist; legacy Sol prompted rechecks PENDING','files_after':{p.name:sha(p) for p in [a/'update_modality_status.py',a/'update_type_status.py',a/'update_recheck_status.py',a/'refresh_recent_modality_audit_overlay.py',registry]}}
if not receipt_path.exists():receipt_path.write_text(json.dumps(payload,indent=2),encoding='utf-8')
print(json.dumps(payload))
