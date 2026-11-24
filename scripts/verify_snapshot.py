#!/usr/bin/env python3
"""Static checks only: no imports of agent code, no network, no Docker start/build."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT/'agentic-banking-lab'

def main():
    counts = {'python_compiled':0,'banking_json_parsed':0,'toml_parsed':0,'source_hashes_checked':0}
    for project in json.loads((ROOT/'provenance/source-snapshot.json').read_text()):
        for item in project['files']:
            path = ROOT/project['directory']/item['path']
            assert path.is_file(), f'Missing source {path}'
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], f'Source drift {path}'
            counts['source_hashes_checked'] += 1
    for path in [*LAB.rglob('*.py'),ROOT/'integration/validation.py',* (ROOT/'scripts').glob('*.py')]:
        compile(path.read_bytes(),str(path),'exec')
        counts['python_compiled'] += 1
    for path in LAB.rglob('*.json'):
        json.loads(path.read_bytes())
        counts['banking_json_parsed'] += 1
    for path in [LAB/'pyproject.toml',LAB/'configs/appa.toml',ROOT/'OpenAPPA/Cargo.toml',ROOT/'OpenAPPA/Cargo.lock',ROOT/'OpenAPPA/appa-agent-python/Cargo.toml',ROOT/'OpenAPPA/appa-agent-python/pyproject.toml']:
        tomllib.loads(path.read_text())
        counts['toml_parsed'] += 1
    policy=tomllib.loads((LAB/'configs/appa.toml').read_text())
    assert len(policy['tool'])==14
    result={'counts':counts,'compose':{},'limitations':['No wheel rebuild or deployment performed','Search names mismatch: news_search/text_search vs policy news/text']}
    # Do not load an operator .env, or inherit operator interpolation values.
    env={k:os.environ[k] for k in ['PATH','HOME','DOCKER_CONFIG'] if k in os.environ}
    for file in ['docker-compose.yml','docker-compose.appa.yml']:
        cmd=['docker','compose','--env-file',os.devnull,'-f',str(LAB/file),'config','--format','json']
        run=subprocess.run(cmd,cwd=LAB,env=env,text=True,capture_output=True)
        if run.returncode:
            raise RuntimeError(f'Compose config failed for {file}: {run.stderr}')
        doc=json.loads(run.stdout)
        for name,service in doc['services'].items():
            build=service.get('build')
            if build:
                context=Path(build['context'])
                assert context==LAB, (name,context)
                assert (context/build.get('dockerfile','Dockerfile')).is_file()
                args=build.get('args') or {}
                package=args.get('SERVICE_PACKAGE')
                if package:
                    assert (context/'services'/package).is_dir()
                assert (context/'configs/appa.toml').is_file()
                assert (context/'vendor').is_dir()
            for volume in service.get('volumes',[]):
                if isinstance(volume,dict) and volume['type']=='bind':
                    source=Path(volume['source'])
                    assert source.is_relative_to(LAB) and source.exists(), (name,source)
        result['compose'][file]={'services':sorted(doc['services']),'service_count':len(doc['services']),'build_contexts_and_bind_sources':'PASS'}
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
