"""Read-only local inbox diagnostics; never read credentials or message contents."""

import datetime
import json
import sqlite3
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


def check_http(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=4) as response:
            print(f"{url}: HTTP {response.status}")
    except urllib.error.HTTPError as error:
        print(f"{url}: HTTP {error.code}")
    except (urllib.error.URLError, TimeoutError, OSError):
        print(f"{url}: unreachable")


def quoted(name):
    return '"' + name.replace('"', '""') + '"'


def inspect_database(filename):
    path = PROJECT / "backend" / "data" / filename
    print(f"\nDatabase: {filename}")
    if not path.is_file():
        print("Not present at the default project location.")
        return
    connection = None
    try:
        connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3)
        connection.execute("PRAGMA query_only=ON")
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        for (table,) in tables:
            table_sql = quoted(table)
            columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table_sql})")}
            # Restrict persistent feedback summaries to the WhatsApp source.
            where = " WHERE source = 'whatsapp'" if "source" in columns else ""
            total = connection.execute(f"SELECT COUNT(*) FROM {table_sql}{where}").fetchone()[0]
            print(f"  {table}: {total} rows" + (" (WhatsApp only)" if where else ""))
            for column in ("status", "state"):
                if column in columns:
                    values = connection.execute(
                        f"SELECT {quoted(column)}, COUNT(*) FROM {table_sql}{where} GROUP BY {quoted(column)}"
                    ).fetchall()
                    print(f"    {column}: {json.dumps(values, ensure_ascii=False)}")
            for column in ("created_at", "received_at", "updated_at", "expires_at"):
                if column in columns:
                    latest = connection.execute(
                        f"SELECT MAX({quoted(column)}) FROM {table_sql}{where}"
                    ).fetchone()[0]
                    print(f"    latest {column}: {latest}")
    except sqlite3.Error as error:
        print(f"Could not inspect database ({type(error).__name__}).")
    finally:
        if connection is not None:
            connection.close()


def main():
    print("WhatsApp local diagnostics (read-only; no tokens or message content)")
    print("UTC:", datetime.datetime.now(datetime.timezone.utc).isoformat())
    for url in (
        "http://127.0.0.1:8003/health",
        "http://127.0.0.1:8003/api/config",
        "http://127.0.0.1:5174/",
    ):
        check_http(url)
    print("API config HTTP 401 is expected here: this check sends no app token.")
    for name in ("cloudflared", "ngrok"):
        try:
            result = subprocess.run(
                ["pgrep", "-x", name], stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=4, check=False,
            )
            state = "running" if result.returncode == 0 else "not detected"
        except (OSError, subprocess.TimeoutExpired):
            state = "could not check"
        print(f"Tunnel process {name}: {state}")
    print("A tunnel process alone does not confirm Meta's callback URL or subscription.")
    inspect_database("inbox.sqlite3")
    inspect_database("voice_feedback.db")


if __name__ == "__main__":
    main()
