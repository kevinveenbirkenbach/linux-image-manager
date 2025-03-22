#!/usr/bin/env python3
import subprocess
import os
import argparse

def run_script(script_path, extra_args):
    if not os.path.exists(script_path):
        print(f"[ERROR] Script not found at {script_path}")
        exit(1)
    command = ["sudo","bash", script_path] + extra_args
    print(f"[INFO] Running command: {' '.join(command)}")
    result = subprocess.run(command)
    if result.returncode != 0:
        print(f"[ERROR] Script exited with code {result.returncode}")
        exit(result.returncode)
    print("[SUCCESS] Script executed successfully.")

def main():
    # Use os.path.realpath to get the actual path of this file regardless of symlinks
    repo_root = os.path.dirname(os.path.realpath(__file__))

    # Define available scripts along with their descriptions.
    setup_scripts = {
        "image": {
            "path": os.path.join(repo_root, "scripts", "image", "setup.sh"),
            "description": (
                "Linux Image Setup:\n"
                "  - Creates partitions and formats them.\n"
                "  - Transfers the Linux image file to the device.\n"
                "  - Configures boot and root partitions."
            )
        },
        "single": {
            "path": os.path.join(repo_root, "scripts", "encryption", "storage", "single_drive", "setup.sh"),
            "description": (
                "Single Drive Encryption Setup:\n"
                "  - Sets up disk encryption using LUKS on one drive.\n"
                "  - Configures a Btrfs file system for secure storage."
            )
        },
        "raid1": {
            "path": os.path.join(repo_root, "scripts", "encryption", "storage", "raid1", "setup.sh"),
            "description": (
                "RAID1 Encryption Setup:\n"
                "  - Configures a virtual RAID1 with two drives.\n"
                "  - Uses LUKS encryption and a Btrfs RAID1 file system for redundancy."
            )
        },
        "backup": {
            "path": os.path.join(repo_root, "scripts", "image", "backup.sh"),
            "description": (
                "Backup Image Setup:\n"
                "  - Creates an image backup from a memory device to a file.\n"
                "  - Uses dd to transfer the image from the specified device to an image file."
            )
        },
        "chroot": {
            "path": os.path.join(repo_root, "scripts", "image", "chroot.sh"),
            "description": (
                "Chroot Environment Setup:\n"
                "  - Mounts partitions and configures the chroot environment for a Linux image.\n"
                "  - Provides a shell within the Linux image for system maintenance."
            )
        }
    }

    parser = argparse.ArgumentParser(
        description="Wrapper for executing various scripts from Linux Image Manager.",
        epilog=(
            "Available script types:\n"
            "  image  - Linux Image Setup\n"
            "  single - Single Drive Encryption Setup\n"
            "  raid1  - RAID1 Encryption Setup\n"
            "  backup - Backup Image Setup\n"
            "  chroot - Chroot Environment Setup\n\n"
            "Additional Options:\n"
            "  --extra         Pass extra parameters to the selected script.\n"
            "  --auto-confirm  Bypass the confirmation prompt before execution.\n"
            "  --help          Display this help message and exit."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--type", required=True, choices=list(setup_scripts.keys()),
                        help="Select the script type to execute. Options: " + ", ".join(setup_scripts.keys()))
    parser.add_argument("--extra", nargs=argparse.REMAINDER, default=[],
                        help="Extra parameters to pass to the selected script.")
    parser.add_argument("--auto-confirm", action="store_true",
                        help="Automatically confirm execution without prompting the user.")

    args = parser.parse_args()

    script_info = setup_scripts[args.type]
    print("[INFO] Selected script type:", args.type)
    print("[INFO] Description:")
    print(script_info["description"])
    print("[INFO] Script path:", script_info["path"])
    if args.extra:
        print("[INFO] Extra parameters provided:", " ".join(args.extra))
    else:
        print("[INFO] No extra parameters provided.")

    if not args.auto_confirm:
        input("Press Enter to execute the script or Ctrl+C to cancel...")

    run_script(script_info["path"], args.extra)

if __name__ == "__main__":
    main()
