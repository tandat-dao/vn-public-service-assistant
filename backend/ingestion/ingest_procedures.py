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


# ---------------------------------------------------------------------------
# Civil Registration (hộ tịch) domain
# ---------------------------------------------------------------------------

# --- Civil Registration (hộ tịch) domain ---
# Ministry: Bộ Tư pháp
# Enforcing authority: UBND phường (cấp xã)
# Primary law: Luật Hộ tịch 2014 (60/2014/QH13)
CATEGORY_HOT_TICH = {
    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "ho-tich")),
    "name": "Hộ tịch",
    "name_slug": "ho-tich",
    "ministry": "Bộ Tư pháp",
}

# --- Adoption (nuôi con nuôi) domain ---
# Ministry: Bộ Tư pháp
# Enforcing authority: UBND phường (cấp xã)
# Primary law: Luật Nuôi con nuôi 2010 (52/2010/QH12)
CATEGORY_NUOI_CON_NUOI = {
    "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "nuoi-con-nuoi")),
    "name": "Nuôi con nuôi",
    "name_slug": "nuoi-con-nuoi",
    "ministry": "Bộ Tư pháp",
}

NEW_PROCEDURES: list[dict] = [
    # Civil Registration procedures
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-CR-001")),
        "category_id": CATEGORY_HOT_TICH["id"],
        "code": "TTHC-CR-001",
        "name": "Đăng ký khai sinh",
        "domain": "civil_registration",
        "description": (
            "Đăng ký khai sinh cho trẻ em tại UBND cấp xã "
            "nơi cư trú của cha hoặc mẹ."
        ),
        "legal_basis": [
            "Luật Hộ tịch số 60/2014/QH13",
            "Nghị định 123/2015/NĐ-CP hướng dẫn Luật Hộ tịch",
            "Thông tư 15/2015/TT-BTP hướng dẫn thi hành Luật Hộ tịch",
        ],
        "processing_time_days": 3,
        "fee_vnd": 0,
        "competent_authority": "UBND cấp xã",
        "is_online": False,
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-CR-002")),
        "category_id": CATEGORY_HOT_TICH["id"],
        "code": "TTHC-CR-002",
        "name": "Cấp bản sao Trích lục hộ tịch",
        "domain": "civil_registration",
        "description": (
            "Cấp bản sao trích lục hộ tịch về sự kiện khai "
            "sinh đã đăng ký tại cơ quan quản lý cơ sở dữ "
            "liệu hộ tịch."
        ),
        "legal_basis": [
            "Luật Hộ tịch số 60/2014/QH13",
            "Nghị định 123/2015/NĐ-CP hướng dẫn Luật Hộ tịch",
        ],
        "processing_time_days": 1,
        "fee_vnd": 0,
        "competent_authority": "UBND cấp xã hoặc cấp huyện",
        "is_online": False,
    },
    # Adoption procedures
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-AD-001")),
        "category_id": CATEGORY_NUOI_CON_NUOI["id"],
        "code": "TTHC-AD-001",
        "name": "Đăng ký việc nuôi con nuôi trong nước",
        "domain": "adoption",
        "description": (
            "Đăng ký việc nuôi con nuôi trong nước tại UBND "
            "cấp xã nơi thường trú của người được giới thiệu "
            "làm con nuôi hoặc của người nhận con nuôi."
        ),
        "legal_basis": [
            "Luật Nuôi con nuôi số 52/2010/QH12",
            "Nghị định 19/2011/NĐ-CP hướng dẫn Luật Nuôi con nuôi",
            "Nghị định 24/2019/NĐ-CP sửa đổi Nghị định 19/2011",
        ],
        "processing_time_days": 30,
        "fee_vnd": 0,
        "competent_authority": "UBND cấp xã",
        "is_online": False,
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-AD-002")),
        "category_id": CATEGORY_NUOI_CON_NUOI["id"],
        "code": "TTHC-AD-002",
        "name": "Đăng ký lại việc nuôi con nuôi trong nước",
        "domain": "adoption",
        "description": (
            "Đăng ký lại việc nuôi con nuôi trong nước trong "
            "trường hợp Sổ hộ tịch và bản chính giấy tờ hộ "
            "tịch đều bị mất."
        ),
        "legal_basis": [
            "Luật Nuôi con nuôi số 52/2010/QH12",
            "Nghị định 19/2011/NĐ-CP hướng dẫn Luật Nuôi con nuôi",
            "Điều 29 Nghị định 19/2011/NĐ-CP về đăng ký lại việc nuôi con nuôi",
        ],
        "processing_time_days": 10,
        "fee_vnd": 0,
        "competent_authority": "UBND cấp xã",
        "is_online": False,
    },
]

# Dependency edges for new domains.
# TTHC-CR-002 requires TTHC-CR-001:
#   Legal basis: Điều 63-64 Luật Hộ tịch 2014 — a copy of a birth record can
#   only be issued after the original birth event has been registered.
# TTHC-AD-002 requires TTHC-AD-001:
#   Legal basis: Điều 24 Nghị định 123/2015/NĐ-CP — re-registration only
#   applies when the original adoption was previously registered and all
#   original records have been lost.
NEW_DEPENDENCIES: list[dict] = [
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "dep-cr-002-requires-cr-001")),
        "procedure_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-CR-002")),
        "depends_on_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-CR-001")),
        "is_mandatory": True,
        "condition": None,
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "dep-ad-002-requires-ad-001")),
        "procedure_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-AD-002")),
        "depends_on_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "TTHC-AD-001")),
        "is_mandatory": True,
        "condition": None,
    },
]


def seed_new_procedures() -> None:
    """Seed civil_registration and adoption procedures into PostgreSQL.

    Idempotent: uses ON CONFLICT DO NOTHING so it is safe to run multiple times.
    Requires that Alembic migration 0003 (domain column) has been applied.
    """
    conn_url = settings.POSTGRES_URL.replace("postgresql+asyncpg", "postgresql")
    conn = psycopg2.connect(conn_url)
    cur = conn.cursor()

    # 1. New categories
    for cat in [CATEGORY_HOT_TICH, CATEGORY_NUOI_CON_NUOI]:
        cur.execute(
            """
            INSERT INTO procedure_categories (id, name, name_slug, ministry)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name_slug) DO NOTHING
            """,
            (cat["id"], cat["name"], cat["name_slug"], cat["ministry"]),
        )
        print(f"  Category '{cat['name']}': inserted or already exists.")

    # 2. New procedures (includes domain column — requires migration 0003)
    for p in NEW_PROCEDURES:
        cur.execute(
            """
            INSERT INTO procedures
              (id, category_id, code, name, description,
               legal_basis, processing_time_days, fee_vnd,
               competent_authority, is_online, domain)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
            """,
            (
                p["id"],
                p["category_id"],
                p["code"],
                p["name"],
                p["description"],
                p["legal_basis"],
                p["processing_time_days"],
                p["fee_vnd"],
                p["competent_authority"],
                p["is_online"],
                p["domain"],
            ),
        )
        print(f"  Procedure '{p['code']} — {p['name']}': inserted or already exists.")

    # 3. New dependency edges
    for dep in NEW_DEPENDENCIES:
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
    print()
    print("Seeding new domain procedures (civil_registration + adoption)...")
    seed_new_procedures()
    print("Done. 2 categories + 4 procedures + 2 dependency edges seeded.")
