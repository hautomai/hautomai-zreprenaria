import pandas as pd
import sqlite3

SRC = "data/work/leads_enriched.parquet"
DB = "data/leads.db"
CSV_ALL = "data/leads_all.csv.gz"
CSV_TOP = "data/leads_top200k.csv"

catjur_labels = {
    1000: "Entrepreneur individuel",
    2100: "Entreprise individuelle agricole",
    2110: "EARL",
    2210: "Exploitation agricole à responsabilité limitée",
    3110: "GIE",
    3120: "SICA",
    5202: "SNC",
    5410: "SA à conseil d'administration",
    5420: "SA à directoire",
    5485: "SELARL",
    5498: "EURL / SARL unipersonnelle",
    5499: "SARL",
    5710: "SAS",
    5720: "SASU",
    5599: "SA",
    6533: "GAEC",
    6534: "GFA",
    6540: "SCI",
    6561: "SCP d'avocats",
    6571: "SCP de médecins",
    9220: "Association déclarée",
}

df = pd.read_parquet(SRC)
df["denom"] = df["denom"].fillna(df["siren"])

def legal_label(code):
    return catjur_labels.get(int(code), f"Catégorie {code}")

df["forme_juridique"] = df["categorieJuridiqueUniteLegale"].map(legal_label)

eff_labels = {
    "00": "0 salarié", "01": "1-2", "02": "3-5", "03": "6-9",
    "11": "10-19", "12": "20-49", "21": "50-99", "NN": "Non renseigné",
}
df["effectifs"] = df["trancheEffectifsUniteLegale"].map(lambda x: eff_labels.get(x, x))

def reason(r):
    parts = [f"firme âgée de {int(r['firm_age'])} ans (créée {int(r['creation_year'])})"]
    if r["is_ei"]:
        parts.append("entreprise individuelle — un seul dirigeant")
    if r["is_eurl_sasu"]:
        parts.append("EURL/SASU — associé unique")
    if r["is_sarl_sas"]:
        parts.append("SARL/SAS — forme familiale courante")
    return " ; ".join(parts)

df["lead_reason"] = df.apply(reason, axis=1)

out_cols = [
    "siren", "denom", "forme_juridique", "lead_tier", "score_total",
    "est_owner_age", "firm_age", "creation_year",
    "activitePrincipaleUniteLegale", "naf_section", "naf_section_label",
    "effectifs", "adresse", "cp", "commune", "departement", "pays",
    "siret_siege", "lead_reason", "score_age", "score_keyman", "score_size",
]
export = df[out_cols].copy()
export = export.rename(columns={
    "denom": "nom_entreprise",
    "lead_tier": "tier",
    "score_total": "score_risque_transmission",
    "est_owner_age": "age_estime_fondateur",
    "firm_age": "age_entreprise",
    "creation_year": "annee_creation",
    "activitePrincipaleUniteLegale": "ape",
    "naf_section_label": "secteur",
})

export = export.sort_values("score_risque_transmission", ascending=False)

con = sqlite3.connect(DB)
export.to_sql("leads", con, if_exists="replace", index=False)
con.execute("CREATE INDEX IF NOT EXISTS idx_tier ON leads(tier)")
con.execute("CREATE INDEX IF NOT EXISTS idx_dep ON leads(departement)")
con.execute("CREATE INDEX IF NOT EXISTS idx_ape ON leads(ape)")
con.commit()
n = con.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
print("SQLite rows:", n)
con.close()

export.to_csv(CSV_ALL, index=False, compression="gzip")
export.head(200_000).to_csv(CSV_TOP, index=False)
print("wrote", CSV_ALL, "and", CSV_TOP)

sub = export.head(15)
print(sub[
    ["siren", "nom_entreprise", "forme_juridique", "tier",
     "score_risque_transmission", "age_estime_fondateur", "age_entreprise",
     "ape", "secteur", "commune", "departement"]
].to_string())