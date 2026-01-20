#!/usr/bin/env python3
import json
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from paths import ESTEBAN_OUTPUTS

OUTPUTS_BASE = ESTEBAN_OUTPUTS


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


def move_scenario_scene_to_reconstruction_root(reconstruction_dir: Path) -> Tuple[bool, Optional[str]]:
    """
    Move:
      reconstruction/scenario/scene_optimized.glb -> reconstruction/scene.glb
    Returns (changed, error_message)
    """
    try:
        scenario_file = reconstruction_dir / "scenario" / "scene_optimized.glb"
        dest_file = reconstruction_dir / "scene.glb"
        if scenario_file.exists():
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            if dest_file.exists():
                dest_file.unlink()
            scenario_file.rename(dest_file)
            return True, None
        return False, None
    except Exception as e:
        return False, f"move_scenario_scene_to_reconstruction_root: {e}"


def prune_objects_to_mp4_only(objects_dir: Path) -> Tuple[int, Optional[str]]:
    """
    In reconstruction/objects, keep only *.mp4 files and delete everything else.
    Returns (num_deleted, error_message)
    """
    if not objects_dir.exists():
        return 0, None
    deleted = 0
    try:
        for item in objects_dir.iterdir():
            if item.is_file() and item.suffix.lower() != ".mp4":
                item.unlink(missing_ok=True)
                deleted += 1
        return deleted, None
    except Exception as e:
        return deleted, f"prune_objects_to_mp4_only: {e}"


def list_mp4_files(objects_dir: Path) -> List[str]:
    """
    Return a sorted (non-recursive) list of .mp4 filenames within objects_dir.
    """
    if not objects_dir.exists() or not objects_dir.is_dir():
        return []
    mp4_names: List[str] = []
    for item in objects_dir.iterdir():
        if item.is_file() and item.suffix.lower() == ".mp4":
            mp4_names.append(item.name)
    mp4_names.sort()
    return mp4_names


def write_objects_index(objects_dir: Path) -> Tuple[Tuple[int, bool], Optional[str]]:
    """
    Write index.json under reconstruction/objects listing all .mp4 filenames.
    Returns ((num_entries, was_overwrite), error_message)
    """
    try:
        if not objects_dir.exists() or not objects_dir.is_dir():
            return (0, False), None
        index_path = objects_dir / "index.json"
        was_overwrite = index_path.exists()
        filenames = list_mp4_files(objects_dir)
        with open(index_path, "w") as f:
            json.dump(filenames, f, indent=2)
            f.write("\n")
        return (len(filenames), was_overwrite), None
    except Exception as e:
        return (0, False), f"write_objects_index: {e}"


def prune_scene_to_only_pkl(scene_dir: Path) -> Tuple[int, Optional[str]]:
    """
    Under /scene keep only scene.pkl; delete everything else (including subdirectories).
    Returns (num_deleted, error_message)
    """
    if not scene_dir.exists():
        return 0, None
    deleted = 0
    try:
        for item in scene_dir.iterdir():
            if item.is_file() and item.name != "scene.pkl":
                item.unlink(missing_ok=True)
                deleted += 1
            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
                deleted += 1
        return deleted, None
    except Exception as e:
        return deleted, f"prune_scene_to_only_pkl: {e}"


def find_first_image_in_images(images_dir: Path) -> Optional[Path]:
    """
    Frames will always have 5 zeros. Use exactly 'frame_00000.jpg'.
    """
    if not images_dir.exists():
        return None
    candidate = images_dir / "frame_00000.jpg"
    return candidate if candidate.exists() else None


def find_first_image_in_resized(resized_dir: Path) -> Optional[Path]:
    """
    Resized images will always have 6 zeros. Use exactly '000000.jpg'.
    """
    if not resized_dir.exists():
        return None
    candidate = resized_dir / "000000.jpg"
    return candidate if candidate.exists() else None


def create_source_with_first_frames(key_dir: Path) -> Tuple[int, Optional[str]]:
    """
    Create /source and copy first frames from:
      - images/ -> first frame_*.jpg
      - resized_images/ -> first numeric *.jpg
    Files are copied preserving the original filename.
    Returns (num_copied, error_message)
    """
    copied = 0
    try:
        source_dir = key_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)

        first_img = find_first_image_in_images(key_dir / "images")
        if first_img is not None and first_img.exists():
            shutil.copy2(first_img, source_dir / first_img.name)
            copied += 1

        first_resized = find_first_image_in_resized(key_dir / "resized_images")
        if first_resized is not None and first_resized.exists():
            shutil.copy2(first_resized, source_dir / first_resized.name)
            copied += 1

        return copied, None
    except Exception as e:
        return copied, f"create_source_with_first_frames: {e}"


def clean_reconstruction_keep_only_objects_and_scene(reconstruction_dir: Path) -> Tuple[Tuple[int, int], Optional[str]]:
    """
    In reconstruction/, keep only:
      - objects/ (directory, contents already filtered elsewhere)
      - scene.glb (file at reconstruction root)
    Delete everything else.
    Returns ((files_deleted, dirs_deleted), error_message)
    """
    if not reconstruction_dir.exists():
        return (0, 0), None
    files_deleted = 0
    dirs_deleted = 0
    try:
        for item in reconstruction_dir.iterdir():
            if item.is_dir():
                if item.name != "objects":
                    shutil.rmtree(item, ignore_errors=True)
                    dirs_deleted += 1
            else:
                if item.name != "scene.glb":
                    item.unlink(missing_ok=True)
                    files_deleted += 1
        return (files_deleted, dirs_deleted), None
    except Exception as e:
        return (files_deleted, dirs_deleted), f"clean_reconstruction_keep_only_objects_and_scene: {e}"


def delete_other_top_level_dirs(key_dir: Path, keep: List[str]) -> Tuple[int, Optional[str]]:
    """
    Delete all top-level directories under key_dir except those in 'keep'.
    Returns (dirs_deleted, error_message)
    """
    if not key_dir.exists():
        return 0, None
    deleted = 0
    try:
        for item in key_dir.iterdir():
            if item.is_dir() and item.name not in keep:
                shutil.rmtree(item, ignore_errors=True)
                deleted += 1
        return deleted, None
    except Exception as e:
        return deleted, f"delete_other_top_level_dirs: {e}"


def prepare_one_key(key: str, log) -> bool:
    """
    Prepare one key for storage. Returns True if ALL steps succeeded.
    """
    key_dir = OUTPUTS_BASE / key
    if not key_dir.exists():
        log(f"⚠️  Key directory not found (skipping): {key_dir}")
        return False

    reconstruction_dir = key_dir / "reconstruction"
    objects_dir = reconstruction_dir / "objects"
    scene_dir = key_dir / "scene"

    log(f"\nProcessing: {key_dir}")

    all_success = True

    moved, move_err = move_scenario_scene_to_reconstruction_root(reconstruction_dir)
    if move_err:
        log(f"  ✗ {move_err}")
        all_success = False
    else:
        if moved:
            log("  ✓ Moved scenario/scene_optimized.glb -> reconstruction/scene.glb")
        else:
            log("  • scenario/scene_optimized.glb not found (no move)")

    deleted_non_mp4, obj_err = prune_objects_to_mp4_only(objects_dir)
    if obj_err:
        log(f"  ✗ {obj_err}")
        all_success = False
    else:
        log(f"  ✓ reconstruction/objects: deleted {deleted_non_mp4} non-mp4 files")

    (entries_written, was_overwrite), idx_err = write_objects_index(objects_dir)
    if idx_err:
        log(f"  ✗ {idx_err}")
        all_success = False
    else:
        action = "Overwrote" if was_overwrite else "Created"
        log(f"  ✓ reconstruction/objects: {action} index.json with {entries_written} entrie(s)")

    scene_deleted, scene_err = prune_scene_to_only_pkl(scene_dir)
    if scene_err:
        log(f"  ✗ {scene_err}")
        all_success = False
    else:
        log(f"  ✓ scene/: deleted {scene_deleted} non-scene.pkl files")

    copied, src_err = create_source_with_first_frames(key_dir)
    if src_err:
        log(f"  ✗ {src_err}")
        all_success = False
    else:
        log(f"  ✓ source/: copied {copied} file(s)")

    (files_deleted, dirs_deleted), clean_recon_err = clean_reconstruction_keep_only_objects_and_scene(reconstruction_dir)
    if clean_recon_err:
        log(f"  ✗ {clean_recon_err}")
        all_success = False
    else:
        log(f"  ✓ reconstruction/: deleted {files_deleted} file(s), {dirs_deleted} dir(s) (kept objects/ and scene.glb)")

    keep_dirs = ["simulation", "reconstruction", "scene", "source", "metadata.yaml"]
    deleted_dirs, del_top_err = delete_other_top_level_dirs(key_dir, keep=keep_dirs)
    if del_top_err:
        log(f"  ✗ {del_top_err}")
        all_success = False
    else:
        log(f"  ✓ top-level: deleted {deleted_dirs} non-essential directorie(s)")

    return all_success


def prepare_for_storage(config_path: str, log_file: str = None) -> List[str]:
    """
    Prepare output directories for storage by pruning and consolidating files.

    Args:
        config_path: Path to the YAML config file containing 'keys'
        log_file: If provided, write output to this file instead of stdout

    Returns:
        List of keys that were successfully prepared (all steps passed)
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

        log(f"\nPreparing storage for keys in base: {OUTPUTS_BASE}")
        log(f"Keys: {keys}\n")

        for key in keys:
            try:
                success = prepare_one_key(key, log)
                if success:
                    successful_keys.append(key)
            except Exception as e:
                log(f"✗ Error processing {key}: {e}")

        log(f"\n{'=' * 60}")
        log("Summary for prepare_for_storage")
        log(f"{'=' * 60}")
        log(f"Successful: {len(successful_keys)}/{len(keys)}")
        log(f"{'=' * 60}\n")

    except Exception as e:
        log(f"Error: {e}")

    return successful_keys


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Prepare output directories for storage by pruning and consolidating files."
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to YAML config containing 'keys'",
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
    successful = prepare_for_storage(args.config, args.log_file)

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(successful, f)
