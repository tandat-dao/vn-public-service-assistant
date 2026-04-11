"""Seed script — insert Ho Chi Minh City administrative units.

Populates the minimum ward codes needed for housing domain test cases.
Scope codes used in Qdrant payloads are constructed as: VN-HCM-{code}

Run from the backend/ directory:
    PYTHONPATH=. .venv/Scripts/python ingestion/seed_administrative_units.py

Idempotent — uses ON CONFLICT DO NOTHING, safe to run multiple times.
"""

import psycopg2

from app.config import settings

# Official Ministry of Home Affairs administrative unit codes for Ho Chi Minh City.
# Scope code for ward-level documents: VN-HCM-{code}
SEED_DATA = [
    # Ho Chi Minh City (province level)
    {
        "code": "79",
        "name": "Thành phố Hồ Chí Minh",
        "administrative_level": "province",
        "parent_code": None,
    },
    # District 1
    {
        "code": "760",
        "name": "Quận 1",
        "administrative_level": "district",
        "parent_code": "79",
    },
    # District 3
    {
        "code": "770",
        "name": "Quận 3",
        "administrative_level": "district",
        "parent_code": "79",
    },
    # Tân Bình District
    {
        "code": "761",
        "name": "Quận Tân Bình",
        "administrative_level": "district",
        "parent_code": "79",
    },
    # Ward Bến Nghé (District 1) → scope VN-HCM-26734
    {
        "code": "26734",
        "name": "Phường Bến Nghé",
        "administrative_level": "ward",
        "parent_code": "760",
    },
    # Ward Bến Thành (District 1) → scope VN-HCM-26737
    {
        "code": "26737",
        "name": "Phường Bến Thành",
        "administrative_level": "ward",
        "parent_code": "760",
    },
    # Ward 1 (District 3) → scope VN-HCM-27100
    {
        "code": "27100",
        "name": "Phường 1",
        "administrative_level": "ward",
        "parent_code": "770",
    },
    # Ward Tân Hòa (Tân Bình) → scope VN-HCM-26968
    {
        "code": "26968",
        "name": "Phường Tân Hòa",
        "administrative_level": "ward",
        "parent_code": "761",
    },
]


def seed_administrative_units() -> None:
    conn_url = settings.POSTGRES_URL.replace("postgresql+asyncpg", "postgresql")
    conn = psycopg2.connect(conn_url)
    cur = conn.cursor()

    inserted = 0
    for row in SEED_DATA:
        cur.execute(
            """
            INSERT INTO administrative_units
              (code, name, administrative_level, parent_code)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
            """,
            (row["code"], row["name"], row["administrative_level"], row["parent_code"]),
        )
        if cur.rowcount:
            inserted += 1
            print(f"  Inserted: {row['code']} — {row['name']} ({row['administrative_level']})")
        else:
            print(f"  Skipped (already exists): {row['code']} — {row['name']}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nDone. {inserted} new rows inserted, {len(SEED_DATA) - inserted} already existed.")


if __name__ == "__main__":
    print("Seeding administrative units (Ho Chi Minh City)...")
    seed_administrative_units()
