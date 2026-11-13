"""Read-only full-initial preservation and sample check; never assigns labels.

Optional --output writes an exclusive validation report, not a screening ledger.
"""
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import resume_screening as s


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--output', type=Path)
    args = cli.parse_args()
    can = s.RUN / 'canonical'
    inventory = s.inv()
    baseline = json.loads((s.RUN / 'admin/initial-screening-completion-20261113-01.json').read_text(encoding='utf-8'))
    initials = {}
    for pas in 'AB':
        path = can / f'pass-{pas}-original-initials.csv'
        assert s.sha(path) == baseline['final_original_pass_sha256'][path.name], ('COMPLETED_ORIGINAL_PASS_DRIFT', pas)
        rows = s.rd(path)
        initials[pas] = {row['publication_id']: row for row in rows}
        assert len(rows) == len(initials[pas]) == 18976
        assert set(initials[pas]) == set(inventory)
        for row in rows:
            for field in ['source_memberships_json', 'record_ids_json']:
                assert json.loads(row[field]) == json.loads(inventory[row['publication_id']][field]), ('MEMBERSHIP_DRIFT', pas, row['publication_id'], field)
    legacy, legacy_hashes = s.legacy()
    assert [len(legacy[pas]) for pas in 'AB'] == [2918, 2862]
    preserved = Counter()
    for pas in 'AB':
        raw = dict(legacy[pas])
        for worker in s.WORKERS:
            if worker[0] == pas:
                added = s.worker_rows(worker)
                assert not set(added) & set(raw), ('DUPLICATE_INITIAL_OWNER', worker)
                raw.update(added)
        assert set(raw) == set(inventory)
        for key, original in raw.items():
            exported = initials[pas][key]
            for field, value in original.items():
                if field in ['source_memberships_json', 'record_ids_json'] and not value:
                    assert exported.get('administrative_membership_join')
                    continue
                assert exported.get(field) == value, ('RAW_INITIAL_FIELD_CHANGED', pas, key, field)
            preserved[pas] += 1
    batches = s.idx()
    all_batch_ids = [key for batch in batches for key in batch['ids']]
    assert len(batches) == 380 and len(all_batch_ids) == len(set(all_batch_ids)) == 18958
    assert set(all_batch_ids) <= set(inventory) and len(set(inventory) - set(all_batch_ids)) == 18
    results = []
    for batch in batches:
        folder = s.RUN / 'paired' / batch['batch_id']
        ids = set(batch['ids'])
        paired = {pas: {row['publication_id']: row for row in s.rd(folder / f'pass-{pas}.csv')} for pas in 'AB'}
        for pas in 'AB':
            assert set(paired[pas]) == ids
            for key in ids:
                fields = set(paired[pas][key]) | set(initials[pas][key])
                for field in fields:
                    value = paired[pas][key].get(field, '')
                    joined = field in ['source_memberships_json', 'record_ids_json', 'administrative_membership_join'] and not value and initials[pas][key].get('administrative_membership_join')
                    assert joined or value == initials[pas][key].get(field, ''), ('PAIRED_ORIGINAL_DRIFT', batch['batch_id'], pas, key, field)
        source = {row['publication_id']: row for row in s.rd(folder / 'source.csv')}
        assert source == {key: inventory[key] for key in ids}, ('PAIRED_FROZEN_SOURCE_DRIFT', batch['batch_id'])
        candidates = [key for key in batch['ids'] if initials['A'][key]['eligibility'] == initials['B'][key]['eligibility'] == 'EXCLUDE']
        expected = sorted(candidates, key=lambda key: hashlib.sha256(('MedicalXR-20261111-v03:' + key).encode()).hexdigest())[:min(len(candidates), max(10, math.ceil(.1 * len(candidates))))]
        selection = json.loads((folder / 'audit-selection.json').read_text(encoding='utf-8'))
        assert selection['sample_ids'] == expected, ('FIXED_SAMPLE_ORDER_OR_SET_CHANGED', batch['batch_id'])
        results.append({'batch_id': batch['batch_id'], 'n': len(ids), 'agreed_exclusion_n': len(candidates), 'sample_ids': expected, 'selection_sha256': s.sha(folder / 'audit-selection.json'), 'exact_match': True})
    report = {'generated_at_utc': s.stamp(), 'inventory_sha256': s.EXPECTED_HASH, 'frozen_publication_ids': 18976, 'original_rows_preserved': dict(preserved), 'legacy_rows_preserved': {pas: len(legacy[pas]) for pas in 'AB'}, 'new_initial_rows_preserved': 32172, 'completed_pass_sha256': baseline['final_original_pass_sha256'], 'batch_n': len(results), 'fixed_sample_n': sum(len(row['sample_ids']) for row in results), 'batch_results': results, 'errors': [], 'scope': 'Mechanical original-field, source-membership, paired-source and deterministic sample preservation only. Does not source-assess scientific classifications, validate agreement as accuracy, or supply human verification.'}
    if args.output:
        s.js(args.output, report, exclusive=True)
    print(json.dumps({key: value for key, value in report.items() if key != 'batch_results'}))


if __name__ == '__main__':
    main()
