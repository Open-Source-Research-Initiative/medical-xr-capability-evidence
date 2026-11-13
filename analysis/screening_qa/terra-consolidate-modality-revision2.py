import csv,re,pathlib
p=pathlib.Path('outputs/Medical-XR-Calibration-and-Full-Screening/terra')
def read(f):
 with open(f,encoding='utf-8-sig',newline='') as h:return list(csv.DictReader(h))
original={}
for f in [p/'calibration-v0.3.csv',*[p/f'B{i:04}.csv' for i in range(1,7)]]:
 for r in read(f): original[r['publication_id']]=r
receipt=(p/'modality-sweep-receipt-partial-v0.4.3.md').read_text(encoding='utf-8-sig')
ids=set(re.findall(r'P\d{7}',receipt))
for name in ['modality-sweep-locator-rechecks-v0.4.3.csv','modality-sweep-additional-rechecks-v0.4.3.csv']:
 ids.update(r['publication_id'] for r in read(p/name))
for n in range(130,281): ids.add(f'P{n:07}')
for i in range(1,7):
 for f in p.glob(f'modality-sweep-primary-batch{i}-*.csv'): ids.update(r['publication_id'] for r in read(f))
ids &= original.keys()
latest={}
files=[p/'field-recheck-v0.4.3.csv',p/'modality-sweep-locator-rechecks-v0.4.3.csv',p/'modality-sweep-additional-rechecks-v0.4.3.csv']+[p/f'modality-sweep-review-batch{i}-v0.4.3.csv' for i in range(1,10)]+[p/f'modality-sweep-primary-batch{i}-v0.4.3.csv' for i in range(1,6)]+[p/'modality-sweep-primary-batch6-v0.4.5.csv',p/'modality-sweep-primary-batch7-v0.4.5.csv',p/'modality-sweep-primary-batch8-v0.4.5.csv',p/'modality-disagreement-recheck-v0.4.5.csv']
for f in files:
 for r in read(f):
  k=r['publication_id']
  if k in ids: latest[k]=r|{'file':f.name}
out=[]
for k in sorted(ids):
 o=original[k]; r=latest.get(k)
 if r:
  stream=r.get('modality_stream') or r.get('corrected_modality_stream',''); comp=r.get('modality_components') or r.get('corrected_modality_components',''); basis=r.get('rationale',''); coord=r.get('source_coordinate',''); provenance=r['file']
 else:
  stream=o.get('modality_stream',''); comp=o.get('modality_components',''); basis='Retained after individual source review; '+o.get('rationale',''); coord=o.get('source_coordinate',k+'; inventory title/abstract'); provenance='modality-sweep-receipt-partial-v0.4.3.md or retrospective-checkpoint-v0.4.5.md; original '+o.get('batch_id','calibration')
 out.append(dict(publication_id=k,modality_stream=stream,modality_components=comp,basis=basis,source_coordinate=coord,recheck_provenance=provenance,human_verification='PENDING'))
f=p/'modality-sweep-consolidated-partial-v0.4.5-revision2.csv'
with f.open('w',encoding='utf-8',newline='') as h:
 w=csv.DictWriter(h,fieldnames=out[0].keys());w.writeheader();w.writerows(out)
print('checked_unique',len(out),'pending_among_original_318',318-len(out),'unpopulated_stream',sum(not r['modality_stream'] for r in out))


