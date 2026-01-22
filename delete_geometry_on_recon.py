#!/usr/bin/env python3
import shutil
from pathlib import Path

from paths import HUNYUAN, SAM


def delete_geometry_on_recon(base_dir: Path, week: str | None = None, author: str | None = None) -> None:
    """
    Delete the 'geometry' folder inside each scene under:
      RECONSTRUCTIONS/{week}/{author}/{scene}/geometry

    Args:
        base_dir: Base directory that contains 'week_*' subdirectories
        week: Optional specific week directory name to filter on (e.g., 'week_0')
        author: Optional author directory name to filter on (e.g., 'esteban')
    """
    if not base_dir.exists():
        print(f"Path does not exist: {base_dir}")
        return

    deleted = 0
    missing = 0
    errors = 0
    scenes_seen = 0

    for week_dir in base_dir.iterdir():
        if not week_dir.is_dir():
            continue
        if week is not None and week_dir.name != week:
            continue

        for author_dir in week_dir.iterdir():
            if not author_dir.is_dir():
                continue
            if author is not None and author_dir.name != author:
                continue

            for scene_dir in author_dir.iterdir():
                if not scene_dir.is_dir():
                    continue
                scenes_seen += 1
                geometry_path = scene_dir / "geometry"

                if geometry_path.exists():
                    try:
                        if geometry_path.is_dir():
                            shutil.rmtree(geometry_path)
                            deleted += 1
                        else:
                            geometry_path.unlink(missing_ok=True)
                            deleted += 1
                    except Exception as e:
                        print(f"Error deleting geometry for {scene_dir}: {e}")
                        errors += 1
                else:
                    missing += 1

    print(f"\n{'='*50}")
    print("Geometry deletion summary on reconstructions/data")
    scope = []
    if week is not None:
        scope.append(f"week={week}")
    if author is not None:
        scope.append(f"author={author}")
    print(f"Scope: {', '.join(scope) if scope else 'ALL weeks and authors'}")
    print(f"{'='*50}")
    print(f"Scene directories scanned: {scenes_seen}")
    print(f"'geometry' deleted: {deleted}")
    print(f"'geometry' missing: {missing}")
    print(f"Errors: {errors}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Delete the 'geometry' folder under each scene in "
            "RECONSTRUCTIONS/{week}/{author}/{scene}"
        )
    )
    parser.add_argument(
        "--week",
        "-w",
        required=False,
        help="Optional week directory to filter on (e.g., 'week_0'). Defaults to all weeks.",
    )
    parser.add_argument(
        "--author",
        "-a",
        required=False,
        help="Optional author to filter on (e.g., 'esteban'). Defaults to all authors.",
    )
    parser.add_argument(
        "--use-sam",
        action="store_true",
        default=False,
        help="Use SAM path instead of HUNYUAN",
    )

    args = parser.parse_args()
    base_dir = SAM if args.use_sam else HUNYUAN
    delete_geometry_on_recon(
        base_dir=base_dir,
        week=args.week,
        author=args.author,
    )

