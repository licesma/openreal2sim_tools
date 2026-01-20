#!/usr/bin/env python3
import json
import shutil
import yaml
import os
from pathlib import Path
from typing import List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from paths import ROOT, ESTEBAN_OUTPUTS


def load_config(config_path: str) -> dict:
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    if config is None:
        raise ValueError(f"Config file is empty: {config_path}")

    return config


def get_author_keys(config: dict) -> List[str]:
    all_keys = config.get('keys', [])
    local_config = config.get('local', {})
    return list(local_config.keys()) if local_config else all_keys


def change_ownership(path: str, uid: int, gid: int) -> None:
    for root, dirs, files in os.walk(path):
        os.chown(root, uid, gid)
        for file in files:
            os.chown(os.path.join(root, file), uid, gid)


def move_author_files(author: str, config_path: str, log_file: str = None) -> List[str]:
    """
    Move files for a specific author from their outputs directory to esteban/outputs.

    Args:
        author: The author name whose files to move
        config_path: Path to the YAML config file
        log_file: If provided, write output to this file instead of stdout

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
        # Load configuration
        config = load_config(config_path)
        author_keys = get_author_keys(config)

        if not author_keys:
            log(f"No keys found for author '{author}' in config")
            return successful_keys

        # Set up paths
        author_outputs = ROOT / author / "outputs"
        esteban_outputs = ESTEBAN_OUTPUTS

        # Validate source directory exists
        if not author_outputs.exists():
            log(f"Author outputs directory does not exist: {author_outputs}")
            return successful_keys

        # Create destination directory if it doesn't exist
        if not esteban_outputs.exists():
            esteban_outputs.mkdir(parents=True, exist_ok=True)
            log(f"Created directory: {esteban_outputs}")

        # Track statistics
        moved = 0
        skipped = 0
        errors = []

        log(f"\nMoving files for author '{author}':")
        log(f"Source: {author_outputs}")
        log(f"Destination: {esteban_outputs}")
        log(f"Keys to move: {author_keys}\n")

        # Move each key's directory
        for key in author_keys:
            source_dir = author_outputs / key
            dest_dir = esteban_outputs / key

            if not source_dir.exists():
                log(f"⚠️  Source not found: {source_dir}")
                skipped += 1
                continue

            if dest_dir.exists():
                log(f"⏭️  Already exists (skipping): {dest_dir}")
                skipped += 1
                continue

            try:
                shutil.move(str(source_dir), str(dest_dir))
                change_ownership(str(dest_dir), 1044, 1045)
                log(f"✓ Moved: {key}")
                moved += 1
                successful_keys.append(key)
            except Exception as e:
                error_msg = f"✗ Error moving {key}: {e}"
                log(error_msg)
                errors.append(error_msg)

        # Print summary
        log(f"\n{'='*60}")
        log(f"Summary for author: {author}")
        log(f"{'='*60}")
        log(f"Files moved: {moved}")
        log(f"Files skipped: {skipped}")
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
        description="Move files for a specific author to esteban/outputs"
    )
    parser.add_argument(
        "--author",
        "-a",
        required=True,
        help="The author name whose files to move"
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to the YAML config file"
    )
    parser.add_argument(
        "--log-file",
        "-l",
        default=None,
        help="Path to log file (if not provided, prints to stdout)"
    )
    parser.add_argument(
        "--output-json",
        "-o",
        default=None,
        help="Path to JSON file to write successful keys"
    )

    args = parser.parse_args()
    successful = move_author_files(args.author, args.config, args.log_file)

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(successful, f)
