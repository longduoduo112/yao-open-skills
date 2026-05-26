import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "add_copyright_comments.py"


class AddCopyrightCommentsTests(unittest.TestCase):
    def run_tool(self, skill_dir, *args):
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(skill_dir),
                "--project",
                "demo-skill",
                "--date",
                "2026-05-16",
                *args,
            ],
            check=True,
            text=True,
            capture_output=True,
        )

    def test_inserts_markdown_notice_after_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(
                "---\nname: demo-skill\ndescription: Use when testing.\n---\n\n# Demo\n",
                encoding="utf-8",
            )

            self.run_tool(skill_dir)

            text = skill_file.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\nname: demo-skill"))
            self.assertIn(
                "---\n\n<!--\nCopyright © 2026 姚金刚. All rights reserved.",
                text,
            )
            self.assertIn("Project: demo-skill", text)

    def test_is_idempotent_and_skips_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp)
            (skill_dir / "README.md").write_text("# Demo\n", encoding="utf-8")
            package_json = skill_dir / "package.json"
            package_json.write_text('{"name":"demo"}\n', encoding="utf-8")

            self.run_tool(skill_dir)
            self.run_tool(skill_dir)

            readme = (skill_dir / "README.md").read_text(encoding="utf-8")
            self.assertEqual(readme.count("Copyright © 2026 姚金刚"), 1)
            self.assertEqual(package_json.read_text(encoding="utf-8"), '{"name":"demo"}\n')

    def test_all_scope_formats_script_headers_and_preserves_shebang(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp)
            scripts = skill_dir / "scripts"
            scripts.mkdir()
            shell_file = scripts / "run.sh"
            shell_file.write_text("#!/usr/bin/env bash\nset -e\n", encoding="utf-8")
            ts_file = scripts / "tool.ts"
            ts_file.write_text("export const ok = true;\n", encoding="utf-8")

            self.run_tool(skill_dir, "--scope", "all")

            shell_text = shell_file.read_text(encoding="utf-8")
            ts_text = ts_file.read_text(encoding="utf-8")
            self.assertTrue(shell_text.startswith("#!/usr/bin/env bash\n# Copyright"))
            self.assertTrue(ts_text.startswith("/**\n * Copyright"))

    def test_dry_run_reports_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp)
            readme = skill_dir / "README.md"
            readme.write_text("# Demo\n", encoding="utf-8")

            result = self.run_tool(skill_dir, "--dry-run")

            self.assertIn("[dry-run]", result.stdout)
            self.assertEqual(readme.read_text(encoding="utf-8"), "# Demo\n")

    def test_all_scope_does_not_touch_test_helpers(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp)
            tests = skill_dir / "tests"
            tests.mkdir()
            helper = tests / "helper.py"
            helper.write_text("VALUE = 1\n", encoding="utf-8")

            self.run_tool(skill_dir, "--scope", "all")

            self.assertEqual(helper.read_text(encoding="utf-8"), "VALUE = 1\n")

    def test_generated_phrase_in_body_does_not_skip_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp)
            references = skill_dir / "references"
            references.mkdir()
            policy = references / "policy.md"
            policy.write_text(
                "# Policy\n\nGenerated files may say do not edit.\n",
                encoding="utf-8",
            )

            self.run_tool(skill_dir)

            self.assertIn(
                "Copyright © 2026 姚金刚",
                policy.read_text(encoding="utf-8"),
            )

    def test_copyright_template_in_body_does_not_count_as_existing_notice(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp)
            references = skill_dir / "references"
            references.mkdir()
            policy = references / "policy.md"
            policy.write_text(
                "# Policy\n\n```markdown\nCopyright © 2026 姚金刚. All rights reserved.\n```\n",
                encoding="utf-8",
            )

            self.run_tool(skill_dir)

            text = policy.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("<!--\nCopyright © 2026 姚金刚"))
            self.assertEqual(text.count("Copyright © 2026 姚金刚"), 2)


if __name__ == "__main__":
    unittest.main()
