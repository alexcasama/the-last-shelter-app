import os
import shutil
from pathlib import Path

# Paths
source_dir = Path(__file__).parent / "projects"
dest_dir = Path("/app/data/projects")

print("Checking data volume migration...")
if dest_dir.exists() and len(list(dest_dir.glob("*"))) > 0:
    print("Data already exists in volume. Skipping migration.")
else:
    print(f"Migrating projects from {source_dir} to {dest_dir}...")
    try:
        shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
        print("Migration complete!")
    except Exception as e:
        print(f"Migration failed: {e}")
