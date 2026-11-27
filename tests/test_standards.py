"""Self-check for standards.py. Run: python tests/test_standards.py (exits non-zero on failure)."""
import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

TEMPLATES = Path(__file__).resolve().parent.parent / "skills" / "setup-standards" / "templates"
sys.path.insert(0, str(TEMPLATES / ".githooks"))
import standards as s  # noqa: E402

CFG = tomllib.loads((TEMPLATES / "standards.toml").read_text(encoding="utf-8"))
HARNESS_BLOCK = 2  # the agent harness contract: a hook exiting 2 blocks the tool call


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
    tag = "refs/tags/v1 abc refs/tags/v1 0000\n"
    assert s.cmd_pre_push(CFG, tag) == 0  # a tag is not a branch: release tags push freely
    assert s.cmd_pre_push(CFG, tag + "refs/heads/wip abc refs/heads/wip 0000\n") != 0


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


def test_codeowners():
    owners = s.codeowners(CFG).splitlines()
    assert "/standards.toml @org/seniors" in owners  # guarded
    assert "/tests/acceptance/ @org/seniors" in owners  # holdout
    assert "**/migrations/** @org/seniors" in owners  # human path; globs stay unanchored
    assert not any(o.startswith(("* ", "/src/")) for o in owners)  # agent-merge paths: no owner


def rules(branch: str, cfg: dict) -> dict:
    return {r["type"]: r.get("parameters", {}) for r in s.ruleset(branch, cfg)["rules"]}


def test_ruleset_merge_methods():
    dev, main = rules("dev", CFG), rules("main", CFG)
    assert "required_linear_history" in dev and "required_linear_history" not in main
    assert dev["pull_request"]["allowed_merge_methods"] == ["rebase"]
    assert main["pull_request"]["allowed_merge_methods"] == ["merge"]  # release keeps a merge commit
    assert dev["required_status_checks"]["strict_required_status_checks_policy"]
    # release: main's merge commits never reach a linear dev, so "up to date" would block every release
    assert not main["required_status_checks"]["strict_required_status_checks_policy"]


def test_ruleset_reviews_and_checks():
    dev = rules("dev", CFG)
    pr = dev["pull_request"]
    assert pr["require_code_owner_review"] and pr["dismiss_stale_reviews_on_push"]
    assert pr["required_review_thread_resolution"]
    assert not pr["require_last_push_approval"]  # reviews_required = 0: it would block agent paths
    strict = {**CFG, "pr": {**CFG["pr"], "reviews_required": 1}}
    assert s.ruleset("dev", strict)["rules"][2]["parameters"]["require_last_push_approval"]
    contexts = [c["context"] for c in dev["required_status_checks"]["required_status_checks"]]
    assert contexts == ["standards", "tier"]  # tier: human review waits for a senior (ADR 0002)
    reviewed = {**CFG, "review": {"check": "verdict", "app_id": 42}}
    checks = s.branch_rules("dev", reviewed)[3]["parameters"]["required_status_checks"]
    assert {"context": "verdict", "integration_id": 42} in checks  # reviewer agent's App only
    assert s.ruleset("dev", CFG)["bypass_actors"] == []  # template default: nobody bypasses
    solo = {**CFG, "roles": {**CFG["roles"], "admin_bypass": True}}
    assert s.ruleset("dev", solo)["bypass_actors"][0]["bypass_mode"] == "pull_request"


def test_pr_rules():
    assert s.link_problem("Adds export.\n\nCloses #12", CFG) is None
    assert s.link_problem("Refs #7", CFG) is None
    assert "ticket" in s.link_problem("Adds export.", CFG)
    assert s.link_problem(None, CFG) is None  # no body given (local run): not checked
    assert s.holdout_problem(["tests/acceptance/test_export.py"], CFG) is None
    assert s.holdout_problem(["src/export.py", "tests/unit/test_export.py"], CFG) is None
    assert "own PR" in s.holdout_problem(["src/export.py", "tests/acceptance/test_export.py"], CFG)
    # a release (dev -> main) is a promotion: no size, ticket-link or holdout rules (ADR 0003)
    # nor are its commits rechecked: each passed in its ticket PR, and `release` proves that
    assert s.cmd_range(CFG, "no-such-base", {"branch": "dev", "body": "", "size": True}) == 0


def fake_github(responses):
    """Swap the GitHub API for a dict of path -> JSON; unknown paths fail like a 404."""
    s.gh_api = lambda path: responses.get(path)


REVIEW = "repos/{owner}/{repo}/pulls/7"


def test_release_approval_setting():
    floor = ("agent-merge", [])
    assert s.release_floor(floor, CFG)[0] == "human-review"  # template default: human
    tiered = {**CFG, "release": {"approval": "tiered"}}
    assert s.release_floor(floor, tiered) == floor  # human only if the release hits a trigger
    assert s.release_floor(("human-review", ["x"]), tiered)[0] == "human-review"
    assert s.release_floor(("human-review", ["x"]), {**CFG, "release": {"approval": "auto"}})[0] == "agent-merge"


def test_senior_approval_of_head_commit():
    reviews = [
        {"user": {"login": "ana"}, "state": "APPROVED", "commit_id": "old"},  # stale: before a push
        {"user": {"login": "bo"}, "state": "APPROVED", "commit_id": "head"},
        {"user": {"login": "bo"}, "state": "COMMENTED", "commit_id": "head"},  # a comment keeps it
        {"user": {"login": "cy"}, "state": "APPROVED", "commit_id": "head"},
        {"user": {"login": "cy"}, "state": "DISMISSED", "commit_id": "head"},  # dismissed: void
    ]
    assert s.latest_approvers(reviews, "head") == ["bo"]
    solo = {**CFG, "roles": {**CFG["roles"], "senior": ["@Bo"]}}
    fake_github({REVIEW: {"head": {"sha": "head"}}, REVIEW + "/reviews?per_page=100": reviews})
    assert s.approval_problem("7", solo) is None
    assert "senior" in s.approval_problem("7", CFG)  # @org/seniors: membership unreadable -> fail closed
    fake_github({"repos/{owner}/{repo}/pulls/7": {"head": {"sha": "head"}},
                 REVIEW + "/reviews?per_page=100": reviews,
                 "orgs/org/teams/seniors/memberships/bo": {"state": "active"}})
    assert s.approval_problem("7", CFG) is None


def test_release_proof_of_review():
    pulls = "repos/{owner}/{repo}/commits/abc12345/pulls"
    runs = "repos/{owner}/{repo}/commits/prhead/check-runs?check_name=tier"
    merged = [{"number": 9, "merged_at": "2026-11-21", "base": {"ref": "dev"}, "head": {"sha": "prhead"}}]
    fake_github({pulls: merged, runs: {"check_runs": [{"conclusion": "success"}]}})
    assert s.proof_problem("abc12345", CFG) is None
    fake_github({pulls: [{**merged[0], "merged_at": None}]})
    assert "without a merged PR" in s.proof_problem("abc12345", CFG)  # open PR only: unreviewed
    fake_github({pulls: merged, runs: {"check_runs": [{"conclusion": "failure"}]}})
    assert "'tier'" in s.proof_problem("abc12345", CFG)
    fake_github({pulls: merged, runs: {"check_runs": [{"conclusion": "success"}]}})
    reviewed = {**CFG, "review": {**CFG["review"], "app_id": 42}}
    assert "'verdict'" in s.proof_problem("abc12345", reviewed)  # verdict required once its App exists
    # solo repo: an admin-bypass merge by a senior is the review (they cannot approve their own PR)
    failed = {pulls: merged, runs: {"check_runs": [{"conclusion": "failure"}]},
              "repos/{owner}/{repo}/pulls/9": {"merged_by": {"login": "Bo"}}}
    solo = {**CFG, "roles": {**CFG["roles"], "senior": ["@bo"], "admin_bypass": True}}
    fake_github(failed)
    assert s.proof_problem("abc12345", solo) is None
    assert "'tier'" in s.proof_problem("abc12345", {**solo, "roles": {**solo["roles"], "admin_bypass": False}})
    fake_github({**failed, "repos/{owner}/{repo}/pulls/9": {"merged_by": {"login": "eve"}}})
    assert "'tier'" in s.proof_problem("abc12345", solo)  # merged by a non-senior: no proof


def test_tier_floor():
    def floor(files, added=None):
        return s.tier_floor(files, added or {}, CFG)
    assert floor(["docs/research/a.md"], {"docs/research/a.md": ["hi"]}) == ("auto-merge", [])
    assert floor(["docs/research/a.md"], {"docs/research/a.md": ["x"] * 51})[0] == "agent-merge"  # over the cap
    assert floor(["docs/guide.md"], {"docs/guide.md": ["hi"]})[0] == "agent-merge"  # product docs
    assert floor(["docs/adr/0004-x.md"])[0] == "human-review"  # decisions
    assert floor(["src/app.py", "docs/a.md"])[0] == "agent-merge"  # default tier
    tier, why = floor(["db/migrations/0042.py"])
    assert tier == "human-review" and why == ["human-review: db/migrations/0042.py — path **/migrations/**"]
    assert floor(["migrations/0001.py"])[0] == "human-review"  # **/ also matches at the root
    assert floor(["standards.toml"])[0] == "human-review"  # [roles].guarded
    assert floor(["tests/acceptance/test_x.py"])[0] == "human-review"  # holdout tests
    assert floor(["REVIEW.md"])[0] == "human-review"  # human path beats the docs allow-list
    drop = floor(["src/m.py"], {"src/m.py": ["ALTER TABLE t DROP COLUMN email"]})[1]
    assert drop == ["human-review: src/m.py — content 'DROP COLUMN'"]
    assert floor(["src/r.py"], {"src/r.py": ["DELETE FROM users;"]})[0] == "human-review"
    assert floor(["src/r.py"], {"src/r.py": ["DELETE FROM users WHERE id = 1;"]})[0] == "agent-merge"
    assert floor(["src/t.py"], {"src/t.py": ["s.truncate(10)"]})[0] == "agent-merge"  # case-sensitive


def test_added_by_file():
    diff = ("diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -0,0 +1 @@\n+new line\n"
            "diff --git a/y b/y\n--- a/y\n+++ /dev/null\n@@ -1 +0,0 @@\n-gone\n")
    assert s.added_by_file(diff) == {"x": ["new line"]}


def isolated_env() -> dict:
    """Run from a git hook in a worktree, GIT_DIR points at the real repo: a throwaway repo's git
    commands must not inherit it, or their init, config and commits land there."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | {"GIT_CONFIG_NOSYSTEM": "1"}


def throwaway_repo(tmp: str) -> SimpleNamespace:
    """`run` runs a command in the repo; `std` runs the standards hook there."""
    env = isolated_env()

    def run(*args, stdin=None):
        return subprocess.run(args, cwd=tmp, input=stdin, capture_output=True, text=True, env=env)

    def std(*args, stdin=None):
        return run(sys.executable, str(TEMPLATES / ".githooks" / "standards.py"), *args, stdin=stdin)

    return SimpleNamespace(path=Path(tmp), run=run, std=std)


def init_on_main(repo: SimpleNamespace) -> None:
    repo.run("git", "init", "-q", "-b", "main")
    repo.run("git", "config", "user.email", "t@example.com")
    repo.run("git", "config", "user.name", "t")
    (repo.path / "standards.toml").write_text(
        (TEMPLATES / "standards.toml").read_text(encoding="utf-8"), encoding="utf-8")
    repo.run("git", "add", "-A")
    assert repo.std("staged").returncode == 1, "commit on main must be blocked"
    repo.run("git", "commit", "-q", "-m", "chore: init")


def ticket_flow(repo: SimpleNamespace) -> None:
    repo.run("git", "checkout", "-q", "-b", "wip")
    assert repo.std("staged").returncode == 1, "commit on a misnamed branch must be blocked"
    repo.run("git", "checkout", "-q", "-b", "feat/x")
    (repo.path / "a.txt").write_text("hello ←\n", encoding="utf-8")  # byte 0x90: cp1252 cannot decode it
    repo.run("git", "add", "-A")
    assert repo.std("staged").returncode == 0
    msg = repo.path / "MSG"
    msg.write_text("wip", encoding="utf-8")
    assert repo.std("commit-msg", str(msg)).returncode == 1
    repo.run("git", "commit", "-q", "-m", "feat: add greeting")
    assert repo.std("range", "main").returncode == 0
    assert "tier: agent-merge" in repo.std("tier", "main").stdout
    assert repo.std("pre-push", stdin="refs/heads/feat/x abc refs/heads/main def\n").returncode == 1
    guard = repo.std("guard", stdin=json.dumps({"tool_input": {"command": "git push origin dev"}}))
    assert guard.returncode == HARNESS_BLOCK


def release_flow(repo: SimpleNamespace) -> None:
    """dev -> main: an old oversized commit on dev does not block it."""
    repo.run("git", "checkout", "-q", "-b", "dev")
    (repo.path / "big.txt").write_text("x\n" * 400, encoding="utf-8")
    repo.run("git", "add", "-A")
    repo.run("git", "commit", "-q", "-m", "feat: bootstrap")
    assert repo.std("range", "main", "--branch", "feat/y").returncode == 1, "a ticket PR still checks commit size"
    assert repo.std("range", "main", "--branch", "dev").returncode == 0


def test_hooks_end_to_end():
    """Real git repo: protected-branch commit and bad message are blocked; good flow passes."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = throwaway_repo(tmp)
        init_on_main(repo)
        ticket_flow(repo)
        release_flow(repo)


def test_end_to_end_ignores_hook_git_dir():
    """A hook in a worktree sets GIT_DIR to the real repo; the end-to-end test must not touch it."""
    with tempfile.TemporaryDirectory() as decoy:
        subprocess.run(["git", "init", "-q", decoy], capture_output=True, env=isolated_env())
        config = Path(decoy) / ".git" / "config"
        before = config.read_bytes()
        with mock.patch.dict(os.environ, {"GIT_DIR": str(Path(decoy) / ".git")}):
            test_hooks_end_to_end()
        assert config.read_bytes() == before, "end-to-end test wrote into the hook's repo"


if __name__ == "__main__":
    os.environ.setdefault("GIT_CONFIG_NOSYSTEM", "1")
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
