"""Run existing guarded status routines, failing at the first unsuccessful step."""
import json, subprocess, sys
from datetime import datetime,timezone
from pathlib import Path

root=Path('outputs/Medical-XR-Calibration-and-Full-Screening');a=root/'astra'
run=root/'resume-20261112';logs=run/'admin';logs.mkdir(exist_ok=True)
steps=['update_recheck_status.py','reconcile_progress.py','refresh_recent_modality_audit_overlay.py','update_modality_status.py','update_type_status.py','update_date_check_status.py','update_immersion_clarification_status.py','reconcile_progress.py','update_uncertainty_overlay.py','update_queues.py','refresh_access_metrics.py','update_original_ledgers.py','refresh_checkpoint.py']
out=[]
for step in steps:
    r=subprocess.run([sys.executable,str(a/step)],capture_output=True,text=True,encoding='utf-8',errors='replace')
    out.append({'step':step,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
    (logs/'guarded-legacy-refresh-log.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    if r.returncode:
        print(json.dumps({'failed_step':step,'returncode':r.returncode,'stderr':r.stderr}));sys.exit(r.returncode)
c=json.loads((a/'current-counts.json').read_text(encoding='utf-8'))
assert not c['errors']
assert (c['sol_complete'],c['terra_complete'],c['dual_complete'],c['adjudicated'])==(2918,2862,1854,1668)
receipt={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'Legacy saved checkpoints only; new fixed-pool work is in resume canonical adapter','legacy_counts':{k:c[k] for k in ['sol_complete','terra_complete','dual_complete','adjudicated','human_verified']},'steps_succeeded':steps}
(logs/'guarded-legacy-refresh-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt))
