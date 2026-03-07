import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv("../.env")

df = pd.read_excel("sample.xlsx", header=2)

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

for _, row in df.head(5).iterrows():
    doc_issue_date = pd.to_datetime(row["DoC issue date"], dayfirst=True, errors="coerce")
    doc_expiry_date = pd.to_datetime(row["DoC expiry date"], dayfirst=True, errors="coerce")

    cur.execute(
        """
        insert into reports (
            vessel_imo,
            reporting_period,
            technical_efficiency,
            doc_issue_date,
            doc_expiry_date,
            verifier_number,
            verifier_name,
            verifier_nab,
            verifier_address,
            verifier_city,
            verifier_accreditation_number,
            verifier_country,
            total_fuel_consumption,
            total_co2_emissions,
            time_spent_at_sea_hours
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (vessel_imo, reporting_period) do nothing
        """,
        (
            int(row["IMO Number"]),
            int(row["Reporting Period"]),
            row["Technical efficiency"],
            doc_issue_date.date() if pd.notna(doc_issue_date) else None,
            doc_expiry_date.date() if pd.notna(doc_expiry_date) else None,
            str(row["Verifier Number"]) if pd.notna(row["Verifier Number"]) else None,
            row["Verifier Name"],
            row["Verifier NAB"],
            row["Verifier Address"],
            row["Verifier City"],
            str(row["Verifier Accreditation number"]) if pd.notna(row["Verifier Accreditation number"]) else None,
            row["Verifier Country"],
            row["Total fuel consumption [m tonnes]"],
            row["Total CO₂ emissions [m tonnes]"],
            row["Annual Total time spent at sea [hours]"],
        ),
    )

conn.commit()
cur.close()
conn.close()

print("Inserted reports")