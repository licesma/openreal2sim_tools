#!/usr/bin/env python3
"""
Change ownership of ESTEBAN_OUTPUTS and all subfolders recursively.
Uses Docker to run as root since chown requires elevated privileges.
"""
import subprocess
import sys
from pathlib import Path

from paths import ESTEBAN_OUTPUTS


def fix_ownership() -> None:
    """
    Change ownership of esteban/outputs recursively using Docker.
    Sets ownership to uid=1044, gid=1045.
    """
    target_path = ESTEBAN_OUTPUTS
    docker_dir = Path("/data2/openreal2sim/scripts/docker")
    
    if not target_path.exists():
        print(f"Target directory does not exist: {target_path}")
        sys.exit(1)
    
    if not docker_dir.exists():
        print(f"Docker directory does not exist: {docker_dir}")
        sys.exit(1)
    
    print(f"Changing ownership of: {target_path}")
    print("Setting uid=1044, gid=1045 recursively...")
    print()
    
    # Use docker compose to run chown as root
    cmd = [
        "docker", "compose", "-f", str(docker_dir / "compose.yml"),
        "run", "--rm", "from_others",
        "chown", "-R", "1044:1045", str(target_path)
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    try:
        subprocess.run(cmd, check=True, capture_output=False)
        print()
        print("✓ Ownership changed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Error changing ownership: {e}")
        sys.exit(1)


if __name__ == "__main__":
    fix_ownership()
