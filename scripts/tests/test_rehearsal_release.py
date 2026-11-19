import unittest
from scripts import cloudshell_rehearsal_release as release


class RehearsalReleaseTests(unittest.TestCase):
    def test_patch_preserves_secrets_environment_and_scaling(self):
        self.assertEqual(release.image_only_patch('repo@sha256:verified').to_dict(),
                         {'image_reference': 'repo@sha256:verified'})

    def test_build_requires_exact_reviewed_commit_and_digest(self):
        source = 'a' * 40
        run = {'status_details': {'git_commit_sha': source, 'output_digest': 'sha256:' + 'b' * 64}}
        self.assertEqual(release.deployment_image(run, source),
                         release.IMAGE_REPOSITORY + '@sha256:' + 'b' * 64)
        for changed in ({'git_commit_sha': 'c' * 40}, {'output_digest': 'mutable-tag'}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                release.deployment_image({'status_details': {**run['status_details'], **changed}}, source)

    def test_concurrent_edit_and_old_ready_revision_do_not_pass(self):
        with self.assertRaises(RuntimeError):
            release.assert_unchanged({'entity_tag': 'v1'}, {'entity_tag': 'v2'})
        app = {'status': 'ready', 'image_reference': 'new-image',
               'status_details': {'latest_ready_revision': 'old'}}
        self.assertFalse(release.revision_ready(app, 'new', 'new-image'))

    def test_health_requires_session_aware_version(self):
        health = {'outage_demo_version': release.VERSION, 'agent_profile': 'network_service',
                  'rehearsal_sessions': True, 'compensation_type':'bonus_data','compensation_gb':20}
        release.assert_health(health)
        for changes in ({'rehearsal_sessions': False}, {'outage_demo_version': '2026-11-18-en-v2'},
                        {'agent_profile': 'customer_account'},{'compensation_gb':90},
                        {'compensation_type':'invoice_credit'}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeError):
                release.assert_health({**health, **changes})
