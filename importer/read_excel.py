import pandas as pd

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

print(df.head())
print(df.columns.tolist())