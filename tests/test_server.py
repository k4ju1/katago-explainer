"""HTTP contract for the standalone demonstration, without an engine or GPU."""

from http.server import ThreadingHTTPServer
import json
import threading
from types import SimpleNamespace
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from explainer.server import Application, PROJECT_DIR, handler_for


class StaticServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(Application(SimpleNamespace())))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def test_page_and_assets_have_explicit_types_and_no_cache(self):
        for route, mime in (('/', 'text/html'), ('/styles.css', 'text/css'),
                            ('/app.js', 'text/javascript')):
            with self.subTest(route=route), urlopen(self.base_url + route, timeout=2) as response:
                self.assertEqual(response.headers.get_content_type(), mime)
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
                self.assertTrue(response.read())

    def test_arbitrary_files_and_path_traversal_are_not_served(self):
        for route in ('/README.md', '/web/app.js', '/../explainer/engine.py', '/%2e%2e/README.md'):
            with self.subTest(route=route), self.assertRaises(HTTPError) as error:
                urlopen(self.base_url + route, timeout=2)
            self.assertEqual(error.exception.code, 404)

    def test_other_origins_cannot_read_local_resources(self):
        request = Request(self.base_url + '/app.js', headers={'Origin': 'https://example.com'})
        with self.assertRaises(HTTPError) as error:
            urlopen(request, timeout=2)
        self.assertEqual(error.exception.code, 403)

    def test_classic_example_returns_target_position(self):
        with urlopen(self.base_url + '/api/example/joseki/mi', timeout=2) as response:
            example = json.load(response)
        self.assertEqual(example['move_index'], 16)
        self.assertIn("Mi's Flying Dagger", example['sgf'])
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base_url + '/api/example/joseki/missing', timeout=2)
        self.assertEqual(error.exception.code, 404)

    def test_invalid_game_identifiers_produce_http_error_instead_of_disconnect(self):
        for value in (None, '', {}, []):
            request = Request(self.base_url + '/api/analyze',
                              data=json.dumps({'game_id': value, 'move_index': 0}).encode('utf-8'),
                              headers={'Content-Type': 'application/json'})
            with self.subTest(value=value), self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=2)
            self.assertEqual(error.exception.code, 400)
            self.assertIn('Game ID', json.load(error.exception)['error']['en'])


class GameRetentionTests(unittest.TestCase):
    def test_default_sample_remains_analyzable_after_upload_eviction(self):
        app = Application(SimpleNamespace())
        sgf = (PROJECT_DIR / 'examples' / 'shusaku-demo.sgf').read_text(encoding='utf-8')
        uploaded = [app.add_game(sgf)['id'] for _ in range(13)]
        self.assertEqual(len(app.games), 12)
        self.assertIn(app.state()['game']['id'], app.games)
        self.assertIn(uploaded[-1], app.games)
        self.assertNotIn(uploaded[0], app.games)


if __name__ == '__main__':
    unittest.main()
