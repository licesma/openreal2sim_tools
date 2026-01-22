#!/usr/bin/env python3
import yaml
from pathlib import Path
from typing import List

from paths import HUNYUAN, SAM


def load_config(config_path: str) -> dict:
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    if config is None:
        raise ValueError(f"Config file is empty: {config_path}")

    return config


def get_keys(config: dict) -> List[str]:
    return list(config.get('keys', []))


def find_key_paths_in_reconstructions(recon_base: Path, key: str) -> List[Path]:
    """
    Search for directories matching reconstructions/data/<week>/<author>/<key>.
    Return a list of matching Paths. Normally there should be 0 or 1.
    """
    matches: List[Path] = []
    if not recon_base.exists():
        return matches
    for week_dir in recon_base.iterdir():
        if not week_dir.is_dir():
            continue
        for author_dir in week_dir.iterdir():
            if not author_dir.is_dir():
                continue
            candidate = author_dir / key
            if candidate.exists() and candidate.is_dir():
                matches.append(candidate)
    return matches


def check_background_jpg(config_path: str, use_sam: bool = False) -> None:
    """
    Check if background.jpg exists for all keys in reconstructions.

    Checks: RECONSTRUCTIONS/<week>/<author>/<key>/simulation/background.jpg

    Args:
        config_path: Path to the YAML config file containing 'keys'
        use_sam: If True, use SAM path instead of HUNYUAN
    """
    try:
        # Load configuration
        config = load_config(config_path)
        keys = get_keys(config)

        if not keys:
            print("No keys found in config")
            return

        # Set up paths
        recon_outputs = SAM if use_sam else HUNYUAN

        # Validate source base directory exists
        if not recon_outputs.exists():
            print(f"Reconstructions directory does not exist: {recon_outputs}")
            return

        # Track statistics
        found = 0
        missing = 0
        not_in_recon = 0
        ambiguous = 0

        found_keys: List[str] = []
        missing_keys: List[str] = []

        print(f"\nChecking for background.jpg in reconstructions:")
        print(f"Base path: {recon_outputs}")
        print(f"Keys to check: {len(keys)}\n")

        for key in keys:
            matches = find_key_paths_in_reconstructions(recon_outputs, key)
            
            if len(matches) == 0:
                print(f"⏭️  {key}: not found in reconstructions")
                not_in_recon += 1
                continue
            
            if len(matches) > 1:
                joined = ", ".join(str(p) for p in matches)
                print(f"⚠️  {key}: multiple matches (skipping): {joined}")
                ambiguous += 1
                continue

            source_dir = matches[0]
            week = source_dir.parents[1].name if len(source_dir.parents) >= 2 else "unknown_week"
            author = source_dir.parents[0].name if len(source_dir.parents) >= 1 else "unknown_author"

            background_path = source_dir / "simulation" / "background.jpg"

            if background_path.exists():
                print(f"✓  {key}: {week}/{author}/{key}/simulation/background.jpg")
                found += 1
                found_keys.append(key)
            else:
                print(f"✗  {key}: missing ({week}/{author}/{key}/simulation/background.jpg)")
                missing += 1
                missing_keys.append(key)

        # Print summary
        print(f"\n{'='*60}")
        print("Summary: background.jpg check")
        print(f"{'='*60}")
        print(f"Total keys:        {len(keys)}")
        print(f"Found:             {found}")
        print(f"Missing:           {missing}")
        print(f"Not in recon:      {not_in_recon}")
        print(f"Ambiguous:         {ambiguous}")
        
        if missing_keys:
            print(f"\nKeys missing background.jpg:")
            for k in missing_keys:
                print(f"  - {k}")
        
        if found_keys:
            print(f"\nKeys with background.jpg:")
            for k in found_keys:
                print(f"  - {k}")
        
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Check if background.jpg exists in simulation folder for all config keys"
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to the YAML config file containing 'keys'"
    )
    parser.add_argument(
        "--use-sam",
        action="store_true",
        default=False,
        help="Use SAM path instead of HUNYUAN"
    )

    args = parser.parse_args()
    check_background_jpg(args.config, use_sam=args.use_sam)
