#!/usr/bin/env python3
import json
import subprocess
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import yaml

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from pipeline_integration.p2_fill_metadata import fill_metadata
from pipeline_integration.p3_prepare_for_storage import prepare_for_storage
from pipeline_integration.p4_push_metadatas import push_metadatas
from pipeline_integration.p5_move_to_reconstructions import move_to_reconstructions
from paths import TOOLS_PATH


DOCKER_COMPOSE_DIR = TOOLS_PATH / "docker" 
PIPELINE_SCRIPTS_DIR = TOOLS_PATH / "pipeline_integration"
LOGS_DIR = TOOLS_PATH / "logs"

STEPS = ["1_move", "2_metadata", "3_storage", "4_firestore", "5_recon"]


def load_keys_from_config(config_path: str) -> List[str]:
    """Load all keys from the config file."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return list(config.get("keys", []))


def print_status_table(keys: List[str], status: Dict[str, Dict[str, str]], reprint: bool = False) -> None:
    """Print the status table. If reprint=True, moves cursor up to overwrite previous table."""
    if not keys:
        return

    # Calculate column widths
    key_width = max(len(k) for k in keys)
    step_width = max(len(s) for s in STEPS)

    # Header
    header = f"{'Key':<{key_width}} | " + " | ".join(f"{s:^{step_width}}" for s in STEPS)
    separator = "-" * len(header)

    # Number of lines: separator + header + separator + rows + separator = 4 + len(keys)
    num_lines = 4 + len(keys)

    # If reprinting, move cursor up to overwrite previous table
    if reprint:
        print(f"\033[{num_lines}A", end="")

    print(separator)
    print(header)
    print(separator)

    # Rows
    for key in keys:
        row = f"{key:<{key_width}} | "
        row += " | ".join(f"{status[key].get(step, '-'):^{step_width}}" for step in STEPS)
        print(row)

    print(separator)


def run_in_docker(script_name: str, args: list[str], log_file: Path = None) -> int:
    """
    Run a pipeline script inside the from_others docker container.

    Args:
        script_name: Name of the script in pipeline_integration folder
        args: Arguments to pass to the script
        log_file: If provided, redirect stdout/stderr to this file

    Returns:
        Exit code from the docker command
    """
    script_path = PIPELINE_SCRIPTS_DIR / script_name

    docker_cmd = [
        "docker", "compose",
        "-f", str(DOCKER_COMPOSE_DIR / "compose.yml"),
        "run", "--rm",
        "from_others",
        "python", str(script_path),
        *args
    ]

    if log_file:
        with open(log_file, "w") as f:
            result = subprocess.run(docker_cmd, stdout=f, stderr=subprocess.STDOUT)
    else:
        result = subprocess.run(docker_cmd)
    return result.returncode


def update_status(status: Dict[str, Dict[str, str]], keys: List[str], 
                  step: str, successful_keys: List[str]) -> None:
    """Update status table for a step."""
    successful_set = set(successful_keys)
    for key in keys:
        if key in successful_set:
            status[key][step] = "g"
        else:
            status[key][step] = "x"


def integrate_to_pipeline(author: str, config: str, week: str, start_step: int = 1) -> None:
    """
    Run the full pipeline integration for an author.

    Args:
        author: The author name whose files to process
        config: Path to the YAML config file
        week: Week value to set in metadata (e.g., week_1)
        start_step: Step number to start from (1-5)
    """
    # Convert config to absolute path
    config = str(Path(config).resolve())

    # Create timestamped log folder
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_folder = LOGS_DIR / timestamp
    log_folder.mkdir(parents=True, exist_ok=True)

    # Load all keys from config
    all_keys = load_keys_from_config(config)

    # Initialize status table with '-' for all keys/steps, '~' for skipped steps
    status: Dict[str, Dict[str, str]] = {}
    for key in all_keys:
        status[key] = {}
        for i, step in enumerate(STEPS, 1):
            status[key][step] = "~" if i < start_step else "-"

    print(f"\n{'='*60}")
    print(f"Starting pipeline integration for author: {author}")
    print(f"Config: {config}")
    print(f"Week: {week}")
    print(f"Logs: {log_folder}")
    print(f"Keys: {len(all_keys)}")
    if start_step > 1:
        print(f"Starting from step: {start_step}")
    print(f"{'='*60}")

    # Show initial status
    print_status_table(all_keys, status, reprint=False)

    # Step 1: Move files to esteban/outputs
    if start_step <= 1:
        step1_log = log_folder / "p1_move_to_esteban.log"
        step1_json = log_folder / "p1_move_to_esteban.json"
        exit_code = run_in_docker("p1_move_to_esteban.py", [
            "--author", author,
            "--config", config,
            "--output-json", str(step1_json),
        ], log_file=step1_log)

        # Read successful keys from JSON output
        step1_successful = []
        if step1_json.exists():
            with open(step1_json, "r") as f:
                step1_successful = json.load(f)

        update_status(status, all_keys, "1_move", step1_successful)
        print_status_table(all_keys, status, reprint=True)

        if exit_code != 0:
            print(f"\nStep 1 failed with exit code {exit_code}. Check {step1_log} for details.")
            sys.exit(exit_code)

    # Step 2: Fill metadata (author, status=pending, week)
    if start_step <= 2:
        step2_log = log_folder / "p2_fill_metadata.log"
        step2_successful = fill_metadata(config, author, week, log_file=str(step2_log))

        update_status(status, all_keys, "2_metadata", step2_successful)
        print_status_table(all_keys, status, reprint=True)

    # Step 3: Prepare for storage (prune and consolidate files)
    if start_step <= 3:
        step3_log = log_folder / "p3_prepare_for_storage.log"
        step3_successful = prepare_for_storage(config, log_file=str(step3_log))

        update_status(status, all_keys, "3_storage", step3_successful)
        print_status_table(all_keys, status, reprint=True)

    # Step 4: Push metadata to Firestore
    if start_step <= 4:
        step4_log = log_folder / "p4_push_metadatas.log"
        step4_successful = push_metadatas(config, log_file=str(step4_log))

        update_status(status, all_keys, "4_firestore", step4_successful)
        print_status_table(all_keys, status, reprint=True)

    # Step 5: Move to reconstructions (organized by week/author)
    if start_step <= 5:
        step5_log = log_folder / "p5_move_to_reconstructions.log"
        step5_successful = move_to_reconstructions(config, log_file=str(step5_log))

        update_status(status, all_keys, "5_recon", step5_successful)
        print_status_table(all_keys, status, reprint=True)

    print(f"\n✓ Pipeline integration completed!")
    print(f"  Logs saved to: {log_folder}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Integrate files from an author into the pipeline"
    )
    parser.add_argument(
        "--author",
        "-a",
        required=True,
        help="The author name whose files to integrate"
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to the YAML config file"
    )
    parser.add_argument(
        "--week",
        "-w",
        required=True,
        help="Week value to set in metadata (e.g., week_1)"
    )
    parser.add_argument(
        "--step",
        "-s",
        type=int,
        default=1,
        choices=[1, 2, 3, 4, 5],
        help="Step to start from (1=move, 2=metadata, 3=storage, 4=firestore, 5=recon). Default: 1"
    )

    args = parser.parse_args()
    integrate_to_pipeline(args.author, args.config, args.week, args.step)
