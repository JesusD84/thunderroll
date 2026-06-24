"""Seed the real client model-equivalence table (manufacturer -> internal).

This is the authoritative mapping the client provided (separate from the demo
placeholders in ``seed.py``). It is idempotent — it upserts by manufacturer
model — so it is safe to run repeatedly and against an already-populated
production database:

    python -m app.database.seed_equivalences

Notes on the source data (all confirmed with the client, jun-2026):
- ``AK-160`` is stored without the stray space the client wrote ("AK- 160") so
  it matches the real supplier label.
- ``xiaodou`` and ``diaoyu`` use the spelling the suppliers actually ship in the
  sample files (the client wrote them "XIADOU"/"DIAOYOU"); we trust the samples
  since that is the data received directly from the supplier.
- ``TY-D530`` (sample spelling) -> ``TR 530``: the client confirmed it is the
  same product as the "TY-530" in their original table.
- ``MC-316`` / ``MC-118`` / ``Q-02`` are real internal models; on that occasion
  the supplier did not send chassis/motor numbers (the units were registered with
  the client's own internal numbers), so they may not appear in a supplier file,
  but the equivalence is kept as authoritative.
- ``TY-TJ571`` and ``ZHAIBANG`` are intentionally NOT mapped: the client said
  they are not needed (those files were only reference samples).
"""

from app.database.database import SessionLocal
from app.services.model_equivalence_service import upsert_equivalence

# Manufacturer model (as the supplier labels it in the sample files) -> client's
# internal model. Keys follow the supplier's real spelling so imports auto-resolve.
CLIENT_MODEL_EQUIVALENCES: dict[str, str] = {
    "xiaodou": "TR 571 PLUS",
    "X3": "571",
    "diaoyu": "TR 571 PRO",
    "TY-D530": "TR 530",
    "AK-160": "TR-TON",
    "MC-316": "CHOPPER",
    "MC-118": "BICI CHICA",
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
