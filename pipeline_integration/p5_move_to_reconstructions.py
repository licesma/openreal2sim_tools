#!/usr/bin/env python3
import json
import shutil
import sys
from pathlib import Path
from typing import List, Tuple

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from paths import ESTEBAN_OUTPUTS, RECONSTRUCTIONS

RECON_OUTPUTS = RECONSTRUCTIONS


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
    return list(config.get("keys", []))


def load_metadata(source_dir: Path) -> Tuple[str, str]:
    """
    Load week and author from metadata.yaml in the given source directory.
    Returns (week, author).
    Raises ValueError if metadata is missing or incomplete.
    """
    metadata_file = source_dir / "metadata.yaml"
    if not metadata_file.exists():
        raise FileNotFoundError(f"metadata.yaml not found in {source_dir}")

    with open(metadata_file, "r") as f:
        metadata = yaml.safe_load(f) or {}

    week = metadata.get("week")
    author = metadata.get("author")
    if not week or not author:
        raise ValueError(f"Missing 'week' or 'author' in {metadata_file}")

    return week, author


def has_successful_reconstruction(source_dir: Path) -> bool:
    """
    Return True if metadata.yaml has reconstruction_status that indicates success.
    Accepts either boolean True or the string 'success' (case-insensitive).
    """
    metadata_file = source_dir / "metadata.yaml"
    if not metadata_file.exists():
        return False
    try:
        with open(metadata_file, "r") as f:
            metadata = yaml.safe_load(f) or {}
    except Exception:
        return False

    status = metadata.get("reconstruction_status")
    if isinstance(status, bool):
        return status is True
    if isinstance(status, str):
        return status.strip().lower() == "success"
    return False


def move_to_reconstructions(config_path: str, log_file: str = None, require_success: bool = False) -> List[str]:
    """
    Move folders for all keys from esteban outputs to reconstructions outputs,
    organized by week and author.

    Source:      ESTEBAN_OUTPUTS/<key>
    Destination: RECONSTRUCTIONS/<week>/<author>/<key>

    Args:
        config_path: Path to the YAML config file containing 'keys'
        log_file: If provided, write output to this file instead of stdout
        require_success: Only move keys whose metadata has reconstruction_status=success

    Returns:
        List of keys that were successfully moved
    """
    successful_keys: List[str] = []

    def log(msg: str) -> None:
        if log_file:
            with open(log_file, "a") as f:
                f.write(msg + "\n")
        else:
            print(msg)

    try:
        config = load_config(config_path)
        keys = get_keys(config)

        if not keys:
            log("No keys found in config")
            return successful_keys

        if not ESTEBAN_OUTPUTS.exists():
            log(f"Source base directory does not exist: {ESTEBAN_OUTPUTS}")
            return successful_keys

        if not RECON_OUTPUTS.exists():
            RECON_OUTPUTS.mkdir(parents=True, exist_ok=True)
            log(f"Created directory: {RECON_OUTPUTS}")

        moved = 0
        skipped = 0
        errors: List[str] = []

        log(f"\nMoving esteban outputs to reconstructions (by week/author):")
        log(f"Source: {ESTEBAN_OUTPUTS}")
        log(f"Destination: {RECON_OUTPUTS}")
        log(f"Keys: {keys}")
        if require_success:
            log("Require success: True")
        log("")

        for key in keys:
            source_dir = ESTEBAN_OUTPUTS / key

            if not source_dir.exists():
                log(f"⚠️  Source not found: {source_dir}")
                skipped += 1
                continue

            try:
                # If required, ensure reconstruction_status indicates success
                if require_success and not has_successful_reconstruction(source_dir):
                    log(f"⏭️  Not successful or missing status (skipping): {key}")
                    skipped += 1
                    continue

                # Determine destination using metadata
                week, author = load_metadata(source_dir)
                dest_dir = RECON_OUTPUTS / week / author / key

                if dest_dir.exists():
                    log(f"⏭️  Already exists (skipping): {dest_dir}")
                    skipped += 1
                    continue

                # Ensure parent directories exist
                dest_dir.parent.mkdir(parents=True, exist_ok=True)

                shutil.move(str(source_dir), str(dest_dir))
                log(f"✓ Moved: {key} -> {week}/{author}/{key}")
                moved += 1
                successful_keys.append(key)

            except Exception as e:
                error_msg = f"✗ Error moving {key}: {e}"
                log(error_msg)
                errors.append(error_msg)

        log(f"\n{'='*60}")
        log("Summary for move_to_reconstructions")
        log(f"{'='*60}")
        log(f"Moved: {moved}")
        log(f"Skipped: {skipped}")
        log(f"Errors: {len(errors)}")
        if errors:
            log("\nError details:")
            for error in errors:
                log(f"  {error}")
        log(f"{'='*60}\n")

    except Exception as e:
        log(f"Error: {e}")

    return successful_keys


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Move esteban outputs to reconstructions (data/<week>/<author>/<key>)"
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to the YAML config file containing 'keys'",
    )
    parser.add_argument(
        "--log-file",
        "-l",
        default=None,
        help="Path to log file (if not provided, prints to stdout)",
    )
    parser.add_argument(
        "--output-json",
        "-o",
        default=None,
        help="Path to JSON file to write successful keys",
    )
    parser.add_argument(
        "--require-success",
        "-r",
        action="store_true",
        default=False,
        help="Only move keys whose metadata has reconstruction_status=success",
    )

    args = parser.parse_args()
    successful = move_to_reconstructions(args.config, args.log_file, args.require_success)

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(successful, f)
