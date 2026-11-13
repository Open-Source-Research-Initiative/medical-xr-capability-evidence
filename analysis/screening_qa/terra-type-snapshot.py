import csv,pathlib,re
p=pathlib.Path('outputs/Medical-XR-Calibration-and-Full-Screening/terra')
def rows(f):
 with f.open(encoding='utf-8-sig',newline='') as h:return list(csv.DictReader(h))
a=rows(p/'evidence-type-recheck-v0.4.4-partial.csv'); latest={r['publication_id']:r for r in a}; original=[]
for f in [p/'calibration-v0.3.csv',*[p/f'B{i:04}.csv' for i in range(1,7)]]: original.extend(r['publication_id'] for r in rows(f))
assert len(latest)==318 and len(set(original))==318 and set(latest)==set(original) and all(re.fullmatch(r'P\d{7}',k) for k in latest)
f=p/'evidence-type-current-v0.4.6.csv'
with f.open('w',encoding='utf-8',newline='') as h:
 w=csv.DictWriter(h,fieldnames=a[0].keys());w.writeheader();w.writerows(latest[k] for k in sorted(latest))
print('318 unique IDs, exact source set match')
