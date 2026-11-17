"""Self-check for standards.py. Run: python tests/test_standards.py (exits non-zero on failure)."""
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "skills" / "setup-standards" / "templates"
sys.path.insert(0, str(TEMPLATES / ".githooks"))
import standards as s  # noqa: E402

CFG = tomllib.loads((TEMPLATES / "standards.toml").read_text(encoding="utf-8"))


def test_commit_messages():
    assert s.message_problem("feat(api): add export", CFG) is None
    assert s.message_problem("fix!: drop legacy flag", CFG) is None
    assert s.message_problem("Merge branch 'dev'", CFG) is None
    assert "not '<type>" in s.message_problem("added stuff", CFG)
    assert "not '<type>" in s.message_problem("feature: add x", CFG)
    assert "chars" in s.message_problem("feat: " + "x" * 80, CFG)


def test_sizes_skip_excluded_and_binary():
    numstat = "10\t5\tsrc/a.py\n0\t700\tsrc/old.py\n900\t0\tpackage-lock.json\n-\t-\tlogo.png"
    assert s.added_lines(numstat, CFG["size"]["exclude"]) == (10, 1)
    big = "\n".join(f"40\t0\tsrc/f{i}.py" for i in range(8))
    assert "320 added lines" in s.size_problem(big, CFG)
    assert s.size_problem(big, CFG, "pr") is None


def test_branches():
    assert s.branch_problem("feat/export", CFG) is None
    assert "protected" in s.branch_problem("main", CFG)
    assert "must start" in s.branch_problem("johns-branch", CFG)
    assert s.head_problem("feat/export", CFG) is None
    assert s.head_problem("dev", CFG) is None  # release PR dev -> main
    assert "must start" in s.head_problem("patch-1", CFG)


def test_guard():
    assert s.guard_problem("git push origin feat/x", CFG) is None
    assert "protected" in s.guard_problem("git push origin main", CFG)
    assert "protected" in s.guard_problem("git push origin HEAD:refs/heads/dev", CFG)
    assert "--no-verify" in s.guard_problem("git commit --no-verify -m x", CFG)
    assert "--no-verify" in s.guard_problem("git commit -n -m x", CFG)
    assert "--no-verify" in s.guard_problem("git commit -anm x", CFG)
    assert s.guard_problem("ls -la", CFG) is None
    # bypasses wrapped in a nested shell or routed around the hooks directory
    assert "--no-verify" in s.guard_problem('sh -c "git commit --no-verify -m x"', CFG)
    assert "protected" in s.guard_problem("bash -c 'cd repo && git push origin main'", CFG)
    assert "hooksPath" in s.guard_problem("git -c core.hooksPath=/dev/null commit -m x", CFG)
    assert "hooksPath" in s.guard_problem("GIT_CONFIG_KEY_0=core.hooksPath git commit -m x", CFG)
    assert "hooksPath" in s.guard_problem("git config --unset core.hooksPath", CFG)
    # legitimate commands stay allowed
    assert s.guard_problem("git config core.hooksPath .githooks", CFG) is None
    assert s.guard_problem("git commit -m x && git log -n 3", CFG) is None
    assert s.guard_problem('git commit -m "fix: stop passing -n to the parser"', CFG) is None
    assert s.guard_problem('bash -c "git commit -m \'docs: explain --no-verify policy\'"', CFG) is None


def test_hooks_end_to_end():
    """Real git repo: protected-branch commit and bad message are blocked; good flow passes."""
    with tempfile.TemporaryDirectory() as tmp:
        def run(*args, stdin=None):
            return subprocess.run(args, cwd=tmp, input=stdin, capture_output=True, text=True)

        def std(*args, stdin=None):
            return run(sys.executable, str(TEMPLATES / ".githooks" / "standards.py"), *args, stdin=stdin)

        run("git", "init", "-q", "-b", "main")
        run("git", "config", "user.email", "t@example.com")
        run("git", "config", "user.name", "t")
        (Path(tmp) / "standards.toml").write_text(
            (TEMPLATES / "standards.toml").read_text(encoding="utf-8"), encoding="utf-8")
        run("git", "add", "-A")
        assert std("staged").returncode == 1, "commit on main must be blocked"

        run("git", "commit", "-q", "-m", "chore: init")
        run("git", "checkout", "-q", "-b", "feat/x")
        (Path(tmp) / "a.txt").write_text("hello\n", encoding="utf-8")
        run("git", "add", "-A")
        assert std("staged").returncode == 0
        msg = Path(tmp) / "MSG"
        msg.write_text("wip", encoding="utf-8")
        assert std("commit-msg", str(msg)).returncode == 1
        run("git", "commit", "-q", "-m", "feat: add greeting")
        assert std("range", "main").returncode == 0
        assert std("pre-push", stdin="refs/heads/feat/x abc refs/heads/main def\n").returncode == 1
        guard = std("guard", stdin=json.dumps({"tool_input": {"command": "git push origin dev"}}))
        assert guard.returncode == 2


if __name__ == "__main__":
    os.environ.setdefault("GIT_CONFIG_NOSYSTEM", "1")
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
