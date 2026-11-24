#!/usr/bin/env python3
"""Local heuristic secret scan. No uploads; never prints candidate secret values.

Default: working files. --history scans every blob reachable from local refs too.
--private-env compares secret-looking values from an operator-owned env file in
memory only. Reviewed synthetic matches are exact path/rule/value fingerprints.
Not a replacement for review or a comprehensive DLP product.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    'private-key-or-certificate': rb'-----BEGIN (?:[A-Z ]*PRIVATE KEY|CERTIFICATE)-----',
    'provider-key': rb'\b(?:sk-(?:or-v1-|proj-)?[A-Za-z0-9_-]{25,}|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,}|AKIA[A-Z0-9]{16})\b',
    'jwt': rb'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',
    'slack-token': rb'\bxox[baprs]-[A-Za-z0-9-]{15,}',
    'credential-url': rb'https?://[^\s/<>"\']+:[^\s/<>"\']+@[^\s/<>"\']+',
}
FORBIDDEN_SUFFIXES = {'.whl', '.pyc', '.pyo', '.so', '.p12', '.pfx', '.pem', '.key', '.crt', '.sqlite', '.sqlite3', '.db', '.log', '.dump'}
SECRET_NAME = re.compile(r'(?:API_KEY|SECRET|PASSWORD|TOKEN|PRIVATE_KEY|ENCRYPTION_KEY)', re.I)

def env_values(path):
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.removeprefix('export ').split('=', 1)
        value = value.strip().strip('\"\'')
        if SECRET_NAME.search(key) and len(value) >= 8:
            result[key] = value.encode()
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true')
    parser.add_argument('--private-env', type=Path)
    args = parser.parse_args()
    allow = json.loads((ROOT/'provenance/synthetic-secret-allowlist.json').read_text())
    allowed = {(i['path'], i['rule'], i['match_sha256'], i['file_sha256']) for i in allow if i.get('reason') and i['reason'] != 'UNREVIEWED'}
    # Values in the preserved educational example are known demo defaults, not
    # newly supplied provider/production secrets. Count them separately.
    demo = set(env_values(ROOT/'agentic-banking-lab/.env.example').values())
    private = env_values(args.private_env) if args.private_env else {}
    private = {k:v for k,v in private.items() if v not in demo}
    items = []
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or '.git' in p.relative_to(ROOT).parts:
            continue
        if any(x in p.relative_to(ROOT).parts for x in ['.venv','__pycache__','.pytest_cache','target','node_modules']):
            continue
        items.append(('worktree', p.relative_to(ROOT).as_posix(), p.read_bytes()))
    blob_count = 0
    if args.history:
        objects = subprocess.check_output(['git','rev-list','--objects','--all'],cwd=ROOT,text=True).splitlines()
        for line in objects:
            oid, _, path = line.partition(' ')
            kind = subprocess.check_output(['git','cat-file','-t',oid],cwd=ROOT,text=True).strip()
            if kind == 'blob':
                items.append(('history:'+oid, path, subprocess.check_output(['git','cat-file','blob',oid],cwd=ROOT)))
                blob_count += 1
    issues, reviewed = [], 0
    for source, path, data in items:
        p = Path(path)
        if p.name == '.env' or (p.name.startswith('.env.') and not p.name.endswith('.example')) or p.suffix in FORBIDDEN_SUFFIXES or p.name in {'auth.json','credentials.json','id_rsa','id_ed25519'}:
            issues.append({'source':source,'path':path,'rule':'forbidden-artifact'})
        for rule, pattern in RULES.items():
            for match in re.finditer(pattern,data):
                fingerprint = hashlib.sha256(match.group()).hexdigest()
                if (path,rule,fingerprint,hashlib.sha256(data).hexdigest()) in allowed:
                    reviewed += 1
                    continue
                issues.append({'source':source,'path':path,'rule':rule,'line':data[:match.start()].count(b'\n')+1,'match_sha256':fingerprint})
        for key, value in private.items():
            if value in data:
                issues.append({'source':source,'path':path,'rule':'private-env-value','key_name':key})
    print(json.dumps({'worktree_files':len(items)-blob_count,'history_blobs':blob_count,'reviewed_synthetic_matches':reviewed,'private_secret_values_checked':len(set(private.values())),'known_demo_values_excluded':len(set(env_values(args.private_env).values()) & demo) if args.private_env else 0,'unreviewed_issues':issues,'verdict':'PASS' if not issues else 'BLOCK'},indent=2))
    return bool(issues)

if __name__ == '__main__':
    sys.exit(main())
