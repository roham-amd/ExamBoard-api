# Contributing to ExamBoard API

Thank you for your interest in improving the ExamBoard API! This document explains how to work with the repository.

## Branching strategy
- Use short-lived feature branches off `main` (e.g. `feature/short-description`).
- Rebase frequently to keep your branch up to date.
- Delete the branch after the pull request (PR) is merged.

## Commit conventions
- Keep commits focused and write descriptive messages in the imperative mood.
- Prefix optional metadata (e.g. `feat:`, `fix:`) only if it adds clarity.
- Format and lint before committing: `make fmt && make lint`.

## Pull request checklist
Before opening a PR, ensure you:
- [ ] Rebased on the latest `main`.
- [ ] Added or updated tests when necessary.
- [ ] Ran `make fmt`, `make lint`, and `make test`.
- [ ] Updated documentation (README, docs, etc.) when behaviour changed.
- [ ] Filled in the PR template with context and validation steps.

## Code review guidelines
- Keep PRs small and scoped; large changes should be split when possible.
- Address review feedback promptly or clarify follow-up tasks in a new ticket.
- Celebrate merged PRs by documenting notable decisions in `docs/DECISIONS.md`.
