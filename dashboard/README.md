# DAC Project

This project was generated with `dac init`.

`dac init` initialized this directory as a Git repository so Bruin can discover the project root immediately.

## Commands

```shell
dac validate --dir .
dac serve --dir . --open
```

The generated dashboards use a local DuckDB connection named `local_duckdb`. The starter queries include inline sample data, so there is no seed step.

## Agent Skills

This project includes DAC's bundled dashboard authoring skill:

- `.claude/skills/create-dashboard/SKILL.md`
- `.codex/skills/create-dashboard` symlinked to the same skill for Codex

Restart your agent session to pick up newly installed skills.

To inspect one generated widget from the command line:

```shell
dac query --dir . --dashboard "Semantic Sales" --widget "Revenue"
```
