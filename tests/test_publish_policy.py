import unittest
from scripts.publish_policy import should_publish


class PublishPolicyTests(unittest.TestCase):
    def test_only_current_main_push_can_publish(self):
        self.assertTrue(should_publish('push', 'refs/heads/main', 'new', 'new'))
        for event, ref, candidate, head in [
            ('push', 'refs/heads/main', 'old', 'new'),
            ('pull_request', 'refs/pull/1/merge', 'new', 'new'),
            ('push', 'refs/heads/feature', 'new', 'new'),
        ]:
            with self.subTest(event=event, ref=ref, candidate=candidate):
                self.assertFalse(should_publish(event, ref, candidate, head))
