#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from typing import List

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from paths import ESTEBAN_OUTPUTS


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


def fill_metadata(config_path: str, author: str, week: str, log_file: str = None) -> List[str]:
    """
    Fill metadata.yaml for each key in the config with author, status, and week.

    For each key in the config, open or create:
      ESTEBAN_OUTPUTS/<key>/metadata.yaml
    and set the YAML fields:
      author: <author>
      status: pending
      week: <week>

    Args:
        config_path: Path to the YAML config file containing 'keys'
        author: Author name to set in metadata
        week: Week value to set in metadata
        log_file: If provided, write output to this file instead of stdout

    Returns:
        List of keys that were successfully updated
    """
    successful_keys: List[str] = []

    def log(msg: str) -> None:
        if log_file:
            with open(log_file, "a") as f:
                f.write(msg + "\n")
        else:
            print(msg)

    STATUS_VALUE = "pending"

    try:
        config = load_config(config_path)
        keys = get_keys(config)

        if not keys:
            log("No keys found in config")
            return successful_keys

        outputs_base = ESTEBAN_OUTPUTS
        if not outputs_base.exists():
            log(f"Base outputs directory not found: {outputs_base}")
            return successful_keys

        updated_count = 0
        skipped_count = 0
        created_count = 0
        errors: List[str] = []

        log(f"\nFilling metadata for keys:")
        log(f"Base: {outputs_base}")
        log(f"Keys: {keys}")
        log(f"Setting author: {author}")
        log(f"Setting status: {STATUS_VALUE}")
        log(f"Setting week: {week}\n")

        for key in keys:
            key_dir = outputs_base / key
            metadata_file = key_dir / "metadata.yaml"

            if not key_dir.exists():
                log(f"⚠️  Key directory not found (skipping): {key_dir}")
                skipped_count += 1
                continue

            try:
                # Load existing metadata or create new
                if metadata_file.exists():
                    with open(metadata_file, "r") as f:
                        data = yaml.safe_load(f) or {}
                else:
                    data = {}
                    created_count += 1

                # Update all fields
                data["author"] = author
                data["status"] = STATUS_VALUE
                data["week"] = week

                # Write back preserving readability
                with open(metadata_file, "w") as f:
                    yaml.safe_dump(
                        data,
                        f,
                        default_flow_style=False,
                        sort_keys=False,
                        allow_unicode=True,
                    )

                log(f"✓ Updated: {key}")
                updated_count += 1
                successful_keys.append(key)

            except Exception as e:
                error_msg = f"✗ Error updating {key}: {e}"
                log(error_msg)
                errors.append(error_msg)

        # Print summary
        log(f"\n{'=' * 60}")
        log("Summary for fill_metadata")
        log(f"{'=' * 60}")
        log(f"Updated: {updated_count}")
        log(f"Created metadata.yaml: {created_count}")
        log(f"Skipped: {skipped_count}")
        log(f"Errors: {len(errors)}")
        if errors:
            log("\nError details:")
            for error in errors:
                log(f"  {error}")
        log(f"{'=' * 60}\n")

    except Exception as e:
        log(f"Error: {e}")

    return successful_keys


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fill metadata.yaml with author, status (pending), and week for all keys in config"
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to the YAML config file containing 'keys'",
    )
    parser.add_argument(
        "--author",
        "-a",
        required=True,
        help="Author name to set in metadata.yaml",
    )
    parser.add_argument(
        "--week",
        "-w",
        required=True,
        help="Week value to set in metadata.yaml (e.g., week_1)",
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

    args = parser.parse_args()
    successful = fill_metadata(args.config, args.author, args.week, args.log_file)

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(successful, f)
