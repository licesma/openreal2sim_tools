#!/usr/bin/env python3
"""
Extract background.jpg from scene.pkl for keys in a config file.

For each key, loads the numpy image from scene_dict["recon"]["background"]
and saves it as simulation/background.jpg.
"""
import yaml
import pickle
import numpy as np
from pathlib import Path
from typing import List
from PIL import Image

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


def extract_background_from_pkl(config_path: str, dry_run: bool = False, use_sam: bool = False) -> None:
    """
    Extract background.jpg from scene.pkl for all keys in config.

    Reads: RECONSTRUCTIONS/<week>/<author>/<key>/scene/scene.pkl
    Writes: RECONSTRUCTIONS/<week>/<author>/<key>/simulation/background.jpg

    Args:
        config_path: Path to the YAML config file containing 'keys'
        dry_run: Show what would be done without actually extracting
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
        extracted = 0
        already_exists = 0
        no_pkl = 0
        no_background_in_pkl = 0
        not_in_recon = 0
        ambiguous = 0
        errors = 0

        extracted_keys: List[str] = []
        failed_keys: List[str] = []

        print(f"\nExtracting background.jpg from scene.pkl:")
        print(f"Base path: {recon_outputs}")
        print(f"Keys to process: {len(keys)}")
        print(f"Dry run: {dry_run}\n")

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

            # Check if background.jpg already exists
            simulation_dir = source_dir / "simulation"
            background_path = simulation_dir / "background.jpg"
            
            if background_path.exists():
                print(f"⏭️  {key}: background.jpg already exists ({week}/{author}/{key})")
                already_exists += 1
                continue

            # Load scene.pkl
            scene_pkl_path = source_dir / "scene" / "scene.pkl"
            
            if not scene_pkl_path.exists():
                print(f"✗  {key}: scene.pkl not found ({week}/{author}/{key})")
                no_pkl += 1
                failed_keys.append(key)
                continue

            try:
                with open(scene_pkl_path, 'rb') as f:
                    scene_dict = pickle.load(f)
            except Exception as e:
                print(f"✗  {key}: error loading scene.pkl: {e}")
                errors += 1
                failed_keys.append(key)
                continue

            # Check for background in recon
            recon_data = scene_dict.get("recon", {})
            background_array = recon_data.get("background", None)

            if background_array is None:
                print(f"✗  {key}: no 'recon.background' in scene.pkl ({week}/{author}/{key})")
                no_background_in_pkl += 1
                failed_keys.append(key)
                continue

            # Save the background image
            if dry_run:
                print(f"🔍 {key}: would extract background.jpg ({week}/{author}/{key})")
                extracted += 1
                extracted_keys.append(key)
            else:
                try:
                    # Ensure simulation directory exists
                    simulation_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Convert numpy array to PIL Image and save
                    img = Image.fromarray(background_array.astype(np.uint8))
                    img.save(background_path, format="JPEG", quality=100)
                    
                    print(f"✓  {key}: extracted background.jpg ({week}/{author}/{key})")
                    extracted += 1
                    extracted_keys.append(key)
                except Exception as e:
                    print(f"✗  {key}: error saving background.jpg: {e}")
                    errors += 1
                    failed_keys.append(key)

        # Print summary
        print(f"\n{'='*60}")
        print("Summary: extract background.jpg from scene.pkl")
        print(f"{'='*60}")
        print(f"Total keys:           {len(keys)}")
        print(f"Extracted:            {extracted}")
        print(f"Already exists:       {already_exists}")
        print(f"No scene.pkl:         {no_pkl}")
        print(f"No background in pkl: {no_background_in_pkl}")
        print(f"Not in recon:         {not_in_recon}")
        print(f"Ambiguous:            {ambiguous}")
        print(f"Errors:               {errors}")
        
        if failed_keys:
            print(f"\nFailed keys:")
            for k in failed_keys:
                print(f"  - {k}")
        
        if extracted_keys:
            action = "Would extract" if dry_run else "Extracted"
            print(f"\n{action} keys:")
            for k in extracted_keys:
                print(f"  - {k}")
        
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract background.jpg from scene.pkl for all config keys"
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to the YAML config file containing 'keys'"
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be done without actually extracting"
    )
    parser.add_argument(
        "--use-sam",
        action="store_true",
        default=False,
        help="Use SAM path instead of HUNYUAN"
    )

    args = parser.parse_args()
    extract_background_from_pkl(args.config, dry_run=args.dry_run, use_sam=args.use_sam)
