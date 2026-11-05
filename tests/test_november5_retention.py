"""Focused November 5 regression fixtures, offline; no full build claimed."""
import json
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import url_lifecycle

ROOT = Path(url_lifecycle.__file__).parent

class November5RegressionTests(unittest.TestCase):
    def test_actual_reported_removals_block_before_and_pass_after_review(self):
        reviewed = json.loads((ROOT / 'url.lifecycle').read_text())
        added = json.loads((ROOT / 'tests/fixtures/retention-additions-20261105.json').read_text())
        baseline = copy.deepcopy(reviewed)
        added_slugs = {e['slug'] for e in added}
        baseline['retained_references'] = [e for e in baseline['retained_references'] if e['slug'] not in added_slugs]
        missing = {entry['canonical_url'] for entry in added}
        self.assertTrue(missing <= set(baseline['captured_public_urls']))
        for key in ('captured_public_urls', 'planned_release_urls', 'retirements',
                    'capture_at', 'captured_sitemap_sha256', 'captured_inventory_sha256'):
            self.assertEqual(baseline.get(key), reviewed.get(key))
        protected = set(baseline['captured_public_urls']) | set(baseline.get('planned_release_urls', []))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data.json').write_text(json.dumps({'items': []}))
            (root / 'sitemap.xml').write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
                ''.join('<url><loc>' + url + '</loc></url>' for url in sorted(protected - missing)) + '</urlset>')
            (root / 'url.lifecycle').write_text(json.dumps(baseline))
            with self.assertRaises(ValueError) as error:
                url_lifecycle.verify(root)
            for url in missing:
                self.assertIn(url, str(error.exception))
            (root / 'url.lifecycle').write_text(json.dumps(reviewed))
            url_lifecycle.render_retained(root)
            self.assertEqual(url_lifecycle.verify(root)['explicitly_retired'], [])
            for entry in added:
                body = (root / entry['canonical_url'].split('.com/', 1)[1] / 'index.html').read_text()
                self.assertIn('retained reference', body)
                self.assertIn(entry['primary_sources'][0]['url'], body)
                self.assertNotIn('The Diffusion Index', body)
                self.assertNotIn('aggregateRating', body)
                self.assertNotIn('class="rk"', body)

    def test_unsupported_schema_type_stays_blocked_before_output(self):
        rules = json.loads((ROOT / 'url.lifecycle').read_text())
        rules['retained_references'][0]['schema_type'] = 'Organization'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'url.lifecycle').write_text(json.dumps(rules))
            (root / 'data.json').write_text('{"items":[]}')
            (root / 'sitemap.xml').write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>')
            with self.assertRaisesRegex(ValueError, 'schema type'):
                url_lifecycle.render_retained(root)
            self.assertFalse((root / 'p').exists())
