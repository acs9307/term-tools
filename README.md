# term-tools

Personal and shared terminal utilities repo.

## Purpose

This repository stores scripts and helper tools that are useful for day-to-day terminal work.

## Script policy

- Use `python` for any script that is not dead simple.
- Use `bash` only for simple command wrappers with no `if` logic and no loops.
- All Python scripts must use `argparse`, even when they take no runtime arguments.
- Every Python script must provide `-h`/`--help` output that describes what the script does.
- Script filenames must be lowercase kebab-case (`words-like-this`).
- User-installable scripts must live in `bin/`.
- Scripts in `scripts/` are internal repo helpers and are not installed for end users.
- The installer validates `bin/` names and fails if any script is not lowercase kebab-case.

## Repository layout

```text
.
├── bin/            # user-facing scripts that can be installed to ${HOME}/bin
├── scripts/
│   ├── bash/       # internal helper wrappers for this repo
│   └── python/     # internal helper scripts for this repo
└── docs/          # optional script notes or usage docs
```

## Conventions

- Every executable script should include a short usage header.
- Python scripts should use a clear CLI interface with `argparse` (required).
- Keep scripts small and composable.
- Prefer readable output and non-zero exit codes on failure.

## Quick start

```sh
# Optional: create a local venv for Python tools
python3 -m venv .venv
source .venv/bin/activate

# Run a Python script
python3 scripts/python/<script-name>.py --help

# Run a Bash wrapper
bash scripts/bash/<script-name>.sh
```

## Install user-facing scripts

Install all user-facing scripts from this repo's `bin/` into `${HOME}/bin`:

```sh
python3 install-helper-scripts.py
```

Use a custom install directory:

```sh
python3 install-helper-scripts.py --install-dir /path/to/bin
```

Install symlinks instead of copied files (recommended if you want repo updates
to be immediately reflected in installed tools):

```sh
python3 install-helper-scripts.py --symlink
```

Skip all prompts (including overwrite confirmation):

```sh
python3 install-helper-scripts.py -y
```

When the install directory is not already on `PATH`, the installer detects your
shell and suggests the line to add:

- `zsh` -> `~/.zshrc`
- `bash` -> existing `~/.bashrc`, `~/.bash_profile`, or `~/.profile` (first match)
- `fish` -> `~/.config/fish/config.fish`
- fallback -> `~/.profile`

It then asks whether to append that line automatically (or does it automatically
with `-y`).

## Included user-facing tools

`skill` ("smart kill"):

```sh
# Case-sensitive match (default), prompts before kill
skill process-name another-name

# Case-insensitive matching
skill -i process-name

# Send a specific signal (name or number)
skill -s KILL process-name
skill -s 9 process-name

# Skip confirmation prompt
skill -y process-name
```

## Adding a new script

1. For user-facing tools, add executable scripts to `bin/`.
2. For repo-only automation/helpers, use `scripts/bash/` (simple) or `scripts/python/` (everything else).
3. Name scripts in lowercase kebab-case by function (for example, `sync-notes.py`).
4. Add or update docs in `docs/` when behavior is non-obvious.
