# Research: serving Codex CLI, Gemini CLI, OpenCode and GitLab from one contract repo

Scope: how the environment contract (always-on block, skills, agents, PreToolUse guard, git hooks,
CI, tracker adapter, "proof of review") ports to three other agent harnesses and to GitLab.
Part A is harnesses, Part B is GitLab. Accessed 2026-11-26. Sources are the vendors' own docs and
repositories. Page text was read through a fetch tool that summarises pages, so quoted phrases are
the summariser's rendering of the page; re-check any load-bearing line before building on it.
UNVERIFIED marks a claim I could not trace to a primary page.

Versions seen: Codex `rust-v0.172.0` and Gemini CLI `v0.71.1` (both tagged "24 Nov", year not
shown on the page; [codex](https://github.com/openai/codex/releases/latest),
[gemini](https://github.com/google-gemini/gemini-cli/releases/latest)). OpenCode `v2.4.2`,
2026-11-26 via the GitHub API ([releases](https://github.com/anomalyco/opencode/releases)); the
repo is `anomalyco/opencode`, and the HTML "latest" page I fetched showed a stale `v1.19.6`.

Three version traps:
- **Gemini CLI is being replaced.** Every Gemini docs page carries "Gemini CLI was replaced by
  Antigravity CLI on June 18th, 2026" for unpaid-tier and Google One users, and says it is not
  optimised for Gemini 4 ([docs](https://geminicli.com/docs/extensions/)). I did not research
  Antigravity CLI. Whether paid/API-key users stay on Gemini CLI is not stated on the pages read.
- **OpenCode has a V1 and a V2 config surface.** V2 renames `permission`/`bash`/`task` to
  `permissions`/`shell`/`subagent` and `plugin` to `plugins`
  ([permissions](https://opencode.ai/docs/permissions/),
  [migrate](https://github.com/anomalyco/opencode/blob/dev/services/site/src/docs/content/migrate-v1.mdx)).
  V1 plugin entrypoints are supported "in OpenCode 1.18.29 and newer"
  ([migrate-v1](https://github.com/anomalyco/opencode/blob/dev/services/site/src/docs/content/build/plugins/migrate-v1.mdx)).
  Target both, or pin a major.
- **Codex docs moved.** `developers.openai.com/codex/*` answers 308 to `learn.chatgpt.com/docs/*`
  (redirect target is server-supplied; the content matches the OpenAI plugin guide
  at [developers.openai.com/plugins](https://developers.openai.com/plugins/build/plugins)).

# Part A. Harnesses

## A1. Always-on instructions

| Harness | File and discovery | Notes |
|---|---|---|
| Codex | `~/.codex/AGENTS.override.md` or `AGENTS.md` (first non-empty); then root-to-cwd, per directory `AGENTS.override.md`, `AGENTS.md`, then names in `project_doc_fallback_filenames`; one file per directory, concatenated, nearer files last ([agents-md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)) | Stops at `project_doc_max_bytes`, default 32 KiB. Built once per run. |
| Gemini | `~/.gemini/GEMINI.md`; workspace and parent dirs; just-in-time scan when a tool touches a path. `@file.md` imports. `context.fileName` in `settings.json` renames it to e.g. `AGENTS.md` ([gemini-md](https://geminicli.com/docs/cli/gemini-md/)) | `/memory show`, `/memory reload`. |
| OpenCode | `~/.config/opencode/AGENTS.md` plus `AGENTS.md` from workspace upward; nested ones load when a file in that dir is read; `CLAUDE.md` is read only where no `AGENTS.md` exists; `instructions` array in `opencode.jsonc` adds files, globs, URLs ([rules](https://opencode.ai/docs/rules/)) | Sources are combined, conflicts are not resolved. `OPENCODE_DISABLE_CLAUDE_CODE_PROMPT=1` turns off `CLAUDE.md`. |

Consequence: `AGENTS.md` is the common target. Codex and OpenCode read it by default; Gemini needs
`context.fileName` or a `GEMINI.md` containing `@AGENTS.md`. That Claude Code reads only
`CLAUDE.md` (not `AGENTS.md`) is from memory (UNVERIFIED); so keep `CLAUDE.md` as a one-line
`@AGENTS.md` import or keep both files generated from `CLAUDE.standards.md`.

## A2. Skills (`SKILL.md`)

| Harness | Native? | Discovery | Frontmatter / extras |
|---|---|---|---|
| Codex | Yes, open Agent Skills ([skills](https://learn.chatgpt.com/docs/build-skills)) | `.agents/skills` in cwd, each parent up to repo root, `$HOME/.agents/skills`, `/etc/codex/skills`; symlinks followed; same-name skills are not merged | `name`, `description` required. Optional `agents/openai.yaml` (UI, `policy.allow_implicit_invocation`, tool deps). Invoke `$name` or `/skills`. |
| Gemini | Yes ([skills](https://geminicli.com/docs/cli/skills/)) | `.gemini/skills/` or `.agents/skills/` (workspace), `~/.gemini/skills/` or `~/.agents/skills/` (user), extension skills; `.agents/` wins over `.gemini/` in a tier | Consent prompt on activation. `gemini skills install <git-url\|path> [--scope] [--path]`. Frontmatter fields are on a separate page I did not read. |
| OpenCode | Yes ([skills](https://opencode.ai/docs/skills/)) | `.opencode/skills`, `.claude/skills`, `.agents/skills` (cwd up to project root); global `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills`; `skills` array in config incl. URLs | Skill ID comes from the path, not `name`. `disable-model-invocation: true` hides it from the model. `skill` permission rules allow/ask/deny per ID. |

All three read `.agents/skills/`. Claude Code reads `.claude/skills` and plugin `skills/` (not
re-verified here). A repo-root `.agents/skills -> skills` symlink or copy covers Codex, Gemini and
OpenCode in one place; Codex documents following symlinked skill folders. Windows symlink support
for contributors is a risk, so prefer a generated copy plus a drift check (planned; `standards.py
check` has none today).

## A3. Subagents / custom agents

| Harness | Location | Format | Fields |
|---|---|---|---|
| Claude Code (ours) | `agents/*.md` | Markdown + YAML | `name`, `description`, `tools`, `model` |
| Codex | `.codex/agents/`, `~/.codex/agents/` ([subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)) | **TOML**, one agent per file | required `name`, `description`, `developer_instructions`; optional `model`, `model_reasoning_effort`, `features.*`. Cannot set `sandbox_mode`, `approval_policy`, `mcp_servers`: inherited from parent. No tool allow-list field documented. |
| Gemini | `.gemini/agents/*.md`, `~/.gemini/agents/*.md` ([subagents](https://geminicli.com/docs/core/subagents/)) | Markdown + YAML, body is system prompt | `name`, `description` required; `tools` (wildcards; omitted = inherits all), `model` (`inherit` default), `kind`, `temperature`, `max_turns`, `timeout_mins`, `mcpServers`. Extension docs call `agents/` "a preview feature". |
| OpenCode | `.opencode/agents/<name>.md`, `~/.config/opencode/agents/` ([agents](https://opencode.ai/docs/agents/)) | Markdown + YAML, or `agents` in `opencode.jsonc` | `description`, `mode` (`primary`/`subagent`/`all`, default `primary`), `model` as `provider/model`, `permissions` rule list, `steps`, `hidden`. `tools` and singular `permission` are "legacy V1". |

Gemini is closest to ours (same `name/description/tools/model` keys) but tool names differ and a
Claude alias such as `model: sonnet` is not valid elsewhere. OpenCode needs `mode: subagent` or the
agent shows as primary. Codex needs TOML and has no tool restriction. Our `reviewer` is not
read-only at tool level either: `agents/reviewer.md` grants `Bash`, and its no-edit rule is a prompt
rule. Where read-only must hold, enforce it with the sandbox or a hook. Plan: one neutral source per
agent (`reviewer`, `tracker`: name, description, body, tools) and a generator emitting the four files.

## A4. Pre-tool hooks that can block

| Harness | Mechanism | Block protocol | Caveats |
|---|---|---|---|
| Codex | `hooks.json` at `/etc/codex`, `$CODEX_HOME`, or `.codex/hooks.json` (trusted projects), or `[hooks]` in `config.toml`; event `PreToolUse`, matcher is a regex on tool name e.g. `Bash`, `Edit\|Write` ([hooks](https://learn.chatgpt.com/docs/hooks)) | JSON on stdin (`tool_name`, `tool_input`, `cwd`, ...); deny via `permissionDecision: "deny"`, legacy `decision: "block"`, or exit 2 with reason on stderr; `ask` is unsupported and fails the hook | Docs: "a useful guardrail, not a complete enforcement boundary". Non-managed hooks must be reviewed with `/hooks` before they run. Enabled by default; `[features] hooks = false` disables. Exact key holding the shell string inside `tool_input` is not on the page: UNVERIFIED. |
| Gemini | `hooks` in `settings.json` (project `.gemini/`, user, system, extensions); event `BeforeTool`; matcher regex on tool name ([hooks](https://geminicli.com/docs/hooks/), [reference](https://geminicli.com/docs/hooks/reference/)) | stdin has `tool_name`, `tool_input`; stdout must be only JSON; `{"decision":"deny","reason":...}` or exit 2 with stderr as reason; other exit codes are warnings and the action proceeds | Shell tool is `run_shell_command` (named as an example on the reference page and in `excludeTools`; its `tool_input` shape is not documented there). Extension hooks go in `hooks/hooks.json`, not the manifest. |
| OpenCode | No shell-command hook file. Two options: (1) declarative `permissions` rules, e.g. `{action:"shell",resource:"git push *",effect:"deny"}`, last match wins, default `ask` ([permissions](https://opencode.ai/docs/permissions/)); (2) a TS/JS plugin | V1 plugin: `"tool.execute.before": async (input, output) => { throw new Error(...) }` (example in [migrate-v1](https://github.com/anomalyco/opencode/blob/dev/services/site/src/docs/content/build/plugins/migrate-v1.mdx)); V2: `ctx.tool.hook("execute.before", ...)` | Plugin must be written in TS and cannot call `standards.py` without spawning it. Rules are glob-only, so editing-enforcement-file checks map to `edit` rules on paths. |

Claude Code's own shape (stdin JSON, exit 2 blocks, matcher on tool name) is nearly the same as
Codex's and Gemini's. `standards.py guard` can serve both if a thin adapter normalises
`tool_input` to "command string or file path". OpenCode needs a ~15-line plugin that spawns the same
guard, or only the declarative `permissions` subset. Since the vendor itself calls hooks a guardrail,
the real enforcement stays in git hooks, CI and the server-side rules (already harness-agnostic).

## A5. Plugin / extension packaging

| Harness | Unit | Manifest | Bundles | Install |
|---|---|---|---|---|
| Codex | plugin ([build](https://developers.openai.com/plugins/build/plugins)) | root `plugin.json` (portable; `.codex-plugin/plugin.json` is a fallback, not merged) | `skills/`, `mcp.json`, `.app.json`, `hooks/hooks.json`, assets. **Agents not listed as a component.** | `codex plugin marketplace add owner/repo [--ref]`, then `/plugins`. Marketplace file `.agents/plugins/marketplace.json`; legacy `.claude-plugin/marketplace.json` is also read. |
| Gemini | extension ([reference](https://geminicli.com/docs/extensions/reference/)) | `gemini-extension.json` (name, version, `mcpServers`, `contextFileName`, `excludeTools`, `settings`) | `GEMINI.md`/`contextFileName`, `commands/*.toml`, `skills/`, `agents/` (preview), `hooks/hooks.json`, `policies/`, themes, MCP | `gemini extensions install <github-url\|path> [--ref] [--auto-update]`; `link` for dev; CLI keeps a copy, so `update` is needed |
| OpenCode | plugin package ([build](https://github.com/anomalyco/opencode/blob/dev/services/site/src/docs/content/build/plugins/index.mdx), [plugins](https://opencode.ai/docs/plugins/)) | npm `package.json` with `exports` (server `.`, `./tui`, ...) | TS code: tools, hooks, commands, agents. Does **not** carry skill folders or rules files. | `opencode plugin add <pkg>`; `plugins` array in config (npm, git URL, local dir); or auto-load `.opencode/plugins/` |

Codex conflict: the plugin guide says plugin hooks "are supported only for manually installed Codex
desktop plugins" and are not eligible for the public directory, while the hooks page says "Enabled
plugins can also bundle hooks". Treat plugin-delivered hooks as unreliable on Codex CLI; ship the
guard as a project `.codex/hooks.json` written by `setup-standards`.

## A6. Component by harness

N = native, W = workaround, X = not supported. Claude Code is the baseline (N for everything).

| Component | Codex | Gemini | OpenCode |
|---|---|---|---|
| Always-on block | N (`AGENTS.md`) | W (`context.fileName` or `@AGENTS.md` import) | N (`AGENTS.md`; `CLAUDE.md` fallback) |
| Skills `SKILL.md` | N (`.agents/skills`) | N (`.agents/skills`) | N (`.agents/skills`, `.claude/skills`) |
| Agents `agents/*.md` | W (TOML, no tool list) | W (near-identical md; tool/model names differ) | W (md; `mode`, `permissions`, `provider/model`) |
| PreToolUse guard | N (`hooks.json`, same protocol shape; trust prompt) | N (`BeforeTool`, exit 2) | W (TS plugin or `permissions` globs) |
| Git hooks, CI workflow | N | N | N |
| One-command install of everything | W (plugin has no agents; hooks unreliable) | W (extension carries all; `agents/` is preview) | W (npm plugin has no skills/rules) |
| Tracker agent (`agents/tracker.md`) and adapter doc (`docs/agents/issue-tracker.md`) | W (agent as TOML; doc is plain Markdown) | W (agent md) | W (agent md) |

## A7. Minimal packaging, one repo

1. **Canonical sources, generated outputs.** Keep `skills/`, one neutral agent spec, and
   `CLAUDE.standards.md`. A generator (or `setup-standards`) writes `AGENTS.md`, `GEMINI.md`
   (`@AGENTS.md`), `.agents/skills/`, `.codex/agents/*.toml`, `.gemini/agents/*.md`,
   `.opencode/agents/*.md`; a planned drift check in `standards.py check` fails when they differ.
2. **Guard adapters.** `standards.py guard` accepts Claude, Codex and Gemini stdin JSON and exits 2
   on block. Emit `.codex/hooks.json` and `.gemini/settings.json` hook stanzas; for OpenCode emit
   `permissions` deny rules plus an optional spawning plugin.
3. **Per-harness manifests at the root** (all small): `.claude-plugin/` (exists), `plugin.json` +
   `.agents/plugins/marketplace.json` (Codex), `gemini-extension.json` (Gemini). OpenCode: skip npm;
   rely on `.agents/skills` + `AGENTS.md` + generated `.opencode/` files committed by `setup-standards`.
4. **Install story.** Gemini extension and Codex marketplace install skills and context;
   `setup-standards` would then write the project-level hooks and agents that plugins cannot carry
   (planned: its templates have no agents today).

Open item: I did not verify that Gemini loads a Claude-format marketplace or that Codex plugin
skills inherit `allowed-tools` from `SKILL.md` frontmatter.

# Part B. GitLab

## B1. Issues, hierarchy, blocking (glab and API)

`glab issue` subcommands: `board close create delete list note reopen subscribe unsubscribe update
view` ([glab issue](https://docs.gitlab.com/cli/issue/)). `glab issue create` flags include `-t`,
`-d`/`--description-file`, `-l`, `-a`, `-m`, `-c`, `--epic`, `--linked-issues`, `--link-type`
(default `relates_to`), `--linked-mr`, `-y`, `--no-editor`
([create](https://docs.gitlab.com/cli/issue/create/)). `glab mr` has `create list view approve
approvers merge note rebase update ...` ([glab mr](https://docs.gitlab.com/cli/mr/)). `glab api`
takes a REST path or `graphql` ([glab api](https://docs.gitlab.com/cli/api/)).

| Need | Mechanism | Tier |
|---|---|---|
| Issue CRUD, comment, close | `glab issue ...` | Free |
| Issue link `relates_to` / `blocks` / `is_blocked_by` | `POST /projects/:id/issues/:iid/links` with `link_type` ([issue links API](https://docs.gitlab.com/api/issue_links/)); `glab issue create --linked-issues --link-type` | API page tags Free, Premium, Ultimate. The UI page tags the blocking links Premium/Ultimate ([linked items](https://docs.gitlab.com/user/work_items/linked_items/)). **Sources disagree**; test on a Free project before relying on it. |
| "Blocked" semantics | Icon and a confirmation when closing a blocked item; advisory, no hard block, MRs not mentioned | same |
| Task as child of an issue | work item hierarchy; UI "Add existing task / Convert to child item" ([tasks](https://docs.gitlab.com/user/tasks/)) | Free (weight, status, iteration, multi-assignee are Premium+) |
| Issue under an epic | `glab issue create --epic`; "an issue can have at most one parent epic" ([child items](https://docs.gitlab.com/user/work_items/child_items/)) | Epics Premium+ ([epics](https://docs.gitlab.com/user/group/epics/)) |
| Epic under epic | same page; up to 7 levels | Ultimate |
| Set parent / list children programmatically | Epics REST API is deprecated in favour of the work items API (same epics page). The GraphQL mutations (`workItemCreate`, `workItemUpdate` with hierarchy widget, `workItemAddLinkedItems`) are my recollection: I could not confirm names in the fetched reference pages. UNVERIFIED; check the [mutations reference](https://docs.gitlab.com/api/graphql/reference/mutations/) and call via `glab api graphql`. | Per type above |

Adapter shape: Free works with issues, tasks as children and (probably) `blocks` links through REST.
Epics and nested hierarchy are Premium/Ultimate. Role matrix: Guest and up can create issues and
tasks; Planner and up can edit tasks and create epics ([permissions](https://docs.gitlab.com/user/permissions/)).

## B2. Proof of review: GitLab analogue of `commits/:sha/pulls` and check runs

| GitHub | GitLab | Notes |
|---|---|---|
| `GET repos/{o}/{r}/commits/{sha}/pulls` | `GET /projects/:id/repository/commits/:sha/merge_requests`, optional `state=merged` (added 18.2) ([commits API](https://docs.gitlab.com/api/commits/)) | Free. Docs say it returns "the merge request that originally introduced the commit"; fields include `merge_commit_sha`, `target_branch`, `sha`. Behaviour for fast-forward or rebased merges is not described: UNVERIFIED. Cross-check `merge_commit_sha` or `squash_commit_sha` equals the commit ([MR API](https://docs.gitlab.com/api/merge_requests/)). |
| Check run named `tier` | A CI job named `tier`: `GET /projects/:id/pipelines?sha=` ([pipelines](https://docs.gitlab.com/api/pipelines/)) then `GET /projects/:id/pipelines/:pid/jobs` and read `name`, `status`, `allow_failure` ([jobs](https://docs.gitlab.com/api/jobs/)); or an external status `POST /projects/:id/statuses/:sha` with `name`, `state`, then `GET .../commits/:sha/statuses?name=tier` | Free. Jobs endpoint omits retried jobs by default. Whether CI jobs also appear in the commit statuses list is not stated on the page: UNVERIFIED. |
| Required checks in ruleset | Project setting `only_allow_merge_if_pipeline_succeeds` (+ `allow_merge_on_skipped_pipeline: false`) ([projects API](https://docs.gitlab.com/api/projects/)) | Free. Maintainer+ to change. |
| Required external check | external status checks, setting `only_allow_merge_if_all_status_checks_passed` | Ultimate (stated on the projects API page; feature page not read) |

Design point (my inference, not a documented fact): after merge, the merge commit gets a new
branch pipeline whose `tier` job runs after the commit is already on the target, so "proof" cannot
require it at merge time. Prove instead via the MR's `head_pipeline` job `tier` being `success` and the
MR being `merged` with a matching `merge_commit_sha`. With merge-request pipelines the pipeline
`sha` is the source-branch head, not the merge commit.

## B3. Branch and merge controls by tier, with APIs

| Control | Tier | Setting / API |
|---|---|---|
| Protected branches | Free | `POST /projects/:id/protected_branches` (`push_access_level`, `merge_access_level`: 0 none, 30 Developer, 40 Maintainer; default 40) ([API](https://docs.gitlab.com/api/protected_branches/), [guide](https://docs.gitlab.com/user/project/repository/branches/protected/)) |
| Per-user / per-group allowed to push, code-owner approval required, group-level protection | Premium+ | `allowed_to_push` with `user_id`, `group_id`, `access_level` is Premium+; `member_role_id` Ultimate; `deploy_key_id` Free since 18.10 ([API](https://docs.gitlab.com/api/protected_branches/); tier values UNVERIFIED) |
| Pipelines must succeed | Free | Settings > Merge requests > Merge checks; skipped pipelines block unless allowed ([auto-merge](https://docs.gitlab.com/user/project/merge_requests/auto_merge/)) |
| Approvals | Free: any Developer+ can approve, optional, "don't prevent merging". Required approval rules, prevent author approval enforced: Premium+ | `POST /projects/:id/approval_rules`, `POST /projects/:id/approvals` (Premium+) ([API](https://docs.gitlab.com/api/merge_request_approvals/), [guide](https://docs.gitlab.com/user/project/merge_requests/approvals/)) |
| Push rules (commit message / branch name regex, prohibited filenames, secrets, unsigned commits) | Premium+ | Project push rules API ([guide](https://docs.gitlab.com/user/project/repository/push_rules/), [API](https://docs.gitlab.com/api/project_push_rules/)): endpoint details not read |
| External status checks | Ultimate | see B2 |

Mapping to our ruleset generator: on Free, protect the default and `dev` branches (push none, merge
Maintainers), turn on pipelines-must-succeed, and accept that approvals are advisory and path-based
tiers (our `[roles].guarded`) need Premium code owners. The "verdict check from a separate App"
has no direct equivalent; the closest is a second bot user posting commit statuses, which Free
cannot make required (external status checks are Ultimate).

## B4. Least-privilege agent token

Needed: push feature branches, open MRs, read and write issues; not merge to protected branches,
not change settings.

- **Role: Developer.** Per the permissions table, Developer can push to non-protected branches and
  create MRs; pushing to protected branches needs Maintainer; project settings and managing
  protected branches are Maintainer ([permissions](https://docs.gitlab.com/user/permissions/)).
  The table has no "merge MR" row, so merge rights come from the protected-branch "Allowed to merge"
  setting. Set it to Maintainers and push to No one/Maintainers; the guide says new rules default
  push-and-merge to Maintainers.
- **Scope: `api`.** `write_repository` is push-only over HTTPS and "does not support API
  authentication", so it cannot open MRs; `read_api` is read-only. `api` is "complete read and
  write access to the API for the token's scope" ([scopes](https://docs.gitlab.com/security/tokens/access_token_scopes/)).
  No narrower scope covers MR and issue writes, so least privilege rests on the role and the
  protected-branch rules, not the scope. Add `write_repository` only if tooling needs it separately
  (the scopes page says `api` already covers Git-over-HTTP for personal tokens only).
- **Token type.** A project access token creates a bot user with the token's role; it cannot be
  added to other projects; default and maximum lifetime 365 days
  ([project tokens](https://docs.gitlab.com/user/project/settings/project_access_tokens/)). Creation
  needs Maintainer/Owner. On GitLab.com they "require a Premium or Ultimate subscription";
  Self-Managed allows them on any license. For Free on GitLab.com, a dedicated bot user with a
  personal access token at Developer role is the likely fallback (UNVERIFIED; not on the page read).
- **Residual risks to state in the adapter doc:** the bot can still close or delete issues it can
  see, push to any unprotected branch, and with `api` could call any Developer-level endpoint. Keep
  the human merger a different identity from the agent so "prevent author approval" stays meaningful.

# Summary of gaps to resolve before building

- Gemini: how Antigravity CLI affects the supported audience; hook `tool_input` shape for `run_shell_command`.
- Codex: shell string field in `PreToolUse` input; whether plugin skills accept `allowed-tools`.
- OpenCode: target V1, V2 or both; V2 hook signature beyond the migration table.
- GitLab: Free-tier behaviour of `blocks` links; work-item GraphQL mutation names; MR lookup for
  rebased or fast-forwarded commits; whether job results surface in commit statuses.
