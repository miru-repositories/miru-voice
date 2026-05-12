# Security Policy

## Supported versions

This project is in early development (pre-1.0). Only the latest commit on `main` receives security fixes.

| Version | Supported |
|---|---|
| main (HEAD) | yes |
| tagged releases | only the most recent |

## Reporting a vulnerability

**Do not file public GitHub issues for security vulnerabilities.** Use GitHub's private vulnerability reporting:

1. Go to https://github.com/miru-repositories/miru-voice/security/advisories/new
2. Describe the issue, steps to reproduce, and your assessment of impact
3. The maintainer will acknowledge within 7 days and work on a fix

If private reporting is unavailable for any reason, email the repository owner via their GitHub profile.

## Threat model (what we care about)

Miru Voice processes audio captured from your microphone and pastes text into the focused application. Concerns to flag:

- **Code execution via input** — anything that takes audio or text and turns it into a code path that wasn't intended (e.g., text that includes shell metacharacters being passed to a shell).
- **Credential leakage via clipboard** — the injector module reads and writes the system clipboard. If it ever leaks the clipboard contents off-machine, that's a vulnerability.
- **Privilege escalation** — on Windows or macOS, if the hotkey/listener can be tricked into running with higher privileges than the user intended.
- **Supply chain** — if a dependency in `pyproject.toml` is found to be malicious, please report so we can pin or replace.

## What we don't care about

- **Model accuracy** — Whisper occasionally mishears. That's a usability issue, not a security one.
- **OS permissions prompts** — pynput requiring Accessibility on macOS, the cuBLAS DLL workaround on Windows, etc. These are documented requirements, not bugs.
- **Local-only DoS** — making your own machine slow by running too many instances is a usability issue, not a security one.
