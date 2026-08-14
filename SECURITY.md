# Security Policy - skseed

`skseed` is the **sovereign logic kernel** of SKWorld: a pure Python library plus a
`skseed` CLI that runs propositions through a steel-man collider and keeps a local JSON
alignment ledger. It is **not a cryptographic component** and **not a network service**.
Read the posture below before reporting an issue, so your report lands in scope.

## Posture

> **Pre-1.0 and NOT independently security-audited.** No third-party review, fuzzing, or
> formal analysis has been performed. `pyproject.toml` declares
> `Development Status :: 3 - Alpha`. A passing test suite proves behaviour, not the
> absence of flaws. Review it yourself before relying on it.

### Maturity tier

**T0 - N/A (no key material).** Per the sk-standards
[CRYPTOGRAPHY_STANDARD](https://github.com/smilinTux/sk-standards/blob/main/standards/CRYPTOGRAPHY_STANDARD.md)
tiers, skseed sits outside the crypto ladder entirely:

- It generates, stores, and derives **no keys**.
- It performs **no** signing, verification, encryption, decryption, or key exchange.
- It implements **no** cryptographic primitive and binds no crypto library.
- It has no crypto claim to scope, and therefore makes none. Any document in this repo
  claiming post-quantum or quantum-resistant properties **for skseed** would be a defect;
  report it.

One function has a misleading name and deserves the correction: `verify_soul()`
(`skseed/skill.py`, `skseed/collider.py`) is a **semantic** consistency check. It collides
a set of identity claims against each other for logical coherence. It performs **no
cryptographic identity verification** and must never be used as an authentication or
authorization decision. Cryptographic identity, key custody, and capability issuance
belong to [capauth](https://github.com/smilinTux/capauth).

### Attack surface

| Property | State |
|---|---|
| Inbound network listener | **None.** No socket, `listen()`, `bind()`, `uvicorn`, `fastapi`, `flask`, `aiohttp.web`, or `http.server` anywhere under `skseed/`. This is enforced by an executable check in the `docs-evidence` block of [SOP.md](SOP.md) |
| Daemon / systemd unit | **None.** `skseed/integration.py:212` names a `~/.skseed/daemon.pid` path when registering with the skcapstone SDK, but skseed never writes it and no unit exists |
| Outbound network | Caller-initiated only, from `skseed/llm.py`: HTTPS to whichever LLM provider a callback selects, or to `OLLAMA_HOST` (default `http://localhost:11434`). With no callback configured, skseed makes no network calls at all |
| Privileges | Runs entirely as the invoking user. Requires no root, no capabilities, no setuid |
| Persistent state | Plain, unencrypted JSON under `~/.skseed/`. Not synced or replicated by skseed |
| Secrets handled | Provider API keys, read from the environment and passed straight to the provider SDK. Never written to disk, never logged, never included in a result object |

## Threat model

### In scope

- **Arbitrary code execution or file write outside `~/.skseed/`** from a crafted seed
  framework JSON (`skseed install`, or a `framework_path` config value), a crafted LLM
  response, or a crafted memory record fed to the auditor.
- **Path traversal in the alignment store.** A belief id, domain, or issue id that escapes
  `~/.skseed/alignment/` and reads or writes elsewhere on the filesystem.
- **Secret leakage.** A provider API key appearing in a log line, an exception message, a
  `SteelManResult`, an `AuditReport`, a `--json-output` payload, or anything written under
  `~/.skseed/`.
- **Prompt-content exfiltration you did not intend.** `skseed audit` sends belief-shaped
  memory content to whichever provider the active callback points at. A path by which
  memory content reaches a provider the operator did not select is in scope.
- **Denial of service via unbounded parsing.** A response or seed JSON that makes
  `_extract_json()` or the framework loader consume unbounded memory or CPU.
- **A false security claim in this repo's docs**, including any crypto claim about skseed
  or any implication that `verify_soul()` performs cryptographic verification.
- **Supply chain within our control:** a compromised or unexpected artifact published as
  `skseed` on PyPI or `@smilintux/skseed` on npm, or a workflow change that lets one be
  published without review.

### Out of scope (handle these elsewhere)

- **What the LLM says.** Coherence scores, truth grades, and invariants are the model's
  output. A model producing a wrong or manipulable judgement is a model-quality issue, not
  a skseed vulnerability. skseed structures the collision, it does not validate the
  verdict.
- **Prompt injection embedded in audited content.** Memory content is untrusted text sent
  to a model by design. Treat any collider output as untrusted, and never make an
  authorization decision from it. Do not report "a memory can steer the model" as a skseed
  flaw.
- **Confidentiality of data you chose to send to a third-party provider.** Once a callback
  is configured, propositions and memory content leave your machine under that provider's
  terms. Use Ollama or prompt-only mode if that is unacceptable.
- **Filesystem permissions on `$HOME`.** `~/.skseed/` inherits your umask. Protecting the
  home directory is the operator's job.
- **Vulnerabilities in dependencies** (`pydantic`, `click`, `pyyaml`, `typescript`, any
  provider SDK). Report those upstream; tell us if skseed's usage makes one exploitable
  that otherwise would not be.
- **Anything in `openclaw-plugin.archived-2026-04-23/`.** OpenClaw was evicted from the
  fleet in April 2026. That directory is dead history, is not built, is not published, and
  is not an integration.
- **Key custody, identity, authentication, authorization.** Owned by capauth, skvault, and
  the SKWorld authorization plane. skseed has no part in any of them.

## Supported versions

| Version | Supported |
|---|---|
| Latest published `0.1.x` | ✅ security fixes |
| Older `0.1.x` | ❌ best effort, critical only |

Until 1.0, only the latest published `0.x` line receives security fixes, per
[VERSION_LIFECYCLE](https://github.com/smilinTux/sk-standards/blob/main/standards/VERSION_LIFECYCLE.md)
(Active always; older = critical only).

Determine what you are running with the authoritative source, not `skseed --version`
(which prints a stale hardcoded literal, a known defect recorded in
[SOP.md](SOP.md) section 9):

```bash
python -c "from importlib.metadata import version; print(version('skseed'))"
```

Note that the PyPI version comes from the git tag while the npm version comes from a
hardcoded `package.json` literal, so the two registries can report different numbers for
the same commit. Tell us which registry and which number when you report.

## Reporting a vulnerability

**Do not open a public GitHub issue for a security vulnerability.**

- **Primary:** GitHub **private vulnerability reporting**. Use "Report a vulnerability" on
  the Security tab of
  [`smilinTux/skseed`](https://github.com/smilinTux/skseed/security/advisories/new).
- **Secondary (out of band):** contact the maintainers (smilinTux / SKWorld) via the
  address on the GitHub organization profile. Encrypt sensitive reports to the
  maintainer's sovereign capauth / `sk_pgp` PGP key, fingerprint published on the org
  profile.

Please include: the affected version and which registry it came from, your Python (or
Node) version, which LLM callback was active if any, the contents of the relevant
`~/.skseed/` state with secrets redacted, and a minimal reproduction.

**Acknowledgement SLA: within 72 hours.** We aim to ship a fix or a documented mitigation
within 90 days and will coordinate a disclosure date with you.

**Safe harbour:** good-faith security research conducted under coordinated disclosure will
not be pursued or reported. Stay within your own systems and data, do not access other
people's data, and do not degrade a service. Credit is given in the advisory unless you
ask otherwise.

### What we especially want to hear about

- A seed framework JSON, memory record, or LLM response that causes a write outside
  `~/.skseed/`, or any code execution.
- A belief id, domain, or issue id that traverses out of `~/.skseed/alignment/`.
- An API key surfacing anywhere in output, logs, exceptions, or persisted state.
- A path by which audited content reaches a provider the operator did not configure.
- A workflow or packaging change that lets an artifact reach PyPI or npm without review.
  We already know `publish.yml` cannot block on tests (`|| true` plus `if: always()`),
  documented in [SOP.md](SOP.md) section 5; a way to publish without a tag at all would be
  new.
- Any documentation in this repo asserting a security or cryptographic property that the
  code does not have.

---

**License:** GPL-3.0-or-later. **Standards:** ISO/IEC 29147 and 30111 (vulnerability
disclosure); CVSS v4.0; sk-standards
[SECURITY_DISCLOSURE_STANDARD](https://github.com/smilinTux/sk-standards/blob/main/standards/SECURITY_DISCLOSURE_STANDARD.md)
and
[SK_REPO_DOC_STANDARD](https://github.com/smilinTux/sk-standards/blob/main/standards/SK_REPO_DOC_STANDARD.md).
