import pyarrow.parquet as pq
import pyarrow.compute as pc

CURRENT_YEAR = 2026
RAW = "data/raw/stockunitelegale.parquet"
OUT = "data/work/unites_active.parquet"

COLS = [
    "siren", "statutDiffusionUniteLegale", "unitePurgeeUniteLegale",
    "dateCreationUniteLegale", "sigleUniteLegale",
    "prenom1UniteLegale", "nomUniteLegale", "nomUsageUniteLegale",
    "denominationUniteLegale", "denominationUsuelle1UniteLegale",
    "categorieJuridiqueUniteLegale", "activitePrincipaleUniteLegale",
    "nicSiegeUniteLegale", "trancheEffectifsUniteLegale",
    "anneeEffectifsUniteLegale", "caractereEmployeurUniteLegale",
    "categorieEntreprise", "economieSocialeSolidaireUniteLegale",
    "etatAdministratifUniteLegale",
]

f = pq.ParquetFile(RAW)
t = f.read(columns=COLS)
m = pc.and_(
    pc.and_(pc.equal(t["etatAdministratifUniteLegale"], "A"),
            pc.equal(t["statutDiffusionUniteLegale"], "O")),
    pc.fill_null(pc.not_equal(t["unitePurgeeUniteLegale"], True), True),
)
t = t.filter(m)
pq.write_table(t, OUT, compression="zstd", compression_level=3)
print("rows:", t.num_rows, "->", OUT)