#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from typing import Dict, List

import firebase_admin
import yaml
from firebase_admin import credentials, firestore

sys.path.insert(0, str(Path(__file__).parent.parent))
from paths import ESTEBAN_OUTPUTS

OUTPUTS_BASE = ESTEBAN_OUTPUTS
FIREBASE_PATH = Path("/data2/openreal2sim/scripts/config/firebase.json")


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


def read_metadata_yaml(metadata_path: Path) -> Dict:
    if not metadata_path.exists():
        raise FileNotFoundError(f"metadata.yaml not found at {metadata_path}")
    with open(metadata_path, "r") as f:
        metadata = yaml.safe_load(f) or {}
    if not isinstance(metadata, dict):
        raise ValueError(f"metadata.yaml must contain a mapping at {metadata_path}")
    return metadata


def write_metadata_yaml(metadata_path: Path, metadata: Dict) -> None:
    with open(metadata_path, "w") as f:
        yaml.safe_dump(
            metadata,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )


def init_firebase(creds_path: str) -> firestore.Client:
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(creds_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def push_field_if_absent(
    transaction: firestore.Transaction,
    doc_ref: firestore.DocumentReference,
    field_name: str,
    value: Dict
) -> bool:
    """Push a field to Firestore if it doesn't exist. Returns True if pushed."""
    snapshot = doc_ref.get(transaction=transaction)
    current = snapshot.to_dict() or {}
    if field_name in current:
        return False
    transaction.set(doc_ref, {field_name: value}, merge=True)
    return True


def push_metadatas(config_path: str, log_file: str = None) -> List[str]:
    """
    Push metadata.yaml contents to Firestore for all keys in config.
    After successful push, marks local metadata with synced: true.

    Args:
        config_path: Path to the YAML config file containing 'keys'
        log_file: If provided, write output to this file instead of stdout

    Returns:
        List of keys that were successfully pushed or already synced
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

        db = init_firebase(str(FIREBASE_PATH))
        doc_ref = db.collection("reconstructions").document("metadata")

        pushed_count = 0
        already_synced_count = 0
        skipped_existing_count = 0
        missing_metadata_count = 0
        errors: List[str] = []

        log(f"\nPushing metadatas to Firestore:")
        log(f"Base: {OUTPUTS_BASE}")
        log(f"Document: reconstructions/metadata")
        log(f"Keys: {keys}\n")

        for key in keys:
            key_dir = OUTPUTS_BASE / key
            metadata_path = key_dir / "metadata.yaml"

            if not key_dir.exists():
                log(f"⚠️  Key directory not found (skipping): {key_dir}")
                missing_metadata_count += 1
                continue

            if not metadata_path.exists():
                log(f"⚠️  No metadata.yaml (skipping): {metadata_path}")
                missing_metadata_count += 1
                continue

            try:
                metadata_obj = read_metadata_yaml(metadata_path)

                # Check if already synced locally
                if metadata_obj.get("synced") is True:
                    log(f"⏭️  Already synced locally (skipping): {key}")
                    already_synced_count += 1
                    successful_keys.append(key)
                    continue

                # Prepare metadata for Firestore (exclude 'synced' field)
                metadata_to_push = {k: v for k, v in metadata_obj.items() if k != "synced"}

                transaction = db.transaction()

                @firestore.transactional
                def do_push(txn: firestore.Transaction) -> bool:
                    return push_field_if_absent(txn, doc_ref, key, metadata_to_push)

                created = do_push(transaction)

                if created:
                    # Mark as synced locally
                    metadata_obj["synced"] = True
                    write_metadata_yaml(metadata_path, metadata_obj)
                    log(f"✓ Pushed and marked synced: {key}")
                    pushed_count += 1
                    successful_keys.append(key)
                else:
                    # Already exists in Firestore, mark as synced locally
                    metadata_obj["synced"] = True
                    write_metadata_yaml(metadata_path, metadata_obj)
                    log(f"⏭️  Exists in Firestore, marked synced: {key}")
                    skipped_existing_count += 1
                    successful_keys.append(key)

            except Exception as e:
                error_msg = f"✗ Error for {key}: {e}"
                log(error_msg)
                errors.append(error_msg)

        log(f"\n{'='*60}")
        log("Summary for push_metadatas")
        log(f"{'='*60}")
        log(f"Pushed new keys: {pushed_count}")
        log(f"Already synced locally: {already_synced_count}")
        log(f"Existed in Firestore (now synced): {skipped_existing_count}")
        log(f"Missing metadata: {missing_metadata_count}")
        log(f"Errors: {len(errors)}")
        if errors:
            log("\nError details:")
            for error in errors:
                log(f"  {error}")
        log(f"{'='*60}\n")

    except Exception as e:
        log(f"Error: {e}")

    return successful_keys


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Push metadata.yaml to Firestore and mark as synced locally"
    )
    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Path to the YAML config file containing 'keys'",
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
    successful = push_metadatas(args.config, args.log_file)

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(successful, f)
