"""
Minimal test for the page rendering app. Run with:

    python -m api.test
"""

import re
import sys
import unittest


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
        from api import index as api_index
        from api.index import app, PAGES, build_page

        cls.api_index = api_index
        # staticmethod keeps this a plain function; assigning a function to
        # a class attribute would turn it into a bound method and pass cls.
        cls.build_page = staticmethod(build_page)
        cls.PAGES = PAGES
        cls.app = app
        cls.client = app.test_client()

    def test_every_page_renders(self):
        for name in self.PAGES:
            with self.subTest(page=name):
                r = self.client.get(f"/{self.PAGES[name]}")
                self.assertEqual(r.status_code, 200)

    def test_index_is_served_at_root(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_header_and_footer_are_injected(self):
        html = self.build_page("index")
        # the shared markup is now inline...
        self.assertIn('id="navbar"', html)
        self.assertIn("Firm Foundation Academy. All rights reserved.", html)
        # ...and neither placeholder survives
        self.assertNotIn('<div id="header-placeholder"></div>', html)
        self.assertNotIn('<div id="footer-placeholder"></div>', html)

    def test_injection_happens_exactly_once(self):
        html = self.build_page("index")
        self.assertEqual(html.count('id="navbar"'), 1)
        self.assertEqual(html.count("Firm Foundation Academy. All rights reserved."), 1)

    def test_client_side_fetch_is_removed(self):
        for name in self.PAGES:
            with self.subTest(page=name):
                html = self.build_page(name)
                self.assertNotIn("fetch('header.html')", html)
                self.assertNotIn("fetch('footer.html')", html)

    def test_active_nav_is_marked(self):
        html = self.build_page("academics")
        # the academics link should carry the active class
        m = re.search(r'<a[^>]*data-nav="academics"[^>]*>', html)
        self.assertIsNotNone(m)
        self.assertIn("text-secondary", m.group(0))
        self.assertIn("font-bold", m.group(0))

    def test_only_one_active_nav_link(self):
        html = self.build_page("about")
        actives = re.findall(r'<a[^>]*data-nav="[^"]+"[^>]*text-secondary font-bold', html)
        # desktop + mobile pairs, so exactly 2 for the current page
        self.assertEqual(len(actives), 2)

    def test_health_reports_presence_not_values(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertEqual(body["status"], "ok")

        # every secret must be reported as a boolean, never as a value
        for name, present in body["configured"].items():
            self.assertIsInstance(present, bool, f"{name} leaked as {present!r}")

        # and a planted secret must not appear anywhere in the response
        import os

        os.environ["GEMINI_API_KEY"] = "sentinel-value-do-not-leak"
        try:
            r2 = self.client.get("/health")
            self.assertNotIn("sentinel-value-do-not-leak", r2.get_data(as_text=True))
        finally:
            del os.environ["GEMINI_API_KEY"]

    def test_unknown_page_is_404(self):
        self.assertEqual(self.client.get("/nope.html").status_code, 404)
        self.assertEqual(self.client.get("/does-not-exist").status_code, 404)

    def test_path_traversal_is_blocked(self):
        r = self.client.get("/../.env")
        self.assertIn(r.status_code, (400, 404))

    def test_local_env_file_is_never_served(self):
        """The real risk: a developer keeps a .env beside index.html locally."""
        import pathlib

        env = pathlib.Path(self.api_index.BASE_DIR) / ".env"
        self.assertFalse(env.exists(), "test would clobber a real .env")
        env.write_text("SUPABASE_SERVICE_ROLE_KEY=real-secret\n", encoding="utf-8")
        try:
            for url in ("/.env", "/.env.local", "/api/index.py",
                        "/vercel.json", "/.gitignore", "/DEPLOY.md"):
                with self.subTest(url=url):
                    r = self.client.get(url)
                    self.assertEqual(r.status_code, 404)
                    self.assertNotIn("real-secret", r.get_data(as_text=True))
        finally:
            env.unlink()

    def test_local_env_file_is_loaded_even_with_a_windows_bom(self):
        """Notepad/PowerShell save UTF-8 with a BOM; the key must still match."""
        import os
        import pathlib

        env = pathlib.Path(self.api_index.PAGES_DIR) / ".env"
        self.assertFalse(env.exists(), "test would clobber a real .env")
        env.write_bytes(
            "\ufeffSUPABASE_URL=https://bom-test.supabase.co\n".encode("utf-8")
        )
        os.environ.pop("SUPABASE_URL", None)
        try:
            self.api_index._load_local_env()
            self.assertEqual(
                os.environ.get("SUPABASE_URL"), "https://bom-test.supabase.co"
            )
        finally:
            os.environ.pop("SUPABASE_URL", None)
            env.unlink()

    def test_real_assets_are_still_served(self):
        for name in ("ffa.webp", "founder1.webp", "founder2.webp"):
            with self.subTest(asset=name):
                r = self.client.get(f"/{name}")
                try:
                    self.assertEqual(r.status_code, 200)
                finally:
                    r.close()

    def test_include_files_are_not_served_directly(self):
        self.assertEqual(self.client.get("/header.html").status_code, 404)
        self.assertEqual(self.client.get("/footer.html").status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
