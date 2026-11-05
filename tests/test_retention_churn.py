"""Regression checks for reviewed discovery-window churn; no network."""
import json
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
import url_lifecycle
import public_assets

ROOT = Path(url_lifecycle.__file__).parent
RULES = json.loads((ROOT / 'url.lifecycle').read_text())
NS = '{http://www.sitemaps.org/schemas/sitemap/0.9}'

class RetentionChurnTests(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory)
        entries = RULES['retained_references']
        rules = {k: RULES[k] for k in ('host', 'site_name', 'detail_prefix')}
        rules.update(captured_public_urls=['https://' + RULES['host'] + '/'] + [e['canonical_url'] for e in entries], retained_references=entries)
        (root / 'url.lifecycle').write_text(json.dumps(rules))
        (root / 'data.json').write_text(json.dumps({'items': []}))
        (root / 'index.html').write_text('<!doctype html><title>Home</title>')
        (root / 'sitemap.xml').write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://' + RULES['host'] + '/</loc></url></urlset>')
        (root / 'public.assets').write_text(json.dumps({'host': RULES['host'], 'root_files': ['index.html'], 'legacy_source_paths': []}))
        return root, rules, entries

    def test_all_reviewed_missing_records_keep_routes_schema_identity_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root, rules, entries = self.fixture(directory)
            self.assertEqual(url_lifecycle.render_retained(root), len(entries))
            self.assertEqual(url_lifecycle.verify(root)['explicitly_retired'], [])
            receipt = public_assets.seal(root)
            for e in entries:
                relative = e['canonical_url'].split('.com/', 1)[1] + 'index.html'
                body = (root / relative).read_text()
                self.assertIn('retained reference | ' + RULES['site_name'], body)
                self.assertIn('href="/">' + RULES['site_name'], body)
                self.assertIn('outside the current ranked discovery snapshot', body)
                self.assertIn('Catalog snapshot supporting this reference', body)
                self.assertIn(e['last_catalog_snapshot'], body)
                self.assertEqual(body.count('<h1>'), 1)
                self.assertIn('rel="canonical" href="' + e['canonical_url'] + '"', body)
                schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', body, re.S)[1])
                self.assertEqual(schema['@type'], e.get('schema_type', 'SoftwareSourceCode'))
                self.assertEqual(schema['url'], e['canonical_url'])
                self.assertEqual(schema['codeRepository' if e.get('schema_type', 'SoftwareSourceCode') == 'SoftwareSourceCode' else 'sameAs'], e['repository'])
                self.assertNotIn('aggregateRating', schema)
                self.assertIn(relative, receipt['public_files'])
                self.assertIn(relative, public_assets.collect_public_files(root))
            self.assertNotIn('url.lifecycle', receipt['public_files'])
            self.assertNotIn('data.json', receipt['public_files'])
            target = root / (entries[0]['canonical_url'].split('.com/', 1)[1] + 'index.html')
            target.write_text(target.read_text() + '<!-- changed -->')
            with self.assertRaisesRegex(ValueError, 'stale'):
                public_assets.collect_public_files(root)

    def test_record_reentry_is_owned_by_ranked_generator(self):
        with tempfile.TemporaryDirectory() as directory:
            root, rules, entries = self.fixture(directory)
            url_lifecycle.render_retained(root)
            e = entries[0]
            path = root / (e['canonical_url'].split('.com/', 1)[1] + 'index.html')
            path.write_text('fresh ranked generator output')
            (root / 'data.json').write_text(json.dumps({'items': [{'slug': e['slug']}]}))
            url_lifecycle.render_retained(root)
            self.assertEqual(path.read_text(), 'fresh ranked generator output')

    def test_unreviewed_removal_stays_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root, rules, entries = self.fixture(directory)
            rules['captured_public_urls'].append('https://' + RULES['host'] + '/p/unreviewed-project/')
            (root / 'url.lifecycle').write_text(json.dumps(rules))
            url_lifecycle.render_retained(root)
            with self.assertRaisesRegex(ValueError, 'retention/retirement'):
                url_lifecycle.verify(root)

    def test_offhost_or_wrong_prefix_reference_rejected(self):
        for bad in ('https://other.invalid/p/project/', 'https://' + RULES['host'] + '/m/project/'):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as directory:
                root, rules, entries = self.fixture(directory)
                rules['retained_references'][0]['canonical_url'] = bad
                (root / 'url.lifecycle').write_text(json.dumps(rules))
                with self.assertRaisesRegex(ValueError, 'unsafe or mismatched'):
                    url_lifecycle.render_retained(root)
                # fixture uses the parsed module data, so restore for later cases.
                RULES['retained_references'] = json.loads((ROOT / 'url.lifecycle').read_text())['retained_references']

    def test_retained_output_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root, rules, entries = self.fixture(directory)
            path = root / (entries[0]['canonical_url'].split('.com/', 1)[1] + 'index.html')
            path.parent.mkdir(parents=True)
            outside = root / 'outside.html'
            outside.write_text('preserve')
            path.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'symlinks'):
                url_lifecycle.render_retained(root)
            self.assertEqual(outside.read_text(), 'preserve')

if __name__ == '__main__':
    unittest.main()
