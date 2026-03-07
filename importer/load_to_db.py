import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv("../.env")

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

df = pd.read_excel("sample.xlsx", header=2)

for _, row in df.head(5).iterrows():
    cur.execute(
        """
        insert into vessels (imo_number, name, ship_type)
        values (%s,%s,%s)
            on conflict (imo_number) do nothing
        """,
        (
            int(row["IMO Number"]),
            row["Name"],
            row["Ship type"],
        ),
    )

conn.commit()
cur.close()
conn.close()

print("Inserted vessels")