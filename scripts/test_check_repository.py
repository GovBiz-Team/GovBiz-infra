from pathlib import Path
import tempfile
import unittest

from check_repository import REQUIRED, file_errors, index_errors


class RepositoryBoundaryTests(unittest.TestCase):
    def make_repository(self, root):
        for name in REQUIRED:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Guide\n", encoding="utf-8")

    def test_application_gitlinks_and_source_are_rejected(self):
        entries = [
            "160000 " + "a" * 40 + " 0\tservices/GovBiz-web",
            "100644 " + "b" * 40 + " 0\tservices/GovBiz-ops/manage.py",
        ]
        self.assertEqual(len(index_errors(entries)), 2)

    def test_deployment_documents_are_allowed(self):
        self.assertEqual(index_errors(["100644 " + "a" * 40 + " 0\tREADME.md"]), [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            (root / "README.md").write_text(
                "[Guide](docs/repository-transition.md#local)\n[Remote](https://example.com)\n",
                encoding="utf-8",
            )
            self.assertEqual(file_errors(root), [])

    def test_legacy_checkout_is_not_read_but_root_compose_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repository(root)
            legacy = root / "services/GovBiz-web"
            legacy.mkdir(parents=True)
            (legacy / "README.md").write_text("[Broken](missing.md)\n", encoding="utf-8")
            self.assertEqual(file_errors(root), [])
            (root / "compose.yaml").write_text("services: {}\n", encoding="utf-8")
            self.assertEqual(len(file_errors(root)), 1)

    def test_missing_guides_and_invalid_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(len(file_errors(root)), len(REQUIRED))
            self.make_repository(root)
            (root / "README.md").write_text(
                "[Missing](docs/missing.md)\n[Outside](../outside.md)\n",
                encoding="utf-8",
            )
            self.assertEqual(len(file_errors(root)), 2)


if __name__ == "__main__":
    unittest.main()
