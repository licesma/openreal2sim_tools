#!/usr/bin/env python3
import shutil
import yaml
import os
from pathlib import Path
from typing import List, Optional, Tuple

from paths import HUNYUAN, SAM, ESTEBAN_OUTPUTS


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


def move_reconstructions_to_esteban_outputs(config_path: str, overwrite: bool = False, use_sam: bool = False) -> None:
    """
    Move folders for all keys from reconstructions outputs back to esteban outputs.

    Source:      RECONSTRUCTIONS/<week>/<author>/<key>
    Destination: ESTEBAN_OUTPUTS/<key>

    Args:
        config_path: Path to the YAML config file containing 'keys'
        overwrite: If set, overwrite existing destination folders in outputs
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
        esteban_outputs = ESTEBAN_OUTPUTS

        # Validate source base directory exists
        if not recon_outputs.exists():
            print(f"Source base directory does not exist: {recon_outputs}")
            return

        # Create destination directory if it doesn't exist
        if not esteban_outputs.exists():
            esteban_outputs.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {esteban_outputs}")

        # Track statistics
        moved = 0
        skipped = 0
        errors: List[str] = []

        print(f"\nMoving reconstructions back to esteban outputs:")
        print(f"Source: {recon_outputs}")
        print(f"Destination: {esteban_outputs}")
        print(f"Keys to move: {keys}\n")

        for key in keys:
            try:
                matches = find_key_paths_in_reconstructions(recon_outputs, key)
                if len(matches) == 0:
                    print(f"⏭️  Not found in reconstructions (skipping): {key}")
                    skipped += 1
                    continue
                if len(matches) > 1:
                    # Ambiguous; do not guess
                    joined = ", ".join(str(p) for p in matches)
                    print(f"⏭️  Multiple matches found for {key} (skipping): {joined}")
                    skipped += 1
                    continue

                source_dir = matches[0]
                # Extract week/author for logging
                week = source_dir.parents[1].name if len(source_dir.parents) >= 2 else "unknown_week"
                author = source_dir.parents[0].name if len(source_dir.parents) >= 1 else "unknown_author"

                dest_dir = esteban_outputs / key

                if dest_dir.exists():
                    if overwrite:
                        # Remove existing destination before move
                        print(f"⚠️  Destination exists, removing due to --overwrite: {dest_dir}")
                        shutil.rmtree(dest_dir)
                    else:
                        print(f"⏭️  Already exists (skipping): {dest_dir}")
                        skipped += 1
                        continue

                # Ensure parent directory exists
                dest_dir.parent.mkdir(parents=True, exist_ok=True)

                shutil.move(str(source_dir), str(dest_dir))
                print(f"✓ Moved: {week}/{author}/{key} -> outputs/{key}")
                moved += 1
            except Exception as e:
                error_msg = f"✗ Error moving {key}: {e}"
                print(error_msg)
                errors.append(error_msg)

        # Print summary
        print(f"\n{'='*60}")
        print("Summary for move_from_reconstructions (to outputs)")
        print(f"{'='*60}")
        print(f"Folders moved: {moved}")
        print(f"Folders skipped: {skipped}")
        print(f"Errors: {len(errors)}")
        if errors:
            print("\nError details:")
            for error in errors:
                print(f"  {error}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Move reconstructions (data/<week>/<author>/<key>) back to esteban outputs for all config keys"
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to the YAML config file containing 'keys'"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="If set, overwrite existing destination folders in outputs"
    )
    parser.add_argument(
        "--use-sam",
        action="store_true",
        default=False,
        help="Use SAM path instead of HUNYUAN"
    )

    args = parser.parse_args()
    move_reconstructions_to_esteban_outputs(args.config, overwrite=args.overwrite, use_sam=args.use_sam)


