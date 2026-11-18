import unittest
from scripts import cloudshell_release as release


class ReleaseContractTests(unittest.TestCase):
    def test_filming_readiness_requires_english_fresh_case(self):
        health = {'outage_demo_version':'2026-11-18-en-v2', 'agent_profile':'network_service'}
        case = {'customer_name':'Nour Ahmed', 'invoice_due_egp':900, 'credit_receipt':None,
                'history':[{'event':'Internet outage reported'}]}
        release.assert_filming_ready(health, case)
        for changes in ({'customer_ar':'legacy'}, {'invoice_due_egp':810},
                        {'credit_receipt':{'status':'applied'}},
                        {'history':[{'event':'\u062a\u062c\u0631\u0628\u0629'}]}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                release.assert_filming_ready(health, {**case, **changes})
        with self.assertRaises(RuntimeError):
            release.assert_filming_ready({**health, 'outage_demo_version':'2026-11-18-v1'}, case)

    def test_deployment_uses_digest_and_verified_source(self):
        run = {'status_details':{'output_digest':'sha256:'+'a'*64,'git_commit_sha':release.SOURCE}}
        self.assertEqual(release.deployment_image(run), release.IMAGE_REPOSITORY+'@sha256:'+'a'*64)
        with self.assertRaises(ValueError):
            release.deployment_image({'status_details':{'output_digest':'mutable-tag','git_commit_sha':release.SOURCE}})
        with self.assertRaises(ValueError):
            release.deployment_image({'status_details':{'output_digest':'sha256:'+'a'*64,'git_commit_sha':'another-commit'}})

    def test_same_image_concurrent_config_change_aborts(self):
        previous = {'entity_tag':'v1','image_reference':'old-image'}
        with self.assertRaises(RuntimeError):
            release.assert_unchanged(previous, {'entity_tag':'v2','image_reference':'old-image'})

    def test_old_ready_revision_does_not_prove_new_rollout(self):
        app = {'status':'ready','image_reference':'repo@sha256:new',
               'status_details':{'latest_created_revision':'new','latest_ready_revision':'old'}}
        self.assertFalse(release.revision_ready(app, 'new', 'repo@sha256:new'))
        app['status_details']['latest_ready_revision'] = 'new'
        self.assertTrue(release.revision_ready(app, 'new', 'repo@sha256:new'))
