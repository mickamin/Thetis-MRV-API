import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv("../.env")


def clean_numeric(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        if value.lower() in ["n/a", "division by zero!", ""]:
            return None
    try:
        return float(value)
    except:
        return None


# ------------------------
# Parse Excel headers
# ------------------------

header_rows = pd.read_excel("sample.xlsx", header=None, nrows=3)

groups = header_rows.iloc[0].ffill()
subgroups = header_rows.iloc[1]
fields = header_rows.iloc[2]

columns = []
seen = {}

for group, subgroup, field in zip(groups, subgroups, fields):

    group_clean = str(group).strip().lower().replace(" ", "_")

    field_clean = (
        str(field).strip().lower()
        .replace(" ", "_")
        .replace("₂", "2")
    )

    if pd.isna(subgroup):
        col = f"{group_clean}__{field_clean}"
    else:
        subgroup_clean = str(subgroup).strip().lower().replace(" ", "_")
        col = f"{group_clean}__{subgroup_clean}__{field_clean}"

    if col in seen:
        seen[col] += 1
        col = f"{col}_{seen[col]}"
    else:
        seen[col] = 0

    columns.append(col)


df = pd.read_excel("sample.xlsx", header=None, skiprows=3)
df.columns = columns


# ------------------------
# DB connection
# ------------------------

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# Shorthand aliases for long column names
AMR = "annual_monitoring_results"
VR = "voluntary_reporting"


# ------------------------
# Import rows
# ------------------------

for _, row in df.iterrows():

    imo = int(row["ship__imo_number"])
    year = int(row["ship__reporting_period"])

    # ---- ship ----
    cur.execute(
        """
        insert into ship
        (imo_number, reporting_period, name, ship_type,
         technical_efficiency, port_of_registry, home_port, ice_class)
        values (%s,%s,%s,%s,%s,%s,%s,%s)
            on conflict (imo_number, reporting_period) do nothing
        """,
        (
            imo,
            year,
            row["ship__name"],
            row["ship__ship_type"],
            row["ship__technical_efficiency"],
            row["ship__port_of_registry"],
            row["ship__home_port"],
            row["ship__ice_class"],
        ),
    )

    # ---- doc ----
    issue = pd.to_datetime(row["doc__doc_issue_date"], dayfirst=True, errors="coerce")
    expiry = pd.to_datetime(row["doc__doc_expiry_date"], dayfirst=True, errors="coerce")

    cur.execute(
        """
        insert into doc
            (imo_number, reporting_period, doc_issue_date, doc_expiry_date)
        values (%s,%s,%s,%s)
            on conflict (imo_number, reporting_period) do nothing
        """,
        (
            imo,
            year,
            issue.date() if pd.notna(issue) else None,
            expiry.date() if pd.notna(expiry) else None,
        ),
    )

    # ---- verifier ----
    cur.execute(
        """
        insert into verifier
        (imo_number, reporting_period, verifier_number, verifier_name,
         verifier_nab, verifier_address, verifier_city,
         verifier_accreditation_number, verifier_country)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            on conflict (imo_number, reporting_period) do nothing
        """,
        (
            imo,
            year,
            row["verifier__verifier_number"],
            row["verifier__verifier_name"],
            row["verifier__verifier_nab"],
            row["verifier__verifier_address"],
            row["verifier__verifier_city"],
            row["verifier__verifier_accreditation_number"],
            row["verifier__verifier_country"],
        ),
    )

    # ---- monitoring methods ----
    cur.execute(
        """
        insert into monitoring_methods
            (imo_number, reporting_period, a, b, c, d, d_1)
        values (%s,%s,%s,%s,%s,%s,%s)
            on conflict (imo_number, reporting_period) do nothing
        """,
        (
            imo,
            year,
            row["monitoring_methods__a"],
            row["monitoring_methods__b"],
            row["monitoring_methods__c"],
            row["monitoring_methods__d"],
            row["monitoring_methods__d_1"],
        ),
    )

    # ---- annual monitoring results ----
    cur.execute(
        """
        insert into annual_monitoring_results
        (imo_number, reporting_period,
         total_fuel_consumption_m_tonnes,
         fuel_consumption_on_laden_m_tonnes,
         total_co2_emissions_m_tonnes,
         annual_total_time_spent_at_sea_hours,
         co2_between_ms_ports_m_tonnes,
         co2_from_ms_ports_m_tonnes,
         co2_to_ms_ports_m_tonnes,
         co2_at_berth_m_tonnes,
         co2_passenger_m_tonnes,
         co2_freight_m_tonnes,
         co2_on_laden_m_tonnes,
         avg_fuel_per_distance_kg_n_mile,
         avg_fuel_per_transport_mass_g,
         avg_fuel_per_transport_volume_g,
         avg_fuel_per_transport_dwt_g,
         avg_fuel_per_transport_pax_g,
         avg_fuel_per_transport_freight_g,
         avg_co2_per_distance_kg_n_mile,
         avg_co2_per_transport_mass_g,
         avg_co2_per_transport_volume_g,
         avg_co2_per_transport_dwt_g,
         avg_co2_per_transport_pax_g,
         avg_co2_per_transport_freight_g)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            on conflict (imo_number, reporting_period) do nothing
        """,
        (
            imo,
            year,
            clean_numeric(row[f"{AMR}__totals__total_fuel_consumption_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__fuel_consumptions_assigned_to_on_laden_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__total_co2_emissions_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__annual_total_time_spent_at_sea_[hours]"]),
            clean_numeric(row[f"{AMR}__co2_emissions_from_all_voyages_between_ports_under_a_ms_jurisdiction_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__co2_emissions_from_all_voyages_which_departed_from_ports_under_a_ms_jurisdiction_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__co2_emissions_from_all_voyages_to_ports_under_a_ms_jurisdiction_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__co2_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_at_berth_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__co2_emissions_assigned_to_passenger_transport_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__co2_emissions_assigned_to_freight_transport_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__co2_emissions_assigned_to_on_laden_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__average_energy_efficiency__annual_average_fuel_consumption_per_distance_[kg_/_n_mile]"]),
            clean_numeric(row[f"{AMR}__annual_average_fuel_consumption_per_transport_work_(mass)_[g_/_m_tonnes_·_n_miles]"]),
            clean_numeric(row[f"{AMR}__annual_average_fuel_consumption_per_transport_work_(volume)_[g_/_m³_·_n_miles]"]),
            clean_numeric(row[f"{AMR}__annual_average_fuel_consumption_per_transport_work_(dwt)_[g_/_dwt_carried_·_n_miles]"]),
            clean_numeric(row[f"{AMR}__annual_average_fuel_consumption_per_transport_work_(pax)_[g_/_pax_·_n_miles]"]),
            clean_numeric(row[f"{AMR}__annual_average_fuel_consumption_per_transport_work_(freight)_[g_/_m_tonnes_·_n_miles]"]),
            clean_numeric(row[f"{AMR}__annual_average_co2_emissions_per_distance_[kg_co2_/_n_mile]"]),
            clean_numeric(row[f"{AMR}__annual_average_co2_emissions_per_transport_work_(mass)_[g_co2_/_m_tonnes_·_n_miles]"]),
            clean_numeric(row[f"{AMR}__annual_average_co2_emissions_per_transport_work_(volume)_[g_co2_/_m³_·_n_miles]"]),
            clean_numeric(row[f"{AMR}__annual_average_co2_emissions_per_transport_work_(dwt)_[g_co2_/_dwt_carried_·_n_miles]"]),
            clean_numeric(row[f"{AMR}__annual_average_co2_emissions_per_transport_work_(pax)_[g_co2_/_pax_·_n_miles]"]),
            clean_numeric(row[f"{AMR}__annual_average_co2_emissions_per_transport_work_(freight)_[g_co2_/_m_tonnes_·_n_miles]"]),
        ),
    )

    # ---- voluntary reporting ----
    cur.execute(
        """
        insert into voluntary_reporting
        (imo_number, reporting_period,
         through_ice_n_miles,
         total_time_at_sea_hours,
         total_time_at_sea_through_ice_hours,
         fuel_per_distance_on_laden_kg_n_mile,
         fuel_per_transport_mass_on_laden_g,
         fuel_per_transport_volume_on_laden_g,
         fuel_per_transport_dwt_on_laden_g,
         fuel_per_transport_pax_on_laden_g,
         fuel_per_transport_freight_on_laden_g,
         co2_per_distance_on_laden_kg_n_mile,
         co2_per_transport_mass_on_laden_g,
         co2_per_transport_volume_on_laden_g,
         co2_per_transport_dwt_on_laden_g,
         co2_per_transport_pax_on_laden_g,
         co2_per_transport_freight_on_laden_g,
         additional_info,
         avg_cargo_density_m_tonnes_m3)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            on conflict (imo_number, reporting_period) do nothing
        """,
        (
            imo,
            year,
            clean_numeric(row[f"{VR}__distance_and_time__through_ice_[n_miles]"]),
            clean_numeric(row[f"{VR}__total_time_spent_at_sea_[hours]"]),
            clean_numeric(row[f"{VR}__total_time_spent_at_sea_through_ice_[hours]"]),
            clean_numeric(row[f"{VR}__average_energy_efficiency_on_laden_voyages__fuel_consumption_per_distance_on_laden_voyages_[kg_/_n_mile]"]),
            clean_numeric(row[f"{VR}__fuel_consumption_per_transport_work_(mass)_on_laden_voyages_[g_/_m_tonnes_·_n_miles]"]),
            clean_numeric(row[f"{VR}__fuel_consumption_per_transport_work_(volume)_on_laden_voyages_[g_/_m³_·_n_miles]"]),
            clean_numeric(row[f"{VR}__fuel_consumption_per_transport_work_(dwt)_on_laden_voyages_[g_/_dwt_carried_·_n_miles]"]),
            clean_numeric(row[f"{VR}__fuel_consumption_per_transport_work_(pax)_on_laden_voyages_[g_/_pax_·_n_miles]"]),
            clean_numeric(row[f"{VR}__fuel_consumption_per_transport_work_(freight)_on_laden_voyages_[g_/_m_tonnes_·_n_miles]"]),
            clean_numeric(row[f"{VR}__co2_emissions_per_distance_on_laden_voyages_[kg_co2_/_n_mile]"]),
            clean_numeric(row[f"{VR}__co2_emissions_per_transport_work_(mass)_on_laden_voyages_[g_co2_/_m_tonnes_·_n_miles]"]),
            clean_numeric(row[f"{VR}__co2_emissions_per_transport_work_(volume)_on_laden_voyages_[g_co2_/_m³_·_n_miles]"]),
            clean_numeric(row[f"{VR}__co2_emissions_per_transport_work_(dwt)_on_laden_voyages_[g_co2_/_dwt_carried_·_n_miles]"]),
            clean_numeric(row[f"{VR}__co2_emissions_per_transport_work_(pax)_on_laden_voyages_[g_co2_/_pax_·_n_miles]"]),
            clean_numeric(row[f"{VR}__co2_emissions_per_transport_work_(freight)_on_laden_voyages_[g_co2_/_m_tonnes_·_n_miles]"]),
            row[f"{VR}__additional_voluntary_reporting__additional_information_to_facilitate_the_understanding_of_the_reported_average_operational_energy_efficiency_indicators"] or None,
            clean_numeric(row[f"{VR}__average_density_of_the_cargo_transported_[m_tonnes_/_m³]"]),
        ),
    )


conn.commit()
cur.close()
conn.close()

print("Import complete")
