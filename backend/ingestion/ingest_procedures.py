"""Ingestion script — seed procedure and dependency data into PostgreSQL.

Run from the backend/ directory:
    PYTHONPATH=. .venv/Scripts/python ingestion/ingest_procedures.py

Idempotent: uses ON CONFLICT DO NOTHING so it is safe to run multiple times.
"""

import uuid

import psycopg2

from app.config import settings

# ---------------------------------------------------------------------------
# Seed data — matches actual migration schema (0001_initial_schema.py)
# ---------------------------------------------------------------------------

CATEGORY = {
    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "cu-tru")),
    "name": "Cư trú",
    "name_slug": "cu-tru",
    "ministry": "Bộ Công an",
}

PROCEDURES = [
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-001")),
        "category_id": CATEGORY["id"],
        "code": "TTHC-001",
        "name": "Đăng ký thường trú",
        "description": (
            "Thủ tục đăng ký thường trú cho công dân muốn đăng ký nơi thường trú "
            "mới tại địa chỉ hợp pháp theo quy định của Luật Cư trú 2020."
        ),
        "legal_basis": [
            "Luật Cư trú số 68/2020/QH14",
            "Nghị định 62/2021/NĐ-CP hướng dẫn Luật Cư trú",
        ],
        "processing_time_days": 5,
        "fee_vnd": 0,
        "competent_authority": "Công an xã, phường, thị trấn",
        "is_online": True,
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-002")),
        "category_id": CATEGORY["id"],
        "code": "TTHC-002",
        "name": "Đăng ký tạm trú",
        "description": (
            "Thủ tục đăng ký tạm trú cho công dân lưu trú tại nơi không phải "
            "nơi thường trú từ 30 ngày trở lên theo Luật Cư trú 2020."
        ),
        "legal_basis": [
            "Luật Cư trú số 68/2020/QH14",
            "Nghị định 62/2021/NĐ-CP hướng dẫn Luật Cư trú",
        ],
        "processing_time_days": 3,
        "fee_vnd": 0,
        "competent_authority": "Công an xã, phường, thị trấn",
        "is_online": True,
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-003")),
        "category_id": CATEGORY["id"],
        "code": "TTHC-003",
        "name": "Xác nhận thông tin về cư trú",
        "description": (
            "Thủ tục xác nhận thông tin cư trú (thường trú hoặc tạm trú) "
            "để phục vụ các mục đích hành chính, pháp lý theo yêu cầu của công dân."
        ),
        "legal_basis": [
            "Luật Cư trú số 68/2020/QH14",
            "Nghị định 62/2021/NĐ-CP hướng dẫn Luật Cư trú",
        ],
        "processing_time_days": 2,
        "fee_vnd": 0,
        "competent_authority": "Công an xã, phường, thị trấn",
        "is_online": True,
    },
]

# Dependency edges for the topological sort.
# TTHC-003 (xac_nhan_cu_tru) requires proof of an existing registration:
#   Edge 1 — mandatory:  TTHC-003 depends on TTHC-001 (thường trú)
#   Edge 2 — conditional: TTHC-003 depends on TTHC-002 (tạm trú), only if the
#             citizen is a temporary resident (makes the plan non-trivial for testing).
DEPENDENCIES: list[dict] = [
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "dep-003-requires-001")),
        "procedure_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-003")),
        "depends_on_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-001")),
        "is_mandatory": True,
        "condition": None,
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "dep-003-requires-002")),
        "procedure_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-003")),
        "depends_on_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-002")),
        "is_mandatory": False,
        "condition": "Nếu là cư dân tạm trú",
    },
]


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed_procedures() -> None:
    conn_url = settings.POSTGRES_URL.replace("postgresql+asyncpg", "postgresql")
    conn = psycopg2.connect(conn_url)
    cur = conn.cursor()

    # 1. Category
    cur.execute(
        """
        INSERT INTO procedure_categories (id, name, name_slug, ministry)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (name_slug) DO NOTHING
        """,
        (CATEGORY["id"], CATEGORY["name"], CATEGORY["name_slug"], CATEGORY["ministry"]),
    )
    print(f"  Category '{CATEGORY['name']}': inserted or already exists.")

    # 2. Procedures
    for p in PROCEDURES:
        cur.execute(
            """
            INSERT INTO procedures
              (id, category_id, code, name, description,
               legal_basis, processing_time_days, fee_vnd,
               competent_authority, is_online)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
            """,
            (
                p["id"],
                p["category_id"],
                p["code"],
                p["name"],
                p["description"],
                p["legal_basis"],          # psycopg2 maps Python list → Postgres ARRAY
                p["processing_time_days"],
                p["fee_vnd"],
                p["competent_authority"],
                p["is_online"],
            ),
        )
        print(f"  Procedure '{p['code']} — {p['name']}': inserted or already exists.")

    # 3. Dependencies (none for Phase 1 — all 3 procedures are independent)
    for dep in DEPENDENCIES:
        cur.execute(
            """
            INSERT INTO procedure_dependencies
              (id, procedure_id, depends_on_procedure_id, is_mandatory, condition_description)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (procedure_id, depends_on_procedure_id) DO NOTHING
            """,
            (dep["id"], dep["procedure_id"], dep["depends_on_id"], dep["is_mandatory"], dep.get("condition")),
        )
        print(
            f"  Dependency '{dep['procedure_id'][-8:]} → {dep['depends_on_id'][-8:]}': "
            "inserted or already exists."
        )

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    print("Seeding procedure data...")
    seed_procedures()
    print("Done. 1 category + 3 procedures seeded.")
