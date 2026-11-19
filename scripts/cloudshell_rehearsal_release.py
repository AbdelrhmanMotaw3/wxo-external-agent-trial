"""User-operated Cloud Shell release. Image-only update; never reads secrets.

python scripts/cloudshell_rehearsal_release.py --source <exact reviewed commit>
"""
import argparse
import json
import re
import secrets
import subprocess
import time
from urllib.request import urlopen

PROJECT = 'f47a9050-4217-48b2-b630-84b442ed5ea4'
APP = 'telecom-network'
REPOSITORY = 'https://github.com/AbdelrhmanMotaw3/wxo-external-agent-trial'
IMAGE_REPOSITORY = 'private.ca.icr.io/wxo-training-698000u0qu/wxo-external-agent-trial'
ENDPOINT = 'https://telecom-network.2gqohspjx3cv.ca-tor.codeengine.appdomain.cloud'
VERSION = '2026-11-19-en-v3'


def report(phase, **safe):
    print(json.dumps({'phase': phase, **safe}), flush=True)


def deployment_image(run, source):
    details = run.get('status_details', {})
    digest = details.get('output_digest', '')
    if (not re.fullmatch(r'[a-f0-9]{40}', source)
            or details.get('git_commit_sha') != source
            or not re.fullmatch(r'sha256:[a-f0-9]{64}', digest)):
        raise ValueError('Build must match the exact source commit and an immutable image digest')
    return IMAGE_REPOSITORY + '@' + digest


def assert_unchanged(previous, current):
    if not previous.get('entity_tag') or current.get('entity_tag') != previous['entity_tag']:
        raise RuntimeError('Application configuration changed during build; no deployment')


def image_only_patch(image):
    from ibm_code_engine_sdk.code_engine_v2 import AppPatch
    return AppPatch(image_reference=image)


def revision_ready(app, revision, image):
    return bool(revision and app.get('status') == 'ready'
                and app.get('image_reference') == image
                and app.get('status_details', {}).get('latest_ready_revision') == revision)


def assert_health(health):
    if (health.get('outage_demo_version') != VERSION
            or health.get('agent_profile') != 'network_service'
            or health.get('rehearsal_sessions') is not True):
        raise RuntimeError('Expected conversation-aware network application was not observed')


def main(source):
    from ibm_cloud_sdk_core.authenticators import BearerTokenAuthenticator
    from ibm_code_engine_sdk.code_engine_v2 import CodeEngineV2
    if not re.fullmatch(r'[a-f0-9]{40}', source):
        raise ValueError('A full reviewed source commit is required')
    auth = subprocess.run(['ibmcloud', 'iam', 'oauth-tokens', '--output', 'json'],
                          check=True, capture_output=True, text=True)
    token = json.loads(auth.stdout)['iam_token'].removeprefix('Bearer ')
    ce = CodeEngineV2(authenticator=BearerTokenAuthenticator(token), version='2026-02-28')
    ce.set_service_url('https://api.ca-tor.codeengine.cloud.ibm.com/v2')
    ce.set_http_config({'timeout': 45})
    project = ce.get_project(PROJECT).get_result()
    if project.get('name') != 'ce-698000u0qu':
        raise RuntimeError('Unexpected project; no changes made')
    previous = ce.get_app(PROJECT, APP).get_result()
    base = previous.get('endpoint', '').rstrip('/')
    if not base.startswith('https://'):
        base = 'https://' + base
    if base != ENDPOINT:
        raise RuntimeError('Unexpected application endpoint; no changes made')
    report('verified_target', project=project['name'], app=APP,
           previous_image=previous['image_reference'])

    build_name = 'rehearsal-' + source[:7] + '-' + secrets.token_hex(4)
    run = ce.create_build_run(PROJECT, name=build_name,
        output_image=IMAGE_REPOSITORY + ':' + build_name,
        output_secret='wxo-registry-access', source_type='git', source_url=REPOSITORY,
        source_revision=source, strategy_type='dockerfile', strategy_spec_file='Dockerfile',
        strategy_size='medium', timeout=600).get_result()
    report('build_started', build_run=run['name'], source_commit=source)
    deadline = time.monotonic() + 720
    while time.monotonic() < deadline:
        run = ce.get_build_run(PROJECT, build_name).get_result()
        report('build_status', status=run.get('status'))
        if run.get('status') == 'succeeded':
            break
        if run.get('status') in ('failed', 'cancelled'):
            raise RuntimeError('Build failed; previous application unchanged')
        time.sleep(15)
    else:
        raise TimeoutError('Build still pending; previous application unchanged')
    image = deployment_image(run, source)
    current = ce.get_app(PROJECT, APP).get_result()
    assert_unchanged(previous, current)
    old_revision = current.get('status_details', {}).get('latest_created_revision')
    updated = ce.update_app(PROJECT, APP, current['entity_tag'], image_only_patch(image)).get_result()
    candidate = updated.get('status_details', {}).get('latest_created_revision')
    revision = candidate if candidate != old_revision else None
    report('deploy_started', app=APP, image=image, previous_image=previous['image_reference'])
    deadline = time.monotonic() + 420
    while time.monotonic() < deadline:
        current = ce.get_app(PROJECT, APP).get_result()
        created = current.get('status_details', {}).get('latest_created_revision')
        if revision is None and created != old_revision:
            revision = created
        if revision and created != revision:
            raise RuntimeError('Concurrent rollout observed; inspect before continuing')
        report('deploy_status', status=current.get('status'))
        if revision_ready(current, revision, image):
            break
        if current.get('status') == 'failed':
            raise RuntimeError('Deployment failed; previous image is recorded above')
        time.sleep(10)
    else:
        raise TimeoutError('Deployment not yet ready')
    with urlopen(ENDPOINT + '/health', timeout=45) as response:
        assert_health(json.load(response))
    report('ready', endpoint=ENDPOINT, image=image, revision=revision,
           source_commit=source, rehearsal_sessions=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    args = parser.parse_args()
    try:
        main(args.source)
    except Exception as error:
        # SDK errors can echo environment values: print only controlled messages.
        reason = str(error) if type(error) in (RuntimeError, TimeoutError, ValueError) else None
        report('stopped', error_type=type(error).__name__, http_status=getattr(error, 'code', None),
               reason=reason)
        raise SystemExit(1)
