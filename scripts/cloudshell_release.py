"""Run in authenticated IBM Cloud Shell. Never prints tokens or secret data.

pip install --user ibm-code-engine-sdk==6.0.7
python scripts/cloudshell_release.py
Existing Orchestrate connections and external bearer configuration are preserved.
Private rollback/bootstrap records remain in Cloud Shell; no transfer is needed.
"""
import json
import os
import re
import secrets
import subprocess
import time
from pathlib import Path
from urllib.request import Request, urlopen

from ibm_cloud_sdk_core import ApiException
from ibm_cloud_sdk_core.authenticators import BearerTokenAuthenticator
from ibm_code_engine_sdk.code_engine_v2 import CodeEngineV2, AppPatch, EnvVarPrototype

PROJECT = 'f47a9050-4217-48b2-b630-84b442ed5ea4'
APP = 'telecom-network'
SOURCE = '15cd136a4b645e652dccc9785dbbec870741a43f'
IMAGE_REPOSITORY = 'private.ca.icr.io/wxo-training-698000u0qu/wxo-external-agent-trial'
SECRET = 'kai-outage-workflow-20261118'


def report(phase, **safe):
    print(json.dumps({'phase':phase, **safe}), flush=True)


def private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')
    path.chmod(0o600)


def deployment_image(run):
    details = run.get('status_details', {})
    digest = details.get('output_digest', '')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest) or details.get('git_commit_sha') != SOURCE:
        raise ValueError('Expected verified source commit and immutable image digest')
    return IMAGE_REPOSITORY+'@'+digest


def assert_unchanged(previous, current):
    if not previous.get('entity_tag') or current.get('entity_tag') != previous['entity_tag']:
        raise RuntimeError('Application configuration changed during build; no deployment')


def revision_ready(app, revision, image):
    return bool(revision and app.get('status') == 'ready' and
                app.get('image_reference') == image and
                app.get('status_details', {}).get('latest_ready_revision') == revision)


def assert_filming_ready(health, case):
    if (health.get('outage_demo_version') != '2026-11-18-en-v2' or
            health.get('agent_profile') != 'network_service'):
        raise RuntimeError('Expected English network application code was not observed')
    if (case.get('customer_name') != 'Nour Ahmed' or
            'customer_ar' in case or 'customer_en' in case or
            re.search(r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]',
                      json.dumps(case, ensure_ascii=False))):
        raise RuntimeError('Expected English-only customer case was not observed')
    if case.get('invoice_due_egp') != 900 or case.get('credit_receipt') is not None:
        raise RuntimeError('Unexpected synthetic starting invoice or receipt; investigate before filming')


def main():
    os.umask(0o077)
    auth = subprocess.run(['ibmcloud','iam','oauth-tokens','--output','json'],
                          check=True, capture_output=True, text=True)
    token = json.loads(auth.stdout)['iam_token'].removeprefix('Bearer ')
    ce = CodeEngineV2(authenticator=BearerTokenAuthenticator(token), version='2026-02-28')
    ce.set_service_url('https://api.ca-tor.codeengine.cloud.ibm.com/v2')
    ce.set_http_config({'timeout':45})
    project = ce.get_project(PROJECT).get_result()
    if project['name'] != 'ce-698000u0qu':
        raise RuntimeError('Unexpected project; no changes made')
    previous = ce.get_app(PROJECT, APP).get_result()
    private_json(Path('runtime/cloud-previous-app.json'), previous)
    report('verified_target', project=project['name'], app=APP, previous_image=previous['image_reference'])

    # Preserve all existing runtime secret references. Resolve only the already
    # authorized inbound token needed for the Orchestrate connection.
    reader = None
    for entry in previous.get('run_env_variables', []):
        kind = entry.get('type','')
        if entry.get('name') == 'AGENT_AUTH_TOKEN' and kind == 'literal':
            reader = entry.get('value')
        if kind in ('secret_key_reference','secret_full_reference'):
            if kind == 'secret_key_reference' and entry.get('name') != 'AGENT_AUTH_TOKEN':
                continue
            data = ce.get_secret(PROJECT, entry['reference']).get_result().get('data', {})
            if kind == 'secret_key_reference':
                reader = data.get(entry.get('key','AGENT_AUTH_TOKEN'))
            elif data.get('AGENT_AUTH_TOKEN'):
                reader = data['AGENT_AUTH_TOKEN']
    if not reader or reader == 'change-me-trial-token':
        raise RuntimeError('Configured inbound credential could not be safely resolved; no deployment')

    build_name = 'outage-'+SOURCE[:7]+'-'+str(int(time.time()))+'-'+secrets.token_hex(3)
    tagged_image = IMAGE_REPOSITORY+':'+build_name
    run = ce.create_build_run(PROJECT, name=build_name, output_image=tagged_image,
        output_secret='wxo-registry-access', source_type='git',
        source_url='https://github.com/AbdelrhmanMotaw3/wxo-external-agent-trial',
        source_revision=SOURCE, strategy_type='dockerfile', strategy_spec_file='Dockerfile',
        strategy_size='medium', timeout=600).get_result()
    report('build_started', build_run=run['name'], source_commit=SOURCE, image=tagged_image)
    deadline = time.monotonic()+720
    while time.monotonic() < deadline:
        run = ce.get_build_run(PROJECT, build_name).get_result()
        status = run.get('status')
        report('build_status', status=status)
        if status == 'succeeded':
            break
        if status in ('failed','cancelled'):
            raise RuntimeError('Image build failed; previous app revision unchanged')
        time.sleep(15)
    else:
        raise TimeoutError('Build still pending; previous app revision unchanged')
    image = deployment_image(run)

    try:
        existing = ce.get_secret(PROJECT, SECRET).get_result()
        writer = existing.get('data',{}).get('OUTAGE_WORKFLOW_TOKEN')
    except ApiException as error:
        if error.code != 404:
            raise
        writer = secrets.token_urlsafe(48)
        ce.create_secret(PROJECT, 'generic', SECRET, data={'OUTAGE_WORKFLOW_TOKEN':writer})
    if not writer or secrets.compare_digest(reader, writer):
        raise RuntimeError('Distinct workflow capability is required')

    current = ce.get_app(PROJECT, APP).get_result()
    assert_unchanged(previous, current)
    private_json(Path('runtime/cloud-previous-app.json'), current)
    allowed = {'key','name','prefix','reference','type','value'}
    env = [EnvVarPrototype.from_dict({k:v for k,v in e.items() if k in allowed})
           for e in current.get('run_env_variables', [])
           if e.get('name') != 'OUTAGE_WORKFLOW_TOKEN']
    env.append(EnvVarPrototype(name='OUTAGE_WORKFLOW_TOKEN', type='secret_key_reference',
                               reference=SECRET, key='OUTAGE_WORKFLOW_TOKEN'))
    old_revision = current.get('status_details', {}).get('latest_created_revision')
    updated = ce.update_app(PROJECT, APP, current['entity_tag'], AppPatch(
        image_reference=image, run_env_variables=env, scale_min_instances=1, scale_max_instances=1)).get_result()
    candidate = updated.get('status_details', {}).get('latest_created_revision')
    target_revision = candidate if candidate != old_revision else None
    report('deploy_started', app=APP, image=image)
    deadline = time.monotonic()+420
    while time.monotonic() < deadline:
        current = ce.get_app(PROJECT, APP).get_result()
        report('deploy_status', status=current.get('status'))
        created = current.get('status_details', {}).get('latest_created_revision')
        if target_revision is None and created != old_revision:
            target_revision = created
        if target_revision and created != target_revision:
            raise RuntimeError('A concurrent rollout was observed; investigate before continuing')
        if revision_ready(current, target_revision, image):
            break
        if current.get('status') == 'failed':
            raise RuntimeError('Deployment failed; previous image is in the private rollback file')
        time.sleep(10)
    else:
        raise TimeoutError('Deployment not yet ready')
    base = current['endpoint'].rstrip('/')
    if not base.startswith('https://'):
        base = 'https://'+base
    with urlopen(base+'/health', timeout=45) as response:
        health = json.load(response)
    with urlopen(Request(base+'/outage/cases/CASE-NOUR-001',
                        headers={'Authorization':'Bearer '+reader}), timeout=45) as response:
        case = json.load(response)
    assert_filming_ready(health, case)
    private_json(Path('runtime/cloud-bootstrap.json'), {
        'project_id':PROJECT, 'app':APP, 'source_commit':SOURCE,
        'base_url':base, 'reader_token':reader, 'workflow_token':writer})
    private_json(Path('runtime/cloud-deployment.json'), {
        'project':PROJECT, 'app':APP, 'image':image, 'endpoint':base,
        'revision':target_revision, 'source_commit':SOURCE})
    report('ready', endpoint=base, image=image, revision=target_revision,
           private_bootstrap_file=str(Path('runtime/cloud-bootstrap.json').resolve()))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # SDK exception bodies can include echoed request fields; do not print.
        safe_message = str(error) if type(error) in (RuntimeError,TimeoutError,ValueError) else None
        report('stopped', error_type=type(error).__name__, http_status=getattr(error,'code',None), reason=safe_message)
        raise SystemExit(1)
