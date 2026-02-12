#!/usr/bin/env python3
"""
Move output folders from esteban/outputs to <author>/outputs.

Reads keys from config.yaml and moves each matching folder from
/data2/openreal2sim/esteban/outputs to /data2/openreal2sim/<author>/outputs.

Always runs the move inside a minimal docker container as root (no image
build; uses local python image only, never pulls).
"""
import argparse
import errno
import os
import subprocess
import shutil
import yaml
from pathlib import Path
from typing import List

# Owner for moved outputs: reconstructiongroup (uid:gid = 1054:1054)
RECONSTRUCTION_GROUP_UID = 1054
RECONSTRUCTION_GROUP_GID = 1054

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT, ESTEBAN_OUTPUTS


def load_config(config_path: str) -> dict:
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    if config is None:
        raise ValueError(f"Config file is empty: {config_path}")

    return config


def get_keys(config: dict) -> List[str]:
    return config.get("keys", [])


def run_in_docker(config_path: str, author: str) -> int:
    """
    Run this script as root in a standard python container.
    Uses only locally available image (--pull never).
    """
    script_in_container = str(ROOT / "tools" / "move_to_author.py")
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "--pull",
        "never",
        "-v",
        f"{ROOT}:{ROOT}",
        "-w",
        str(ROOT),
        "-e",
        f"MOVE_CONFIG={config_path}",
        "-e",
        f"MOVE_AUTHOR={author}",
        "python:3-slim",
        "sh",
        "-c",
        "pip install -q --root-user-action=ignore PyYAML && python3 "
        + script_in_container
        + ' --config "$MOVE_CONFIG" --author "$MOVE_AUTHOR" --in-docker',
    ]
    result = subprocess.run(docker_cmd)
    return result.returncode


def change_ownership(path: str, uid: int, gid: int) -> None:
    """Recursively chown path and all contents to uid:gid."""
    for root, dirs, files in os.walk(path):
        os.chown(root, uid, gid)
        for f in files:
            os.chown(os.path.join(root, f), uid, gid)


def _is_permission_error(exc: BaseException) -> bool:
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError) and getattr(exc, "errno", None) == errno.EACCES:
        return True
    return False


def move_to_author(config_path: str, author: str) -> List[str]:
    """
    Move folders from esteban/outputs to <author>/outputs for keys in config.

    Args:
        config_path: Path to the YAML config file (must have 'keys' list).
        author: Target author name (e.g. esteban, jun1, div).

    Returns:
        List of keys that were successfully moved.
    """
    config = load_config(config_path)
    keys = get_keys(config)

    if not keys:
        print("No keys found in config")
        return []

    source_base = ESTEBAN_OUTPUTS
    dest_base = ROOT / author / "outputs"

    if not source_base.exists():
        print(f"Source directory does not exist: {source_base}")
        return []

    dest_base.mkdir(parents=True, exist_ok=True)

    moved = []
    for key in keys:
        source_dir = source_base / key
        dest_dir = dest_base / key

        if not source_dir.exists():
            print(f"Skip (not found): {key}")
            continue

        if dest_dir.exists():
            print(f"Skip (already exists): {dest_dir}")
            continue

        try:
            shutil.move(str(source_dir), str(dest_dir))
            change_ownership(str(dest_dir), RECONSTRUCTION_GROUP_UID, RECONSTRUCTION_GROUP_GID)
            print(f"Moved: {key}")
            moved.append(key)
        except (PermissionError, OSError) as e:
            if _is_permission_error(e):
                print(f"Permission denied moving {key}, re-running in docker...")
                raise
            print(f"Error moving {key}: {e}")

    return moved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Move output folders from esteban/outputs to <author>/outputs"
    )
    parser.add_argument("--config", "-c", required=True, help="Path to config.yaml")
    parser.add_argument("--author", "-a", required=True, help="Target author name")
    parser.add_argument("--in-docker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    config_path = str(Path(args.config).resolve())

    if args.in_docker:
        move_to_author(config_path, args.author)
    else:
        sys.exit(run_in_docker(config_path, args.author))


if __name__ == "__main__":
    main()
