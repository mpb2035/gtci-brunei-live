#!/usr/bin/env python3
"""
Consolidates all GTCI dashboard JSON files into one master JSON.
Canonical facts (scores, ranks, source, ministry) come from
ministry_source_mapping.json (the file already treated as source-of-truth
in index.html). Tab-specific narrative content is preserved as nested
sub-objects on each indicator record.
"""
import json
import copy

def load(fname):
    with open(fname) as f:
        return json.load(f)

msm = load('ministry_source_mapping.json')
all77 = load('all_77_indicators.json')
gtci_sectors_raw = load('gtciData.json')
src_groups_raw = load('srcGroupData.json')
edu_raw = load('educationData.json')
zero_raw = load('zeroData.json')  # 23-item superset (zero + near-zero)
zero_near_zero_raw = load('zero_near_zero_indicators.json')  # 16-item file that feeds the live tab; order matters

# ---- Backbone: 77 indicator records, deep-copied from ministry_source_mapping ----
indicators = {i['code']: copy.deepcopy(i) for i in msm['indicators']}

def to_number_or_none(v):
    """Coerce numeric-looking strings (e.g. srcGroupData.json's '95.02') to floats,
    while treating null/None and non-numeric placeholders (e.g. 'NA') as None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return v
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

report = {'rank_score_mismatches': [], 'missing_in_all77': [], 'missing_in_srcgroup': []}

# ---- Merge all_77_indicators.json: only genuinely additional fields ----
all77_by_code = {i['code']: i for i in all77}
for code, ind in indicators.items():
    a = all77_by_code.get(code)
    if not a:
        report['missing_in_all77'].append(code)
        continue
    # Flag (don't silently resolve) numeric discrepancies between files
    for field in ('bn_rank', 'sg_score', 'sg_rank', 'gap'):
        if ind.get(field) != a.get(field):
            report['rank_score_mismatches'].append({
                'code': code, 'name': ind['name'], 'field': field,
                'ministry_source_mapping': ind.get(field), 'all_77_indicators': a.get(field)
            })
    # Genuinely additional narrative/analysis fields not present in backbone schema.
    # NOTE: bn_rank/sg_score/sg_rank/gap are preserved here AS-IS from all_77_indicators.json
    # (not overwritten with the backbone's values) because this file and srcGroupData.json
    # agree with each other on these numbers but disagree with ministry_source_mapping.json
    # in ~300 cases (a pre-existing cross-file inconsistency, not something this consolidation
    # should silently resolve without a source-PDF verification pass). Preserving them here
    # keeps the "All 77 Indicators"/Overview tab KPIs numerically identical to before.
    ind['review_notes'] = {
        'comments': a.get('comments'),
        'insights': a.get('insights'),
        'source_score': a.get('source_score'),
        'source_rank': a.get('source_rank'),
        'data_period': a.get('data_period'),
        'trend': a.get('trend'),
        'analysis': a.get('analysis'),
        'bn_rank': a.get('bn_rank'),
        'sg_score': a.get('sg_score'),
        'sg_rank': a.get('sg_rank'),
        'gap': a.get('gap'),
        'name': a.get('name'),
        'pillar': a.get('pillar'),
        # NO_DATA semantics: ministry_source_mapping.json (the shared backbone field i.bn_score,
        # used by Ministry Overview/Edit and sector tabs) flattens all "no data" cases to 0.0.
        # all_77_indicators.json distinguishes null (truly missing) from 0 (confirmed literal
        # zero), which the All-77-Indicators/Overview tab's KPI counts depend on. Kept separate
        # here (not written back to the shared field) so Ministry tabs keep showing "0.0" exactly
        # as before, while this tab gets the richer null-vs-zero distinction it needs.
        'bn_score': a.get('bn_score'),
    }

# ---- Merge srcGroupData.json: group membership + group-specific action fields ----
source_groups = []
for g in src_groups_raw:
    source_groups.append({
        'id': g['id'], 'key': g['key'], 'label': g['label'],
        'emoji': g['emoji'], 'color': g['color'], 'context': g['context']
    })
    for gi_idx, gi in enumerate(g['indicators']):
        code = gi['code']
        ind = indicators.get(code)
        if not ind:
            report['missing_in_srcgroup'].append(code)
            continue
        ind['src_group_id'] = g['id']
        ind['src_group_order'] = gi_idx
        ind['source_group_notes'] = {
            'provider': gi.get('provider'),
            'mechanism': gi.get('mechanism'),
            'submission': gi.get('submission'),
            'included': gi.get('included'),
            'eligibility': gi.get('eligibility'),
            'action': gi.get('action'),
            'agency': gi.get('agency'),
            'contact': gi.get('contact'),
            'data_local': gi.get('data_local'),
            'est_score': gi.get('est_score'),
            'timeline': gi.get('timeline'),
            'priority': gi.get('priority'),
            'insight': gi.get('insight'),
            'name': gi.get('name'),
            'pillar': gi.get('pillar'),
            'bn_rank': gi.get('bn_rank'),
            'bn_score': (0 if gi.get('bn_score') == '0' else to_number_or_none(gi.get('bn_score'))),
        }

# ---- Merge gtciData.json: sector meta + per-indicator sector_views (multi) ----
sectors = []
sectors_meta = {'title': gtci_sectors_raw.get('title'), 'description': gtci_sectors_raw.get('description')}
for s in gtci_sectors_raw['sectors']:
    sectors.append({
        'id': s['id'], 'title': s['title'], 'context': s['context'],
        'wawasan_ref': s.get('wawasan_ref'), 'sg_benchmark': s.get('sg_benchmark'),
        'sector_target': s.get('sector_target'), 'new_indicators': s.get('new_indicators'),
        'policies': s.get('policies', []), 'intl_orgs': s.get('intl_orgs', []),
        'agencies': s.get('agencies', [])
    })
    for si_idx, si in enumerate(s['indicators']):
        code = si['code']
        ind = indicators.get(code)
        if not ind:
            continue
        ind.setdefault('sector_views', []).append({
            'sector_id': s['id'],
            'sector_order': si_idx,
            'why_relevant': si.get('why_relevant'),
            'remarks': si.get('remarks'),
            'brunei_agency': si.get('brunei_agency'),
            'intl_org': si.get('intl_org'),
            'suggested_policy': si.get('suggested_policy'),
            'timeline': si.get('timeline'),
            'bn_rank': si.get('brunei_rank'),
            'sg_score': si.get('sg_score'),
            'sg_rank': si.get('sg_rank'),
            'gap': si.get('gap'),
            'score_band': si.get('score_band'),
            'name': si.get('name'),
            'pillar': si.get('pillar'),
            'bn_score': si.get('brunei_score'),
        })

# ---- Merge educationData.json: group meta + per-indicator MOE notes ----
education_groups = []
for g in edu_raw['groups']:
    education_groups.append({'id': g['id'], 'label': g['label'], 'context': g['context']})
    for gi_idx, gi in enumerate(g['indicators']):
        code = gi['code']
        ind = indicators.get(code)
        if not ind:
            continue
        ind['moe_group_id'] = g['id']
        ind['moe_group_order'] = gi_idx
        ind['moe_notes'] = {
            'moe_link': gi.get('moe_link'),
            'current_status': gi.get('current_status'),
            'action_plan': gi.get('action_plan'),
            'contact': gi.get('contact'),
            'kpi': gi.get('kpi'),
            'policy_rec': gi.get('policy_rec'),
            'bn_rank': gi.get('brunei_rank'),
            'sg_score': gi.get('sg_score'),
            'sg_rank': gi.get('sg_rank'),
            'gap': gi.get('gap'),
            'score_band': gi.get('score_band'),
            'name': gi.get('name'),
            'pillar': gi.get('pillar'),
            'bn_score': gi.get('brunei_score'),
        }

education_meta = {
    'title': edu_raw.get('title'),
    'subtitle': edu_raw.get('subtitle'),
    'quickWins': edu_raw.get('quickWins', []),
    'strategicSummary': edu_raw.get('strategicSummary', {}),
}

# ---- Merge zeroData.json (23-item zero/near-zero superset) ----
zero_by_code = {z['code']: z for z in zero_raw}
zz_order = {z['code']: idx for idx, z in enumerate(zero_near_zero_raw)}
zero_near_zero_by_code = {z['code']: z for z in zero_near_zero_raw}
next_order = len(zz_order)
for code, z in zero_by_code.items():
    ind = indicators.get(code)
    if not ind:
        continue
    if code in zz_order:
        order = zz_order[code]
    else:
        order = next_order
        next_order += 1
    zz = zero_near_zero_by_code.get(code)
    ind['zero_fix_notes'] = {
        'priority': z.get('priority'),
        'fix_type': z.get('fix_type'),
        'fix_category': z.get('fix_category'),
        'est_gain': z.get('est_gain'),
        'data_exists': z.get('data_exists'),
        'fix_desc': z.get('fix_desc'),
        'timeline': z.get('timeline'),
        'order': order,
        # Own null-vs-zero score, decoupled from the shared backbone bn_score (which stays
        # 0.0 for Ministry tabs) — see the review_notes comment above for the same reasoning.
        'score': (0 if (zz and zz.get('score') == '0') else (zz.get('score') if zz else z.get('score'))),
    }

# ---- Assemble master document ----
master = {
    '_meta': {
        **msm['_meta'],
        'schema_version': '2.0-consolidated',
        'consolidation_note': 'Single source-of-truth file. Canonical facts (scores/ranks/source) '
                               'live once per indicator; tab-specific narrative content is nested '
                               '(source_group_notes, sector_views, moe_notes, zero_fix_notes, review_notes).'
    },
    'ministries': msm['ministries'],
    'data_sources': msm['data_sources'],
    'source_groups': source_groups,
    'sectors_meta': sectors_meta,
    'sectors': sectors,
    'education_meta': education_meta,
    'education_groups': education_groups,
    'indicators': list(indicators.values()),
}

with open('gtci_master_data.json', 'w', encoding='utf-8') as f:
    json.dump(master, f, ensure_ascii=False, indent=None, separators=(',', ':'))

print(f"Master JSON written: {len(master['indicators'])} indicators")
print(f"  ministries: {len(master['ministries'])}, data_sources: {len(master['data_sources'])}")
print(f"  source_groups: {len(master['source_groups'])}, sectors: {len(master['sectors'])}")
print(f"  education_groups: {len(master['education_groups'])}")
print()
print(f"Rank/score mismatches flagged (ministry_source_mapping vs all_77_indicators): {len(report['rank_score_mismatches'])}")
print(f"Codes missing in all_77_indicators.json: {report['missing_in_all77']}")
print(f"Codes missing in srcGroupData.json: {report['missing_in_srcgroup']}")

with open('merge_report.json', 'w') as f:
    json.dump(report, f, indent=2)
