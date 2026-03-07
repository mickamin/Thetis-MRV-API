import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv("../.env")

header_rows = pd.read_excel("sample.xlsx", header=None, nrows=3)

groups = header_rows.iloc[0].ffill()
fields = header_rows.iloc[2]

columns = []
seen = {}

for group, field in zip(groups, fields):
    group_clean = str(group).strip().lower().replace(" ", "_")
    field_clean = (
        str(field).strip().lower()
        .replace(" ", "_")
        .replace("₂", "2")
    )

    col = f"{group_clean}__{field_clean}"

    if col in seen:
        seen[col] += 1
        col = f"{col}_{seen[col]}"
    else:
        seen[col] = 0

    columns.append(col)

df = pd.read_excel("sample.xlsx", header=None, skiprows=3)
df.columns = columns

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

for _, row in df.head(50).iterrows():
    imo_number = int(row["ship__imo_number"])
    reporting_period = int(row["ship__reporting_period"])

    doc_issue_date = pd.to_datetime(
        row["doc__doc_issue_date"], dayfirst=True, errors="coerce"
    )
    doc_expiry_date = pd.to_datetime(
        row["doc__doc_expiry_date"], dayfirst=True, errors="coerce"
    )

    cur.execute(
        """
        insert into ship (
            imo_number,
            reporting_period,
            name,
            ship_type,
            technical_efficiency,
            port_of_registry,
            home_port,
            ice_class
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (imo_number, reporting_period) do nothing
        """,
        (
            imo_number,
            reporting_period,
            row["ship__name"],
            row["ship__ship_type"],
            row["ship__technical_efficiency"],
            row["ship__port_of_registry"],
            row["ship__home_port"],
            row["ship__ice_class"],
        ),
    )

    cur.execute(
        """
        insert into doc (
            imo_number,
            reporting_period,
            doc_issue_date,
            doc_expiry_date
        )
        values (%s, %s, %s, %s)
            on conflict (imo_number, reporting_period) do nothing
        """,
        (
            imo_number,
            reporting_period,
            doc_issue_date.date() if pd.notna(doc_issue_date) else None,
            doc_expiry_date.date() if pd.notna(doc_expiry_date) else None,
        ),
    )

    cur.execute(
        """
        insert into verifier (
            imo_number,
            reporting_period,
            verifier_number,
            verifier_name,
            verifier_nab,
            verifier_address,
            verifier_city,
            verifier_accreditation_number,
            verifier_country
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (imo_number, reporting_period) do nothing
        """,
        (
            imo_number,
            reporting_period,
            str(row["verifier__verifier_number"]) if pd.notna(row["verifier__verifier_number"]) else None,
            row["verifier__verifier_name"],
            row["verifier__verifier_nab"],
            row["verifier__verifier_address"],
            row["verifier__verifier_city"],
            str(row["verifier__verifier_accreditation_number"]) if pd.notna(row["verifier__verifier_accreditation_number"]) else None,
            row["verifier__verifier_country"],
        ),
    )

conn.commit()
cur.close()
conn.close()

print("Inserted ship, doc and verifier rows")