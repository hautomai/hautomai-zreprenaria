import pandas as pd

CURRENT_YEAR = 2026
SRC = "data/work/unites_active.parquet"
OUT = "data/work/leads_unfiltered.parquet"

NAF_SECTIONS = {
    "A": "Agriculture, sylviculture et pêche", "B": "Industries extractives",
    "C": "Industrie manufacturière", "D": "Prod/distrib. électricité, gaz, vapeur",
    "E": "Eau, assainissement, déchets", "F": "Construction",
    "G": "Commerce, réparation auto-moto", "H": "Transport et entreposage",
    "I": "Hébergement et restauration", "J": "Information et communication",
    "K": "Activités financières et d'assurance", "L": "Activités immobilières",
    "M": "Activités spécialisées, scientif. et techniques",
    "N": "Activités de services administratifs et de soutien",
    "O": "Administration publique", "P": "Enseignement",
    "Q": "Santé humaine et action sociale", "R": "Arts, spectacles, loisirs",
    "S": "Autres activités de services", "T": "Activités des ménages",
    "U": "Activités extraterritoriales",
}

def naf_section(nafcode):
    if not isinstance(nafcode, str) or not nafcode:
        return None
    digits = "".join(ch for ch in nafcode if ch.isdigit())
    if len(digits) < 2:
        return None
    n = int(digits[:2])
    if n <= 3: return "A"
    if n <= 9: return "B"
    if n <= 33: return "C"
    if n == 35: return "D"
    if n <= 39: return "E"
    if n <= 43: return "F"
    if n <= 47: return "G"
    if n <= 53: return "H"
    if n <= 56: return "I"
    if n <= 63: return "J"
    if n <= 66: return "K"
    if n == 68: return "L"
    if n <= 75: return "M"
    if n <= 82: return "N"
    if n == 84: return "O"
    if n == 85: return "P"
    if n <= 88: return "Q"
    if n <= 93: return "R"
    if n <= 96: return "S"
    if n <= 98: return "T"
    return "U"

EXCLUDE_CATJUR_FAMILIES = (2, 3, 4, 7, 8, 9)
SCI_CATJUR = {6539, 6540, 6541, 6542, 6535, 6536, 6537, 6538}
SCOP_CATJUR = {5460, 5558, 5658, 5858, 5130, 5140, 5458}
EURL_SASU = {5498, 5720}
SARL_SAS = {5499, 5710, 5410, 5420}
EXCLUDE_NAF_PREFIX = {"68", "84", "91", "94", "97", "98", "99"}
EXCLUDE_EFFECTIF = {"22", "31", "32", "41", "42", "51", "52", "53"}

df = pd.read_parquet(SRC)
print("read rows:", len(df))

df["catjur_family"] = df["categorieJuridiqueUniteLegale"] // 1000
df = df[~df["catjur_family"].isin(EXCLUDE_CATJUR_FAMILIES)].copy()
print("after catjur filter:", len(df))

df["creation_year"] = pd.to_datetime(df["dateCreationUniteLegale"], errors="coerce").dt.year
df = df[df["creation_year"].between(1901, 2020, inclusive="both")].copy()
df["firm_age"] = CURRENT_YEAR - df["creation_year"]

naf = df["activitePrincipaleUniteLegale"].fillna("")
df["naf_section"] = naf.map(naf_section)
df["naf_section_label"] = df["naf_section"].map(NAF_SECTIONS)
df["naf_excluded"] = naf.str[:2].isin(EXCLUDE_NAF_PREFIX)

df["is_ei"] = df["catjur_family"] == 1
df["is_sci"] = df["categorieJuridiqueUniteLegale"].isin(SCI_CATJUR)
df["is_scop"] = df["categorieJuridiqueUniteLegale"].isin(SCOP_CATJUR)
df["is_eurl_sasu"] = df["categorieJuridiqueUniteLegale"].isin(EURL_SASU)
df["is_sarl_sas"] = df["categorieJuridiqueUniteLegale"].isin(SARL_SAS)
df["effectif_excluded"] = df["trancheEffectifsUniteLegale"].isin(EXCLUDE_EFFECTIF)

df["est_owner_age_lb"] = df["firm_age"] + 18
df["est_owner_age"] = df["firm_age"] + 35

def tier(age):
    if pd.isna(age):
        return "EXCLUDED"
    if 65 <= age <= 80:
        return "GOLD"
    if (60 <= age < 65) or (80 < age <= 85):
        return "HIGH"
    if 55 <= age < 60:
        return "MEDIUM"
    return "EXCLUDED"

df["lead_tier"] = df["est_owner_age"].map(tier)

def age_score(owner_age):
    if pd.isna(owner_age):
        return 0.0
    if owner_age < 55:
        return max((owner_age - 45) * 2, 0)
    if owner_age <= 70:
        return 80 + (owner_age - 60) * 2
    if owner_age <= 80:
        return 100 - (owner_age - 70) * 1.5
    return max(85 - (owner_age - 80) * 3, 10)

df["score_age"] = df["est_owner_age"].map(age_score).round(1)

df["score_keyman"] = (
    df["is_ei"] * 10 + df["is_eurl_sasu"] * 8 + df["is_sarl_sas"] * 5
)

small_eff = df["trancheEffectifsUniteLegale"].isin({"00", "01", "02", "03"})
mid_eff = df["trancheEffectifsUniteLegale"].isin({"11", "12", "21"})
df["score_size"] = small_eff * 8 + mid_eff * 4

df["score_total"] = (
    df["score_age"] * 0.6 + df["score_keyman"] + df["score_size"] * 0.6
).round(1)

df.to_parquet(OUT, index=False)
print("leads_unfiltered rows:", len(df))

counts = df["lead_tier"].value_counts(dropna=False)
for t, c in counts.items():
    print(f"{t}: {c}")