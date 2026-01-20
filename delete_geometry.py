#!/usr/bin/env python3
import shutil
from pathlib import Path

from paths import ROOT


def delete_geometry_folders(author: str) -> None:
    """
    Delete the 'geometry' folder inside each key under ROOT/{author}/outputs/{key}.

    Args:
        author: The author name whose outputs directories will be processed
    """
    base_path = ROOT / author / "outputs"

    if not base_path.exists():
        print(f"Path does not exist: {base_path}")
        return

    deleted = 0
    missing = 0
    errors = 0

    for directory in base_path.iterdir():
        if not directory.is_dir():
            continue

        geometry_path = directory / "geometry"

        if geometry_path.exists():
            try:
                if geometry_path.is_dir():
                    shutil.rmtree(geometry_path)
                    deleted += 1
                else:
                    # If a non-directory named 'geometry' exists, remove it
                    geometry_path.unlink(missing_ok=True)  # Python 3.8+: safe on Linux; ignore if already gone
                    deleted += 1
            except Exception as e:
                print(f"Error deleting geometry for {directory.name}: {e}")
                errors += 1
        else:
            missing += 1

    print(f"\n{'='*50}")
    print(f"Geometry deletion summary for author: {author}")
    print(f"{'='*50}")
    print(f"Directories processed: {deleted + missing + errors}")
    print(f"'geometry' deleted: {deleted}")
    print(f"'geometry' missing: {missing}")
    print(f"Errors: {errors}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Delete the 'geometry' folder in each output directory for the given author"
    )
    parser.add_argument(
        "--author",
        "-a",
        required=True,
        help="Author name whose outputs/{key}/geometry folders will be deleted"
    )

    args = parser.parse_args()
    delete_geometry_folders(args.author)

