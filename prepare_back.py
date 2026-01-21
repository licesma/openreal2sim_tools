#!/usr/bin/env python3
"""
Copy scene data from reconstructions scene.pkl to esteban outputs.

Source:      RECONSTRUCTIONS/<week>/<author>/<key>/scene/scene.pkl
Destination: ESTEBAN_OUTPUTS/<key>/scene/scene.pkl

This script:
1. Creates the folder structure if it doesn't exist
2. Copies only these keys: 'images', 'depths', 'intrinsics', 'extrinsics', 'n_frames', 'height', 'width', 'mask'
3. Creates resized_images/ folder with jpg images from the 'images' key
"""
import cv2
import pickle
import yaml
import numpy as np
from pathlib import Path
from typing import List

from paths import RECONSTRUCTIONS, ESTEBAN_OUTPUTS


# Keys to copy from source to destination
KEYS_TO_COPY = [
    'images',
    'depths',
    'intrinsics',
    'extrinsics',
    'n_frames',
    'height',
    'width',
    'mask',
]


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


def save_images_to_folder(images: np.ndarray, output_dir: Path) -> int:
    """
    Save images from numpy array to jpg files.
    
    Args:
        images: numpy array of shape (N, H, W, 3) in RGB format
        output_dir: directory to save images to
        
    Returns:
        Number of images saved
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    n_images = len(images)
    for i in range(n_images):
        img_rgb = images[i]
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        output_path = output_dir / f"{i:06d}.jpg"
        cv2.imwrite(str(output_path), img_bgr)
    
    return n_images


def copy_scene_to_outputs(config_path: str) -> None:
    """
    Copy scene data from reconstructions scene.pkl to esteban outputs.

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

        # Create esteban outputs if it doesn't exist
        esteban_outputs.mkdir(parents=True, exist_ok=True)

        # Track statistics
        created = 0
        skipped = 0
        errors: List[str] = []

        print(f"\nCopying scene data from reconstructions to esteban outputs:")
        print(f"Source base: {recon_outputs}")
        print(f"Destination base: {esteban_outputs}")
        print(f"Keys to copy: {KEYS_TO_COPY}")
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

                # Create destination directory structure
                dest_key_dir = esteban_outputs / key
                dest_scene_dir = dest_key_dir / "scene"
                dest_scene_pkl = dest_scene_dir / "scene.pkl"
                dest_resized_dir = dest_key_dir / "resized_images"

                # Create directories
                dest_scene_dir.mkdir(parents=True, exist_ok=True)
                dest_resized_dir.mkdir(parents=True, exist_ok=True)

                # Load source scene.pkl
                with open(source_scene_pkl, "rb") as f:
                    source_data = pickle.load(f)

                # Extract only the keys we want
                dest_data = {}
                missing_keys = []
                for k in KEYS_TO_COPY:
                    if k in source_data:
                        dest_data[k] = source_data[k]
                    else:
                        missing_keys.append(k)

                if missing_keys:
                    print(f"  ⚠️  Missing keys in source: {missing_keys}")

                # Check if 'images' key exists for resized_images
                if 'images' not in dest_data:
                    print(f"⏭️  No 'images' key in source (skipping): {key}")
                    skipped += 1
                    continue

                # Save the filtered scene.pkl
                with open(dest_scene_pkl, "wb") as f:
                    pickle.dump(dest_data, f)

                # Save images to resized_images folder
                n_images = save_images_to_folder(dest_data['images'], dest_resized_dir)

                print(f"✓ Created: {key}")
                print(f"    → scene.pkl with keys: {list(dest_data.keys())}")
                print(f"    → resized_images/ with {n_images} images")

                created += 1

            except Exception as e:
                error_msg = f"✗ Error processing {key}: {e}"
                print(error_msg)
                errors.append(error_msg)

        # Print summary
        print(f"\n{'='*60}")
        print("Summary for copy_scene_to_outputs")
        print(f"{'='*60}")
        print(f"Directories created: {created}")
        print(f"Keys skipped: {skipped}")
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
        description="Copy scene data from reconstructions scene.pkl to esteban outputs"
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to the YAML config file containing 'keys'"
    )
    args = parser.parse_args()
    copy_scene_to_outputs(args.config)
