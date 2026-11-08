"""Offline regression for the reviewed November 8 discovery rotation."""
import copy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
import url_lifecycle

ROOT = Path(url_lifecycle.__file__).resolve().parent

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

class November8RetentionTests(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory).resolve()
        rules = json.loads((ROOT / 'url.lifecycle').read_text())
        expected = json.loads((ROOT / 'tests/fixtures/retention-additions-20261108.json').read_text())
        missing = {e['canonical_url'] for e in expected['entries']}
        protected = set(rules['captured_public_urls']) | set(rules.get('planned_release_urls', []))
        self.assertTrue(missing <= protected)
        (root / 'url.lifecycle').write_text(json.dumps(rules))
        (root / 'data.json').write_text('{"items":[]}')
        (root / 'sitemap.xml').write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join('<url><loc>' + u + '</loc></url>' for u in sorted(protected - missing)) + '</urlset>')
        return root, rules, expected

    def test_rotation_blocks_before_review_and_preserves_dated_pages_after_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root, rules, expected = self.fixture(directory)
            baseline = copy.deepcopy(rules)
            baseline['retained_references'] = baseline['retained_references'][:expected['previous_reference_count']]
            (root / 'url.lifecycle').write_text(json.dumps(baseline))
            url_lifecycle.render_retained(root)
            with self.assertRaisesRegex(ValueError, 'retention/retirement') as raised:
                url_lifecycle.verify(root)
            for e in expected['entries']:
                self.assertIn(e['canonical_url'], str(raised.exception))
            (root / 'url.lifecycle').write_text(json.dumps(rules))
            url_lifecycle.render_retained(root)
            for e in expected['entries']:
                self.assertIn(e['canonical_url'], url_lifecycle.urls(root))
                body = (root / e['canonical_url'].split('.com/', 1)[1] / 'index.html').read_text()
                self.assertIn('retained reference | ' + rules['site_name'], body)
                self.assertIn('outside the current ranked discovery snapshot', body)
                self.assertIn('rel="canonical" href="' + e['canonical_url'] + '"', body)
                self.assertIn(e['last_catalog_snapshot'], body)
                self.assertIn('2026-11-08', body)
                for source in e['primary_sources']:
                    self.assertIn(source['url'], body)
                schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', body, re.S)[1])
                self.assertEqual(schema['@type'], e.get('schema_type', 'SoftwareSourceCode'))
                self.assertEqual(schema['url'], e['canonical_url'])
                self.assertNotIn('aggregateRating', schema)
                self.assertNotIn('class="rk"', body)
            self.assertEqual(url_lifecycle.verify(root)['explicitly_retired'], [])

    def test_guard_and_all_previous_decisions_are_unchanged(self):
        rules = json.loads((ROOT / 'url.lifecycle').read_text())
        expected = json.loads((ROOT / 'tests/fixtures/retention-additions-20261108.json').read_text())
        self.assertEqual(digest({k:v for k,v in rules.items() if k != 'retained_references'}), expected['unchanged_policy_sha256'])
        self.assertEqual(digest(rules['retained_references'][:expected['previous_reference_count']]), expected['previous_references_sha256'])
        self.assertEqual(rules['retained_references'][expected['previous_reference_count']:], expected['entries'])
        self.assertEqual(len({e['slug'] for e in rules['retained_references']}), len(rules['retained_references']))

    def test_new_sources_are_pinned_to_reviewed_revisions(self):
        expected = json.loads((ROOT / 'tests/fixtures/retention-additions-20261108.json').read_text())
        for entry in expected['entries']:
            pinned = [s for s in entry['primary_sources'] if s.get('commit_sha')]
            self.assertTrue(pinned)
            for source in pinned:
                self.assertRegex(source['commit_sha'], r'^[0-9a-f]{40}$')
                self.assertIn('/blob/' + source['commit_sha'] + '/', source['url'])
                self.assertRegex(source['blob_sha'], r'^[0-9a-f]{40}$')
                self.assertRegex(source['evidence_sha256'], r'^[0-9a-f]{64}$')

    def test_each_reviewed_reentry_remains_owned_by_ranked_generator(self):
        with tempfile.TemporaryDirectory() as directory:
            root, rules, expected = self.fixture(directory)
            (root / 'data.json').write_text(json.dumps({'items':[{'slug':e['slug']} for e in expected['entries']]}))
            for e in expected['entries']:
                path = root / e['canonical_url'].split('.com/', 1)[1] / 'index.html'
                path.parent.mkdir(parents=True); path.write_text('current ranked generator output')
            url_lifecycle.render_retained(root)
            for e in expected['entries']:
                path = root / e['canonical_url'].split('.com/', 1)[1] / 'index.html'
                self.assertEqual(path.read_text(), 'current ranked generator output')

    def test_unknown_removal_still_blocks_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root, rules, expected = self.fixture(directory)
            rules['captured_public_urls'].append('https://' + rules['host'] + '/p/unreviewed-november8-removal/')
            (root / 'url.lifecycle').write_text(json.dumps(rules))
            url_lifecycle.render_retained(root)
            with self.assertRaisesRegex(ValueError, 'unreviewed-november8-removal'):
                url_lifecycle.verify(root)

if __name__ == '__main__':
    unittest.main()
