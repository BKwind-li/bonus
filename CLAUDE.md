# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **Superpowers v5.0.7** — a skills and workflow plugin system for AI coding agents. It ships a library of composable "skills" that enforce structured software development workflows (brainstorming → planning → TDD → subagent execution → code review → branch completion).

The plugin targets Claude Code, Cursor, Codex, OpenCode, and Gemini CLI. There is no build step; the project is pure markdown skills plus a minimal Node.js entry point for OpenCode.

## Repository Structure

```
.claude/
  skills/                  # 14 core skill directories (SKILL.md in each)
  agents/                  # Agent templates (code-reviewer.md)
  commands/                # Deprecated slash-command wrappers
  superpowers-5.0.7/       # Canonical source mirrored to .claude/
    skills/
    agents/
    commands/
    docs/                  # Planning docs and specs
    hooks/                 # Git hooks (hooks.json, run-hook.cmd)
    scripts/               # bump-version.sh
    tests/                 # Scenario-based test prompts
    .claude-plugin/        # Claude Code plugin descriptor
    .cursor-plugin/        # Cursor plugin descriptor
    .opencode/             # OpenCode plugin entry (superpowers.js)
    .codex/                # Codex install instructions
```

The `.claude/skills/` directory is a flat mirror of `.claude/superpowers-5.0.7/skills/`. Changes to skills must be made in both places (or only in `superpowers-5.0.7/` and then mirrored).

## Skills Library

Each skill lives in `.claude/skills/<name>/SKILL.md`. Invoke via the `Skill` tool — never read skill files directly with the `Read` tool.

| Skill | Purpose |
|---|---|
| `using-superpowers` | Entry point; sets skill invocation rules |
| `brainstorming` | Design-first refinement (HARD GATE: no code before approved design) |
| `writing-plans` | Break approved design into 2–5 min tasks with exact file paths |
| `test-driven-development` | RED-GREEN-REFACTOR cycle (rigid — no production code before failing test) |
| `subagent-driven-development` | Dispatch fresh subagents per task with two-stage review |
| `executing-plans` | Sequential plan execution with human checkpoints |
| `dispatching-parallel-agents` | Concurrent multi-task subagent dispatch |
| `systematic-debugging` | 4-phase root-cause investigation |
| `verification-before-completion` | Evidence-based claim verification |
| `requesting-code-review` | Pre-review checklist and review dispatch |
| `receiving-code-review` | Handle incoming review feedback |
| `using-git-worktrees` | Isolated workspace setup and safety checks |
| `finishing-a-development-branch` | Merge/PR/keep/discard decision workflow |
| `writing-skills` | Guide for authoring new skills (includes TDD for skills) |

## Key Workflows

**Default development flow:**
1. `brainstorming` → approved design doc
2. `using-git-worktrees` → isolated branch
3. `writing-plans` → task list
4. `subagent-driven-development` or `executing-plans` → implementation
5. `test-driven-development` → enforced during implementation
6. `requesting-code-review` → between tasks
7. `finishing-a-development-branch` → integration

## Platform Notes

Skills use Claude Code tool names. For other platforms, tool mappings live in:
- Cursor: `.cursor-plugin/plugin.json`
- Codex: `.codex/INSTALL.md`
- OpenCode: `.opencode/INSTALL.md` and `.opencode/plugins/superpowers.js`
- Gemini: `GEMINI.md` and `gemini-extension.json`

## Versioning

Version is tracked in `.claude/superpowers-5.0.7/.version-bump.json`. Bump script: `scripts/bump-version.sh`.

## Contributing New Skills

Follow the `writing-skills` skill (`skills/writing-skills/SKILL.md`). New skills require:
1. A `SKILL.md` with YAML frontmatter (`name`, `description`)
2. Tests under `superpowers-5.0.7/tests/`
3. Mirror into both `.claude/skills/` and `.claude/superpowers-5.0.7/skills/`
