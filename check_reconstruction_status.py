#!/usr/bin/env python3
"""
Check reconstruction_status in metadata.yaml for a subset of keys from config.

For each key, reads ESTEBAN_OUTPUTS/<key>/metadata.yaml and reports whether
reconstruction_status is present and equals 'success'.
"""
import yaml
from pathlib import Path
from typing import List, Optional

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


def has_successful_reconstruction(key_dir: Path) -> bool:
    """
    Return True if metadata.yaml has reconstruction_status that indicates success.
    Accepts either boolean True or the string 'success' (case-insensitive).
    """
    metadata_file = key_dir / "metadata.yaml"
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


def check_reconstruction_status(
    config_path: str,
    keys_subset: Optional[List[str]] = None,
    output_base: Optional[Path] = None,
) -> None:
    """
    For each key (from config or keys_subset), check ESTEBAN_OUTPUTS/<key>/metadata.yaml
    for reconstruction_status: success.

    Args:
        config_path: Path to the YAML config file containing 'keys'
        keys_subset: If provided, only check these keys (must be a subset of config keys).
                    If None, check all keys from config.
        output_base: Base path for key folders (default: ESTEBAN_OUTPUTS).
                    Each key is looked up at output_base/<key>/metadata.yaml.
    """
    base = output_base if output_base is not None else ESTEBAN_OUTPUTS

    try:
        config = load_config(config_path)
        all_keys = get_keys(config)

        if keys_subset is not None:
            keys_to_check = [k for k in keys_subset if k in all_keys]
            unknown = set(keys_subset) - set(all_keys)
            if unknown:
                print(f"⚠️  Keys not in config (skipping): {sorted(unknown)}")
        else:
            keys_to_check = all_keys

        if not keys_to_check:
            print("No keys to check")
            return

        success_keys: List[str] = []
        no_metadata: List[str] = []
        not_success: List[str] = []

        print(f"\nChecking reconstruction_status in metadata.yaml:")
        print(f"Base path: {base}")
        print(f"Keys to check: {len(keys_to_check)}\n")

        for key in keys_to_check:
            key_dir = base / key
            metadata_path = key_dir / "metadata.yaml"

            if not metadata_path.exists():
                print(f"✗  {key}: no metadata.yaml at {key_dir / 'metadata.yaml'}")
                no_metadata.append(key)
                continue

            if has_successful_reconstruction(key_dir):
                print(f"✓  {key}: reconstruction_status = success")
                success_keys.append(key)
            else:
                print(f"✗  {key}: reconstruction_status is not success (or missing)")
                not_success.append(key)

        # Summary
        print(f"\n{'='*60}")
        print("Summary: reconstruction_status check")
        print(f"{'='*60}")
        print(f"Total checked:     {len(keys_to_check)}")
        print(f"Success:           {len(success_keys)}")
        print(f"Not success:       {len(not_success)}")
        print(f"No metadata.yaml:  {len(no_metadata)}")

        if success_keys:
            print(f"\nKeys with reconstruction_status=success:")
            for k in success_keys:
                print(f"  - {k}")
            print(f"\nCopy-paste YAML (success keys):")
            print("---")
            print(yaml.dump({"keys": success_keys}, default_flow_style=False, sort_keys=False), end="")
        if not_success:
            print(f"\nKeys without success:")
            for k in not_success:
                print(f"  - {k}")
        if no_metadata:
            print(f"\nKeys missing metadata.yaml:")
            for k in no_metadata:
                print(f"  - {k}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Check reconstruction_status=success in metadata.yaml for config keys"
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to the YAML config file containing 'keys'",
    )
    parser.add_argument(
        "--keys",
        "-k",
        default=None,
        help="Comma-separated subset of keys to check (default: all keys from config)",
    )
    parser.add_argument(
        "--output-base",
        "-o",
        default=None,
        help="Base path for key folders (default: ESTEBAN_OUTPUTS, e.g. .../esteban/outputs)",
    )

    args = parser.parse_args()

    keys_subset = None
    if args.keys:
        keys_subset = [k.strip() for k in args.keys.split(",") if k.strip()]

    output_base = None
    if args.output_base:
        output_base = Path(args.output_base)

    check_reconstruction_status(
        config_path=args.config,
        keys_subset=keys_subset,
        output_base=output_base,
    )
