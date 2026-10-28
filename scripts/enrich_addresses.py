import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc
import pandas as pd

SRC_ETAB = "data/raw/stocketablissement.parquet"
SRC_LEADS = "data/work/leads_final.parquet"
OUT = "data/work/leads_enriched.parquet"

COLS = [
    "siren", "nic", "siret", "etablissementSiege",
    "etatAdministratifEtablissement", "statutDiffusionEtablissement",
    "complementAdresseEtablissement", "numeroVoieEtablissement",
    "indiceRepetitionEtablissement", "typeVoieEtablissement",
    "libelleVoieEtablissement", "codePostalEtablissement",
    "libelleCommuneEtablissement", "codeCommuneEtablissement",
    "libellePaysEtrangerEtablissement", "libelleCommuneEtrangerEtablissement",
]

leads = pd.read_parquet(SRC_LEADS)
leads["siret_siege"] = leads["siret_siege"].astype(str)
wanted = leads["siret_siege"].unique().tolist()
print("leads:", len(leads), "| unique sièges:", len(wanted))

f = pq.ParquetFile(SRC_ETAB)
wanted_arr = pa.array(wanted)
frames = []
for i, batch in enumerate(f.iter_batches(batch_size=500_000, columns=COLS)):
    m1 = pc.equal(batch["etablissementSiege"], True)
    m2 = pc.equal(batch["etatAdministratifEtablissement"], "A")
    m3 = pc.equal(batch["statutDiffusionEtablissement"], "O")
    m4 = pc.is_in(batch["siret"], value_set=wanted_arr)
    mask = pc.and_(pc.and_(pc.and_(m1, m2), m3), m4)
    sel = batch.filter(mask)
    if sel.num_rows:
        frames.append(sel.to_pandas())
    del batch, mask, sel

etab = pd.concat(frames, ignore_index=True)
print("matched sièges:", len(etab))

etab = etab.rename(columns={
    "complementAdresseEtablissement": "adr_complement",
    "numeroVoieEtablissement": "adr_numero",
    "indiceRepetitionEtablissement": "adr_repetition",
    "typeVoieEtablissement": "adr_type_voie",
    "libelleVoieEtablissement": "adr_voie",
    "codePostalEtablissement": "adr_cp",
    "libelleCommuneEtablissement": "adr_commune",
    "codeCommuneEtablissement": "adr_code_commune",
    "libellePaysEtrangerEtablissement": "adr_pays",
    "libelleCommuneEtrangerEtablissement": "adr_commune_etranger",
})

def build_address(r):
    parts = []
    num = str(r["adr_numero"]) if pd.notna(r["adr_numero"]) else ""
    rep = str(r["adr_repetition"]) if pd.notna(r["adr_repetition"]) else ""
    if num:
        parts.append(num + rep)
    for c in ["adr_complement", "adr_type_voie", "adr_voie"]:
        v = r[c]
        if pd.notna(v) and str(v).strip():
            parts.append(str(v).strip())
    ville = r["adr_commune"] if pd.notna(r["adr_commune"]) else (r["adr_commune_etranger"] if pd.notna(r["adr_commune_etranger"]) else "")
    cp = r["adr_cp"] if pd.notna(r["adr_cp"]) else ""
    loc = f"{cp} {ville}".strip()
    if loc:
        parts.append(loc)
    return ", ".join(p for p in parts if p)

etab["adresse"] = etab.apply(build_address, axis=1)

etab_small = etab[["siret", "adresse", "adr_cp", "adr_commune", "adr_code_commune", "adr_pays"]].copy()
etab_small.columns = ["siret", "adresse", "cp", "commune", "code_commune", "pays"]

enriched = leads.merge(etab_small, left_on="siret_siege", right_on="siret", how="left")
enriched = enriched.drop(columns=["siret"])
enriched["departement"] = enriched["code_commune"].str[:2].where(enriched["code_commune"].notna())
enriched.to_parquet(OUT, index=False)
print("enriched rows:", len(enriched), "| with address:", int(enriched["adresse"].notna().sum()))