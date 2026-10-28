import pandas as pd

SRC = "data/work/leads_unfiltered.parquet"
OUT = "data/work/leads_final.parquet"

df = pd.read_parquet(SRC)

df["is_ess"] = df["economieSocialeSolidaireUniteLegale"] == "O"

keep = (
    ~df["naf_excluded"]
    & ~df["is_sci"]
    & ~df["effectif_excluded"]
    & ~df["is_scop"]
    & ~df["is_ess"]
    & df["trancheEffectifsUniteLegale"].isin(["12", "21"])
    & df["lead_tier"].isin(["GOLD", "HIGH", "MEDIUM"])
)
final = df[keep].copy()

final["denom"] = final["denominationUniteLegale"].fillna("")
mask = final["denom"] == ""
final.loc[mask, "denom"] = final.loc[mask, "nomUsageUniteLegale"].fillna("")
mask2 = final["denom"] == ""
final.loc[mask2, "denom"] = final.loc[mask2, "nomUniteLegale"].fillna("")
final.loc[final["denom"] == "", "denom"] = final["siren"]

final["siret_siege"] = final["siren"].astype(str) + final["nicSiegeUniteLegale"].fillna("")

cols = [
    "siren", "siret_siege", "denom", "sigleUniteLegale",
    "categorieJuridiqueUniteLegale", "catjur_family",
    "activitePrincipaleUniteLegale", "naf_section", "naf_section_label",
    "firm_age", "creation_year", "est_owner_age_lb", "est_owner_age",
    "trancheEffectifsUniteLegale", "caractereEmployeurUniteLegale",
    "categorieEntreprise", "is_ei", "is_eurl_sasu", "is_sarl_sas",
    "lead_tier", "score_age", "score_keyman", "score_size", "score_total",
]
final = final[cols].copy()
final = final.sort_values("score_total", ascending=False)

final.to_parquet(OUT, index=False)
print("final leads:", len(final))
for t, g in final.groupby("lead_tier"):
    print(f"{t}: {len(g)}")
print("\nsample head:")
print(final.head(5).to_string())