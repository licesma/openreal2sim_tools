#!/usr/bin/env python3
"""
Copy the 'mask' key from reconstructions scene.pkl to esteban outputs scene.pkl.

Source:      RECONSTRUCTIONS/<week>/<author>/<key>/scene/scene.pkl
Destination: ESTEBAN_OUTPUTS/<key>/scene/scene.pkl
"""
import pickle
import yaml
from pathlib import Path
from typing import List

from paths import RECONSTRUCTIONS, ESTEBAN_OUTPUTS


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


def copy_mask_to_outputs(config_path: str) -> None:
    """
    Copy the 'mask' key from reconstructions scene.pkl to esteban outputs scene.pkl.

    Source:      RECONSTRUCTIONS/<week>/<author>/<key>/scene/scene.pkl
    Destination: ESTEBAN_OUTPUTS/<key>/scene/scene.pkl
    """
    try:
        # Load configuration
        config = load_config(config_path)
        keys = get_keys(config)

        if not keys:
            print("No keys found in config")
            return

        # Set up paths
        recon_outputs = RECONSTRUCTIONS
        esteban_outputs = ESTEBAN_OUTPUTS

        # Validate source base directory exists
        if not recon_outputs.exists():
            print(f"Source base directory does not exist: {recon_outputs}")
            return

        if not esteban_outputs.exists():
            print(f"Destination base directory does not exist: {esteban_outputs}")
            return

        # Track statistics
        updated = 0
        skipped = 0
        errors: List[str] = []

        print(f"\nCopying 'mask' key from reconstructions to esteban outputs:")
        print(f"Source base: {recon_outputs}")
        print(f"Destination base: {esteban_outputs}")
        print(f"Keys to process: {keys}")
        print()

        for key in keys:
            try:
                # Find source path in reconstructions
                matches = find_key_paths_in_reconstructions(recon_outputs, key)
                if len(matches) == 0:
                    print(f"⏭️  Not found in reconstructions (skipping): {key}")
                    skipped += 1
                    continue
                if len(matches) > 1:
                    joined = ", ".join(str(p) for p in matches)
                    print(f"⏭️  Multiple matches found for {key} (skipping): {joined}")
                    skipped += 1
                    continue

                source_dir = matches[0]
                source_scene_pkl = source_dir / "scene" / "scene.pkl"

                # Check if source scene.pkl exists
                if not source_scene_pkl.exists():
                    print(f"⏭️  Source scene.pkl not found (skipping): {source_scene_pkl}")
                    skipped += 1
                    continue

                # Check destination scene.pkl
                dest_scene_pkl = esteban_outputs / key / "scene" / "scene.pkl"
                if not dest_scene_pkl.exists():
                    print(f"⏭️  Destination scene.pkl not found (skipping): {dest_scene_pkl}")
                    skipped += 1
                    continue

                # Load source scene.pkl
                with open(source_scene_pkl, "rb") as f:
                    source_data = pickle.load(f)

                if "mask" not in source_data:
                    print(f"⏭️  Source scene.pkl has no 'mask' key (skipping): {key}")
                    skipped += 1
                    continue

                # Load destination scene.pkl
                with open(dest_scene_pkl, "rb") as f:
                    dest_data = pickle.load(f)

                # Check if mask already exists
                if "mask" in dest_data:
                    print(f"⚠️  Destination already has 'mask' key, will overwrite: {key}")

                # Copy mask
                dest_data["mask"] = source_data["mask"]

                # Save updated destination scene.pkl
                with open(dest_scene_pkl, "wb") as f:
                    pickle.dump(dest_data, f)
                print(f"✓ Copied 'mask' key: {key}")

                updated += 1

            except Exception as e:
                error_msg = f"✗ Error processing {key}: {e}"
                print(error_msg)
                errors.append(error_msg)

        # Print summary
        print(f"\n{'='*60}")
        print("Summary for copy_mask_to_outputs")
        print(f"{'='*60}")
        print(f"Files updated: {updated}")
        print(f"Files skipped: {skipped}")
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
        description="Copy 'mask' key from reconstructions scene.pkl to esteban outputs scene.pkl"
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to the YAML config file containing 'keys'"
    )
    args = parser.parse_args()
    copy_mask_to_outputs(args.config)
