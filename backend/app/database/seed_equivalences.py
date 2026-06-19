"""Seed the real client model-equivalence table (manufacturer -> internal).

This is the authoritative mapping the client provided (separate from the demo
placeholders in ``seed.py``). It is idempotent — it upserts by manufacturer
model — so it is safe to run repeatedly and against an already-populated
production database:

    python -m app.database.seed_equivalences

Notes on the source data:
- ``AK-160`` is stored without the stray space the client wrote ("AK- 160") so
  it matches the real supplier label.
- Several real supplier labels seen in the sample files use a different spelling
  than this mapping (``xiaodou`` vs ``XIADOU``, ``diaoyu`` vs ``DIAOYOU``,
  ``TY-D530`` vs ``TY-530``) and therefore will NOT auto-resolve until the client
  confirms they are the same product. Those are intentionally left as provided.
"""

from app.database.database import SessionLocal
from app.services.model_equivalence_service import upsert_equivalence

# Manufacturer model (as the supplier labels it) -> client's internal model.
CLIENT_MODEL_EQUIVALENCES: dict[str, str] = {
    "XIADOU": "TR 571 PLUS",
    "X3": "571",
    "DIAOYOU": "TR 571 PRO",
    "TY-530": "TR 530",
    "MC-316": "CHOPPER",
    "MC-118": "BICI CHICA",
    "AK-160": "TR-TON",
    "Q-02": "MOTOR SILLA DE RUEDAS",
}


def seed_client_model_equivalences(db=None) -> int:
    """Upsert the client mapping. Returns the number of equivalences processed."""
    own_session = db is None
    db = db or SessionLocal()
    try:
        for manufacturer_model, internal_model in CLIENT_MODEL_EQUIVALENCES.items():
            upsert_equivalence(db, manufacturer_model, internal_model)
        return len(CLIENT_MODEL_EQUIVALENCES)
    finally:
        if own_session:
            db.close()


if __name__ == "__main__":
    count = seed_client_model_equivalences()
    print(f"✓ Seeded {count} client model equivalences")
