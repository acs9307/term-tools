#!/usr/bin/env python3
"""Install user-facing scripts from this repository's bin directory."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import sys
from dataclasses import dataclass
from pathlib import Path


SCRIPT_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:\.[a-z0-9]+)?$")
PATH_UPDATE_MARKER = "# Added by term-tools install-helper-scripts"


@dataclass(frozen=True)
class PathUpdateTarget:
    shell_name: str
    rc_file: Path
    path_line: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Install scripts from this repository's bin directory into a user "
            "bin directory (default: ${HOME}/bin)."
        )
    )
    parser.add_argument(
        "-d",
        "--install-dir",
        type=Path,
        default=Path.home() / "bin",
        help="Installation directory for scripts (default: %(default)s).",
    )
    parser.add_argument(
        "-s",
        "--symlink",
        action="store_true",
        help=(
            "Install symlinks to repository scripts instead of copying files. "
            "Useful when you want installed tools to track repo updates."
        ),
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Auto-confirm prompts (including overwrite and PATH update confirmation).",
    )
    return parser


def discover_source_scripts(repo_root: Path) -> tuple[Path, list[Path], list[Path]]:
    bin_dir = repo_root / "bin"
    source_scripts: list[Path] = []
    invalid_script_names: list[Path] = []
    if not bin_dir.is_dir():
        return bin_dir, source_scripts, invalid_script_names

    for script_path in sorted(bin_dir.iterdir()):
        if not script_path.is_file():
            continue
        if script_path.name.startswith("."):
            continue
        if not SCRIPT_NAME_PATTERN.match(script_path.name):
            invalid_script_names.append(script_path)
            continue
        source_scripts.append(script_path)

    return bin_dir, source_scripts, invalid_script_names


def detect_repo_root() -> Path:
    script_dir = Path(__file__).resolve().parent
    for candidate in (script_dir, *script_dir.parents):
        if (candidate / "bin").is_dir():
            return candidate
    return script_dir


def is_in_path(directory: Path) -> bool:
    target = directory.expanduser().resolve()
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        try:
            if Path(entry).expanduser().resolve() == target:
                return True
        except OSError:
            continue
    return False


def confirm_overwrites(overwrite_paths: list[Path], assume_yes: bool) -> bool:
    if not overwrite_paths:
        return True

    print("The following files already exist and will be replaced:")
    for path in overwrite_paths:
        print(f"  - {path}")

    if assume_yes:
        print("Proceeding due to -y/--yes.")
        return True

    response = input("Continue with overwrite? [y/N]: ").strip().lower()
    return response in {"y", "yes"}


def format_posix_path_value(path: Path, home_dir: Path) -> str:
    normalized_path = path.expanduser().resolve()
    normalized_home = home_dir.expanduser().resolve()
    if normalized_path == normalized_home:
        return "$HOME"
    try:
        relative_path = normalized_path.relative_to(normalized_home)
    except ValueError:
        return str(normalized_path)
    return f"$HOME/{relative_path.as_posix()}"


def choose_bash_rc_file(home_dir: Path) -> Path:
    for candidate_name in (".bashrc", ".bash_profile", ".profile"):
        candidate = home_dir / candidate_name
        if candidate.exists():
            return candidate
    return home_dir / ".bashrc"


def detect_path_update_target(install_dir: Path) -> PathUpdateTarget:
    home_dir = Path.home().expanduser()
    shell_name = Path(os.environ.get("SHELL", "")).name.lower()
    posix_path_value = format_posix_path_value(install_dir, home_dir)
    escaped_posix_path_value = posix_path_value.replace('"', '\\"')

    if shell_name == "zsh":
        rc_file = home_dir / ".zshrc"
        path_line = f'export PATH="{escaped_posix_path_value}:$PATH"'
    elif shell_name == "bash":
        rc_file = choose_bash_rc_file(home_dir)
        path_line = f'export PATH="{escaped_posix_path_value}:$PATH"'
    elif shell_name == "fish":
        rc_file = home_dir / ".config" / "fish" / "config.fish"
        path_line = f'fish_add_path "{escaped_posix_path_value}"'
    else:
        rc_file = home_dir / ".profile"
        path_line = f'export PATH="{escaped_posix_path_value}:$PATH"'

    return PathUpdateTarget(
        shell_name=shell_name or "unknown",
        rc_file=rc_file,
        path_line=path_line,
    )


def rc_file_has_path_entry(target: PathUpdateTarget, install_dir: Path) -> bool:
    if not target.rc_file.exists():
        return False

    try:
        content = target.rc_file.read_text(encoding="utf-8")
    except OSError:
        return False

    home_dir = Path.home().expanduser()
    detection_tokens = {
        str(install_dir),
        format_posix_path_value(install_dir, home_dir),
    }

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "PATH" not in line and "fish_add_path" not in line:
            continue
        if any(token in line for token in detection_tokens):
            return True
    return False


def append_path_update(target: PathUpdateTarget) -> None:
    target.rc_file.parent.mkdir(parents=True, exist_ok=True)

    needs_separator = False
    if target.rc_file.exists():
        try:
            existing = target.rc_file.read_text(encoding="utf-8")
            needs_separator = bool(existing) and not existing.endswith("\n")
        except OSError:
            needs_separator = False

    with target.rc_file.open("a", encoding="utf-8") as file_handle:
        if needs_separator:
            file_handle.write("\n")
        file_handle.write(f"{PATH_UPDATE_MARKER}\n{target.path_line}\n")


def maybe_offer_path_update(install_dir: Path, assume_yes: bool) -> None:
    if is_in_path(install_dir):
        return

    target = detect_path_update_target(install_dir)
    already_configured = rc_file_has_path_entry(target, install_dir)

    print(
        f"{install_dir} is not currently on PATH in this shell session "
        f"(detected shell: {target.shell_name})."
    )
    print(f"Suggested line for {target.rc_file}:")
    print(f"  {target.path_line}")

    if already_configured:
        print(
            f"{target.rc_file} already appears to include this PATH entry. "
            "Open a new shell or source the file to apply it."
        )
        return

    should_update = False
    if assume_yes:
        print("Updating PATH config due to -y/--yes.")
        should_update = True
    else:
        response = input(f"Add this line to {target.rc_file}? [y/N]: ").strip().lower()
        should_update = response in {"y", "yes"}

    if should_update:
        try:
            append_path_update(target)
        except OSError as exc:
            print(f"Failed to update {target.rc_file}: {exc}")
            print("Add the suggested line manually to your shell RC file.")
            return
        print(f"Updated {target.rc_file}.")
        print(
            f"Open a new shell or run: source {target.rc_file}"
        )
        return

    print("Skipped PATH update.")
    print(f"Add the suggested line manually to {target.rc_file}.")


def destination_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def install_scripts_with_mode(
    source_scripts: list[Path], install_dir: Path, use_symlink: bool
) -> list[Path]:
    installed_paths: list[Path] = []
    for source_path in source_scripts:
        destination_path = install_dir / source_path.name
        if destination_exists(destination_path):
            if destination_path.is_dir() and not destination_path.is_symlink():
                raise IsADirectoryError(
                    f"Cannot replace directory with script file: {destination_path}"
                )
            destination_path.unlink()

        if use_symlink:
            destination_path.symlink_to(source_path.resolve())
        else:
            shutil.copy2(source_path, destination_path)
            destination_path.chmod(destination_path.stat().st_mode | stat.S_IXUSR)
        installed_paths.append(destination_path)
    return installed_paths


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = detect_repo_root()
    install_dir = args.install_dir.expanduser().resolve()

    source_dir, source_scripts, invalid_script_names = discover_source_scripts(repo_root)
    if invalid_script_names:
        print("The following bin scripts do not follow lowercase kebab-case naming:")
        for path in invalid_script_names:
            print(f"  - {path.name}")
        print("Rename these files before installing.")
        return 2

    if not source_scripts:
        print(f"No installable scripts found in {source_dir}.")
        return 0

    install_dir.mkdir(parents=True, exist_ok=True)

    overwrite_paths = []
    for source_path in source_scripts:
        destination_path = install_dir / source_path.name
        if destination_exists(destination_path):
            overwrite_paths.append(destination_path)

    if not confirm_overwrites(overwrite_paths, args.yes):
        print("Installation cancelled.")
        return 1

    install_mode = "symlink" if args.symlink else "copy"
    try:
        installed_paths = install_scripts_with_mode(
            source_scripts, install_dir, use_symlink=args.symlink
        )
    except OSError as exc:
        print(f"Installation failed: {exc}")
        return 1

    print(
        f"Installed {len(installed_paths)} script(s) into {install_dir} "
        f"using {install_mode} mode."
    )
    for path in installed_paths:
        print(f"  - {path}")

    maybe_offer_path_update(install_dir=install_dir, assume_yes=args.yes)

    return 0


if __name__ == "__main__":
    sys.exit(main())
