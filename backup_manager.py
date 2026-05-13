import os
import shutil
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKUP_DIR = "backups"

def create_backup(db_url):
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = f"{BACKUP_DIR}/backup_{timestamp}.sqlite"

    # CASE 1: SQLite backup (simple copy)
    if "sqlite" in db_url:
        db_path = db_url.replace("sqlite:///", "")
        shutil.copy(db_path, backup_file)
        return backup_file

    # CASE 2: PostgreSQL backup (Render)
    else:
        return backup_postgres(db_url, backup_file)


def backup_postgres(db_url, output_file):
    """
    Dumps PostgreSQL using pg_dump
    (works on Render if pg_dump is available)
    """
    try:
        import subprocess

        cmd = f'pg_dump "{db_url}" > {output_file}'
        subprocess.run(cmd, shell=True, check=True)

        return output_file

    except Exception as e:
        print("Backup failed:", e)
        return None