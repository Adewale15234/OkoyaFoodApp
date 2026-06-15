from datetime import datetime
import os

def create_backup(db_url):
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(db_url)

        conn = engine.connect()

        result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
        tables = [row[0] for row in result]

        backup_data = {}

        for table in tables:
            rows = conn.execute(text(f"SELECT * FROM {table}")).fetchall()
            backup_data[table] = [dict(row._mapping) for row in rows]

        os.makedirs("backups", exist_ok=True)

        filename = f"backups/backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"

        import json
        with open(filename, "w") as f:
            json.dump(backup_data, f, default=str, indent=2)

        return filename

    except Exception as e:
        print("Backup error:", e)
        return None