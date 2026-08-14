# Changelog

All notable changes to `skseed` are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning is
pre-1.0: the public API may change between minor versions
(see [VERSION_LIFECYCLE](https://github.com/smilinTux/sk-standards/blob/main/standards/VERSION_LIFECYCLE.md)).

**Where the version number comes from:** the PyPI version is derived from the git tag by
setuptools-scm, so the headings below are tag names. The npm package
`@smilintux/skseed` publishes the literal in `package.json` instead, which is a separate,
manually-bumped number. `SOP.md` section 9 lists every place a version appears and which
one to trust. Dates are the tag creation dates from `git tag --sort=creatordate`; two
tags were cut out of version order, noted inline.

## [Unreleased]

### Added

- `SOP.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and this
  `CHANGELOG.md`, bringing the repo to SK_REPO_DOC_STANDARD.
- `.github/workflows/docs-check.yml`, the DOCS_FRESHNESS_STANDARD gate, plus an
  executable `docs-evidence` block at the end of `SOP.md` that pins the console-script
  entry point, the `~/.skseed` path constants, the absence of any network bind, the
  absence of a `status`/`doctor`/`health` verb, and both unconditional CI gate lines.

### Documented (no code change)

- The `publish.yml` test job runs `pytest ... || true` and `publish-pypi` is
  `needs: test` with `if: always()`, so a tag publishes to PyPI regardless of test
  results. `ci.yml` on the pull request is the only real gate.
- `skseed --version` prints a hardcoded `0.1.0` from `skseed/cli.py:47` rather than the
  installed version. Tracked as a code follow-up; use
  `importlib.metadata.version("skseed")`.
- `package.json` version is hardcoded and can drift from the git tag, since
  `publish-npm.yml` publishes it verbatim. Tracked as a code follow-up; bump it before
  tagging.
- Two `tests/test_llm.py::TestAutoCallback` tests clear only `ANTHROPIC_API_KEY` and
  `OPENAI_API_KEY` while `auto_callback()` probes six provider variables, so they fail on
  a workstation exporting `XAI_API_KEY`, `MOONSHOT_API_KEY`, `MINIMAX_API_KEY`, or
  `NVIDIA_API_KEY`. CI is unaffected. Tracked as a code follow-up.

## [v0.1.8] - 2026-08-13

### Changed

- **The version is now derived from the git tag.** `pyproject.toml` became
  `dynamic = ["version"]` with `[tool.setuptools_scm]`, and `skseed/__init__.py` resolves
  `__version__` through the new `skseed/_ver.py` (importlib.metadata, then the build-time
  `_version.py`, then an obviously-wrong `0.0.0+unknown` fallback). A hardcoded version
  equal to the newest PyPI release makes the next tag rebuild an already-published
  version and upload fails with a bare HTTP 400.
- Every workflow checkout now uses `fetch-depth: 0` and `fetch-tags: true`, without which
  setuptools-scm cannot see a tag.
- `skseed/integration.py` resolves the skcapstone SDK lazily, so `import skseed` no
  longer pulls a subapp in.

### Fixed

- `publish.yml` had a duplicate `with:` key that made the workflow unloadable, so it
  failed in 0s without publishing anything.

### Security

- `secret-scan.yml` now runs the gitleaks 8.28.0 binary with `--exit-code 1` over the
  full history, replacing the gitleaks action (which requires a paid license for
  organization-owned repos and exits before scanning a single byte). The history scanned
  clean on 2026-08-14.

### Added

- `MISSION.md`.

## [v0.1.7] - 2026-06-14

### Changed

- Realigned the release number to the version actually published, and synchronized
  `package.json` to the published npm release.

## [v0.1.6] - 2026-06-11

### Added

- `docs/ARCHITECTURE.md`: collision lifecycle, audit pipeline, alignment state machine,
  the LLM-callback seam, and a module-by-module source map.
- Rewritten `README.md` with the SKStack v2 placement and workflow mermaid diagrams.

## [v0.1.5] - 2026-04-07

### Added

- `minimax_callback()` for MiniMax via the OpenAI-compatible path (`skseed/llm.py`).

### Changed

- `openclaw-plugin/` archived to `openclaw-plugin.archived-2026-04-23/` after the Hermes
  migration. **OpenClaw is not a live integration.** The directory is retained as
  history only; do not wire anything to it.

## [v0.1.4] - 2026-06-14

Tagged out of order, after v0.1.6. Housekeeping release.

## [v0.1.3] - 2026-03-07

### Added

- The OpenClaw plugin (5 tools plus a `/skseed` command). Superseded and archived at
  v0.1.5; see above.

### Fixed

- The collider's JSON parser no longer crashes on a malformed backtick fence. Response
  extraction now tries a direct `json.loads`, then a fenced block, then the first
  `{ ... }` span, and preserves the raw response as `ungraded` rather than raising.

## [v0.1.2] - 2026-03-06

### Changed

- Version metadata synchronized across files. This was the manual approach that v0.1.8
  replaced with a tag-derived version.

## [v0.1.1] - 2026-03-06

### Added

- Attribution to [neuresthetics](https://github.com/neuresthetics) for the original
  [Seed](https://github.com/neuresthetics/seed) recursive cognitive kernel that skseed is
  built on.

## [v0.1.0] - 2026-03-04

Initial release: the Sovereign Logic Kernel.

### Added

- `skseed/collider.py`: the 6-stage steel-man collider (steel-man, inversion, collision,
  reconstruction, meta-recursion, invariant extraction).
- `skseed/framework.py`: the Neuresthetics seed JSON loader and prompt generator, with a
  bundled `skseed/data/seed.json` and a `~/.skseed/seed.json` override.
- `skseed/alignment.py`: the three-space alignment ledger (human, model, collider) plus
  history and an issues queue, as local JSON under `~/.skseed/alignment/`.
- `skseed/audit.py`: belief extraction, domain clustering, cluster collision, and the
  hard truth-versus-moral split (moral conflicts are never auto-resolved).
- `skseed/philosopher.py`: socratic, dialectic, adversarial, and collaborative modes.
- `skseed/llm.py`: provider callbacks and `auto_callback()`.
- `skseed/cli.py`: the `skseed` Click CLI.
- `skill.yaml` and `skseed/skill.py`: the 14-tool SKSkills/MCP surface plus two hooks.
- `src/index.ts`: the `@smilintux/skseed` npm surface (seed JSON re-export plus
  TypeScript types).

[Unreleased]: https://github.com/smilinTux/skseed/compare/v0.1.8...HEAD
[v0.1.8]: https://github.com/smilinTux/skseed/releases/tag/v0.1.8
[v0.1.7]: https://github.com/smilinTux/skseed/releases/tag/v0.1.7
[v0.1.6]: https://github.com/smilinTux/skseed/releases/tag/v0.1.6
[v0.1.5]: https://github.com/smilinTux/skseed/releases/tag/v0.1.5
[v0.1.4]: https://github.com/smilinTux/skseed/releases/tag/v0.1.4
[v0.1.3]: https://github.com/smilinTux/skseed/releases/tag/v0.1.3
[v0.1.2]: https://github.com/smilinTux/skseed/releases/tag/v0.1.2
[v0.1.1]: https://github.com/smilinTux/skseed/releases/tag/v0.1.1
[v0.1.0]: https://github.com/smilinTux/skseed/releases/tag/v0.1.0
