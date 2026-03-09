import hashlib
import io
import os
import sys
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

import pandas as pd
import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv("../.env")

BASE_URL = "https://mrv.emsa.europa.eu"
FILES_URL = f"{BASE_URL}/api/public-emission-report/downloadable-files"
DOWNLOAD_URL = (
    f"{BASE_URL}/api/public-emission-report/reporting-period-document/binary/{{year}}/{{version}}"
)

AMR = "annual_monitoring_results"
VR = "voluntary_reporting"

TABLES = ["voluntary_reporting", "annual_monitoring_results",
          "monitoring_methods", "verifier", "doc", "company", "ship"]

KNOWN_COLUMNS = frozenset([
    "ship__imo_number", "ship__name", "ship__ship_type", "ship__reporting_period",
    "ship__technical_efficiency", "ship__port_of_registry", "ship__home_port", "ship__ice_class",
    "company__imo_number", "company__name",
    "doc__doc_issue_date", "doc__doc_expiry_date",
    "verifier__verifier_number",
    "verifier__verifier_name", "verifier__verifier_nab", "verifier__verifier_address",
    "verifier__verifier_city", "verifier__verifier_accreditation_number", "verifier__verifier_country",
    "monitoring_methods__a", "monitoring_methods__b", "monitoring_methods__c",
    "monitoring_methods__d", "monitoring_methods__d_1",
    f"{AMR}__totals__total_fuel_consumption_[m_tonnes]",
    f"{AMR}__fuel_consumptions_assigned_to_on_laden_[m_tonnes]",
    f"{AMR}__total_co2_emissions_[m_tonnes]",
    f"{AMR}__co2_emissions_from_all_voyages_between_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__co2_emissions_from_all_voyages_which_departed_from_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__co2_emissions_from_all_voyages_to_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__co2_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_at_berth_[m_tonnes]",
    f"{AMR}__co2_emissions_assigned_to_passenger_transport_[m_tonnes]",
    f"{AMR}__co2_emissions_assigned_to_freight_transport_[m_tonnes]",
    f"{AMR}__co2_emissions_assigned_to_on_laden_[m_tonnes]",
    f"{AMR}__annual_total_time_spent_at_sea_[hours]",
    f"{AMR}__annual_time_spent_at_sea_[hours]",
    f"{AMR}__time_spent_at_sea_[hours]",
    f"{AMR}__average_energy_efficiency__annual_average_fuel_consumption_per_distance_[kg_/_n_mile]",
    f"{AMR}__annual_average_fuel_consumption_per_transport_work_(mass)_[g_/_m_tonnes_·_n_miles]",
    f"{AMR}__annual_average_fuel_consumption_per_transport_work_(volume)_[g_/_m³_·_n_miles]",
    f"{AMR}__annual_average_fuel_consumption_per_transport_work_(dwt)_[g_/_dwt_carried_·_n_miles]",
    f"{AMR}__annual_average_fuel_consumption_per_transport_work_(pax)_[g_/_pax_·_n_miles]",
    f"{AMR}__annual_average_fuel_consumption_per_transport_work_(freight)_[g_/_m_tonnes_·_n_miles]",
    f"{AMR}__annual_average_co2_emissions_per_distance_[kg_co2_/_n_mile]",
    f"{AMR}__annual_average_co2_emissions_per_transport_work_(mass)_[g_co2_/_m_tonnes_·_n_miles]",
    f"{AMR}__annual_average_co2_emissions_per_transport_work_(volume)_[g_co2_/_m³_·_n_miles]",
    f"{AMR}__annual_average_co2_emissions_per_transport_work_(dwt)_[g_co2_/_dwt_carried_·_n_miles]",
    f"{AMR}__annual_average_co2_emissions_per_transport_work_(pax)_[g_co2_/_pax_·_n_miles]",
    f"{AMR}__annual_average_co2_emissions_per_transport_work_(freight)_[g_co2_/_m_tonnes_·_n_miles]",
    f"{VR}__distance_and_time__through_ice_[n_miles]",
    f"{VR}__total_time_spent_at_sea_[hours]",
    f"{VR}__time_spent_at_sea_[hours]",
    f"{VR}__total_time_spent_at_sea_through_ice_[hours]",
    f"{VR}__average_energy_efficiency_on_laden_voyages__fuel_consumption_per_distance_on_laden_voyages_[kg_/_n_mile]",
    f"{VR}__fuel_consumption_per_transport_work_(mass)_on_laden_voyages_[g_/_m_tonnes_·_n_miles]",
    f"{VR}__fuel_consumption_per_transport_work_(volume)_on_laden_voyages_[g_/_m³_·_n_miles]",
    f"{VR}__fuel_consumption_per_transport_work_(dwt)_on_laden_voyages_[g_/_dwt_carried_·_n_miles]",
    f"{VR}__fuel_consumption_per_transport_work_(pax)_on_laden_voyages_[g_/_pax_·_n_miles]",
    f"{VR}__fuel_consumption_per_transport_work_(freight)_on_laden_voyages_[g_/_m_tonnes_·_n_miles]",
    f"{VR}__co2_emissions_per_distance_on_laden_voyages_[kg_co2_/_n_mile]",
    f"{VR}__co2_emissions_per_transport_work_(mass)_on_laden_voyages_[g_co2_/_m_tonnes_·_n_miles]",
    f"{VR}__co2_emissions_per_transport_work_(volume)_on_laden_voyages_[g_co2_/_m³_·_n_miles]",
    f"{VR}__co2_emissions_per_transport_work_(dwt)_on_laden_voyages_[g_co2_/_dwt_carried_·_n_miles]",
    f"{VR}__co2_emissions_per_transport_work_(pax)_on_laden_voyages_[g_co2_/_pax_·_n_miles]",
    f"{VR}__co2_emissions_per_transport_work_(freight)_on_laden_voyages_[g_co2_/_m_tonnes_·_n_miles]",
    f"{VR}__additional_voluntary_reporting__additional_information_to_facilitate_the_understanding_of_the_reported_average_operational_energy_efficiency_indicators",
    f"{VR}__average_density_of_the_cargo_transported_[m_tonnes_/_m³]",
    f"{AMR}__fuel_consumption__total_fuel_consumption_[m_tonnes]",
    f"{AMR}__total_fuel_benefitting_from_a_derogation_in_accordance_with_part_c,_point_1.2,_of_annex_ii_to_regulation_(eu)_2015/757_(voluntary)_[m_tonnes]",
    f"{AMR}__fuel_consumptions_assigned_to_cargo_heating_[m_tonnes]",
    f"{AMR}__fuel_consumptions_assigned_to_dynamic_positioning_[m_tonnes]",
    f"{AMR}__co2_emissions__total_co2_emissions_[m_tonnes]",
    f"{AMR}__co2_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__co2_emissions_to_be_reported_under_directive_2003/87/ec_[m_tonnes]",
    f"{AMR}__ch4_emissions__total_ch4_emissions_[m_tonnes]",
    f"{AMR}__ch4_emissions_from_all_voyages_between_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__ch4_emissions_from_all_voyages_which_departed_from_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__ch4_emissions_from_all_voyages_to_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__ch4_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_at_berth_[m_tonnes]",
    f"{AMR}__ch4_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__ch4_emissions_assigned_to_on_laden_[m_tonnes]",
    f"{AMR}__ch4_emissions_assigned_to_passenger_transport_[m_tonnes]",
    f"{AMR}__ch4_emissions_assigned_to_freight_transport_[m_tonnes]",
    f"{AMR}__ch4_emissions_to_be_reported_under_directive_2003/87/ec_[m_tonnes]",
    f"{AMR}__n2o_emissions__total_n2o_emissions_[m_tonnes]",
    f"{AMR}__n2o_emissions_from_all_voyages_between_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__n2o_emissions_from_all_voyages_which_departed_from_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__n2o_emissions_from_all_voyages_to_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__n2o_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_at_berth_[m_tonnes]",
    f"{AMR}__n2o_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__n2o_emissions_assigned_to_on_laden_[m_tonnes]",
    f"{AMR}__n2o_emissions_assigned_to_passenger_transport_[m_tonnes]",
    f"{AMR}__n2o_emissions_assigned_to_freight_transport_[m_tonnes]",
    f"{AMR}__n2o_emissions_to_be_reported_under_directive_2003/87/ec_[m_tonnes]",
    f"{AMR}__co2eq_emissions__total_co2eq_emissions_[m_tonnes]",
    f"{AMR}__co2eq_emissions_from_all_voyages_between_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__co2eq_emissions_from_all_voyages_which_departed_from_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__co2eq_emissions_from_all_voyages_to_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__co2eq_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_at_berth_[m_tonnes]",
    f"{AMR}__co2eq_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_[m_tonnes]",
    f"{AMR}__co2eq_emissions_assigned_to_on_laden_[m_tonnes]",
    f"{AMR}__co2eq_emissions_assigned_to_passenger_transport_[m_tonnes]",
    f"{AMR}__co2eq_emissions_assigned_to_freight_transport_[m_tonnes]",
    f"{AMR}__co2eq_emissions_to_be_reported_under_directive_2003/87/ec_[m_tonnes]",
    f"{AMR}__co2eq_emissions_benefitting_from_a_derogation_in_accordance_with_part_c,_point_1.2,_of_annex_ii_to_regulation_(eu)_2015/757_(voluntary)_[m_tonnes]",
    f"{AMR}__distance_and_time__distance_through_ice_[n_miles]",
    f"{AMR}__time_spent_at_sea_through_ice_[hours]",
    f"{AMR}__average_energy_efficiency__fuel_consumption_per_distance_[kg_/_n_mile]",
    f"{AMR}__fuel_consumption_per_distance_on_laden_voyages_[kg_/_n_mile]",
    f"{AMR}__fuel_consumption_per_transport_work_(mass)_[g_/_m_tonnes_·_n_miles]",
    f"{AMR}__fuel_consumption_per_transport_work_(mass)_on_laden_voyages_[g_/_m_tonnes_·_n_miles]",
    f"{AMR}__fuel_consumption_per_transport_work_(volume)_[g_/_m³_·_n_miles]",
    f"{AMR}__fuel_consumption_per_transport_work_(volume)_on_laden_voyages_[g_/_m³_·_n_miles]",
    f"{AMR}__fuel_consumption_per_transport_work_(dwt)_[g_/_dwt_carried_·_n_miles]",
    f"{AMR}__fuel_consumption_per_transport_work_(dwt)_on_laden_voyages_[g_/_dwt_carried_·_n_miles]",
    f"{AMR}__fuel_consumption_per_transport_work_(pax)_[g_/_pax_·_n_miles]",
    f"{AMR}__fuel_consumption_per_transport_work_(pax)_on_laden_voyages_[g_/_pax_·_n_miles]",
    f"{AMR}__fuel_consumption_per_transport_work_(freight)_[g_/_m_tonnes_·_n_miles]",
    f"{AMR}__fuel_consumption_per_transport_work_(freight)_on_laden_voyages_[g_/_m_tonnes_·_n_miles]",
    f"{AMR}__fuel_consumption_per_time_spent_at_sea_[m_tonnes_/_hour]",
    f"{AMR}__co2_emissions_per_distance_[kg_co2_/_n_mile]",
    f"{AMR}__co2_emissions_per_distance_on_laden_voyages_[kg_co2_/_n_mile]",
    f"{AMR}__co2_emissions_per_transport_work_(mass)_[g_co2_/_m_tonnes_·_n_miles]",
    f"{AMR}__co2_emissions_per_transport_work_(mass)_on_laden_voyages_[g_co2_/_m_tonnes_·_n_miles]",
    f"{AMR}__co2_emissions_per_transport_work_(volume)_[g_co2_/_m³_·_n_miles]",
    f"{AMR}__co2_emissions_per_transport_work_(volume)_on_laden_voyages_[g_co2_/_m³_·_n_miles]",
    f"{AMR}__co2_emissions_per_transport_work_(dwt)_[g_co2_/_dwt_carried_·_n_miles]",
    f"{AMR}__co2_emissions_per_transport_work_(dwt)_on_laden_voyages_[g_co2_/_dwt_carried_·_n_miles]",
    f"{AMR}__co2_emissions_per_transport_work_(pax)_[g_co2_/_pax_·_n_miles]",
    f"{AMR}__co2_emissions_per_transport_work_(pax)_on_laden_voyages_[g_co2_/_pax_·_n_miles]",
    f"{AMR}__co2_emissions_per_transport_work_(freight)_[g_co2_/_m_tonnes_·_n_miles]",
    f"{AMR}__co2_emissions_per_transport_work_(freight)_on_laden_voyages_[g_co2_/_m_tonnes_·_n_miles]",
    f"{AMR}__co2_emissions_per_time_spent_at_sea_[m_tonnes_co2_/_hour]",
    f"{AMR}__co2eq_emissions_per_distance_[kg_co2eq_/_n_mile]",
    f"{AMR}__co2eq_emissions_per_distance_on_laden_voyages_[kg_co2eq_/_n_mile]",
    f"{AMR}__co2eq_emissions_per_transport_work_(mass)_[g_co2eq_/_m_tonnes_·_n_miles]",
    f"{AMR}__co2eq_emissions_per_transport_work_(mass)_on_laden_voyages_[g_co2eq_/_m_tonnes_·_n_miles]",
    f"{AMR}__co2eq_emissions_per_transport_work_(volume)_[g_co2eq_/_m³_·_n_miles]",
    f"{AMR}__co2eq_emissions_per_transport_work_(volume)_on_laden_voyages_[g_co2eq_/_m³_·_n_miles]",
    f"{AMR}__co2eq_emissions_per_transport_work_(dwt)_[g_co2eq_/_dwt_carried_·_n_miles]",
    f"{AMR}__co2eq_emissions_per_transport_work_(dwt)_on_laden_voyages_[g_co2eq_/_dwt_carried_·_n_miles]",
    f"{AMR}__co2eq_emissions_per_transport_work_(pax)_[g_co2eq_/_pax_·_n_miles]",
    f"{AMR}__co2eq_emissions_per_transport_work_(pax)_on_laden_voyages_[g_co2eq_/_pax_·_n_miles]",
    f"{AMR}__co2eq_emissions_per_transport_work_(freight)_[g_co2eq_/_m_tonnes_·_n_miles]",
    f"{AMR}__co2eq_emissions_per_transport_work_(freight)_on_laden_voyages_[g_co2eq_/_m_tonnes_·_n_miles]",
    f"{AMR}__co2eq_emissions_per_time_spent_at_sea_[m_tonnes_co2eq_/_m_tonnes_·_n_miles]",
    f"{AMR}__additional_voluntary_reporting__additional_information_to_facilitate_the_understanding_of_the_reported_average_operational_energy_efficiency_indicators",
    f"{AMR}__average_density_of_the_cargo_transported_[m_tonnes_/_m³]",
])


def clean_numeric(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        if value.lower() in ["n/a", "division by zero!", ""]:
            return None
    try:
        return float(value)
    except Exception:
        return None


def get_col(row, *keys):
    for key in keys:
        if key in row.index:
            val = row[key]
            if not (isinstance(val, float) and pd.isna(val)):
                return val
    return None


def build_columns(excel_bytes):
    header_rows = pd.read_excel(io.BytesIO(excel_bytes), header=None, nrows=3)
    groups = header_rows.iloc[0].ffill()
    subgroups = header_rows.iloc[1]
    fields = header_rows.iloc[2]

    def normalise(text):
        return (
            str(text).strip().lower()
            .replace(" ", "_")
            .replace("₂", "2")
            .replace("₄", "4")
            .replace("₃", "3")
        )

    columns, seen = [], {}
    for group, subgroup, field in zip(groups, subgroups, fields):
        g = normalise(group)
        f = normalise(field)
        if pd.isna(subgroup):
            col = f"{g}__{f}"
        else:
            s = normalise(subgroup)
            col = f"{g}__{s}__{f}"
        if col in seen:
            seen[col] += 1
            col = f"{col}_{seen[col]}"
        else:
            seen[col] = 0
        columns.append(col)
    return columns


def load_df(excel_bytes):
    columns = build_columns(excel_bytes)
    df = pd.read_excel(io.BytesIO(excel_bytes), header=None, skiprows=3)
    df.columns = columns
    return df


def check_unknown_columns(df_columns, year):
    unknown = [c for c in df_columns if c not in KNOWN_COLUMNS]
    if unknown:
        print(f"\n!!! UNKNOWN COLUMNS DETECTED in year {year} !!!")
        for col in unknown:
            print(f"  - {col}")
        print("\nSchema update required. Exiting with code 1.")
        sys.exit(1)


def get_stored_hash(cur, year):
    cur.execute("select file_hash from data_versions where year = %s", (year,))
    row = cur.fetchone()
    return row[0] if row else None


def save_hash(cur, year, file_hash):
    cur.execute(
        """
        insert into data_versions (year, file_hash, imported_at)
        values (%s, %s, now())
        on conflict (year) do update
            set file_hash = excluded.file_hash,
                imported_at = now()
        """,
        (year, file_hash),
    )


def delete_year(cur, year):
    for table in TABLES:
        cur.execute(f"delete from {table} where reporting_period = %s", (year,))
    print(f"  Deleted existing data for {year}")


def import_row(cur, row):
    imo = int(row["ship__imo_number"])
    year = int(row["ship__reporting_period"])
    is_new_format = "company__imo_number" in row.index

    cur.execute(
        """
        insert into ship
            (imo_number, reporting_period, name, ship_type,
             technical_efficiency, port_of_registry, home_port, ice_class)
        values (%s,%s,%s,%s,%s,%s,%s,%s)
        on conflict (imo_number, reporting_period) do nothing
        """,
        (imo, year,
         row["ship__name"], row["ship__ship_type"],
         row["ship__technical_efficiency"], row["ship__port_of_registry"],
         row["ship__home_port"], row["ship__ice_class"]),
    )

    if is_new_format:
        cur.execute(
            """
            insert into company (imo_number, reporting_period, company_imo_number, company_name)
            values (%s,%s,%s,%s)
            on conflict (imo_number, reporting_period) do nothing
            """,
            (imo, year,
             get_col(row, "company__imo_number"),
             get_col(row, "company__name")),
        )

    issue = pd.to_datetime(row["doc__doc_issue_date"], dayfirst=True, errors="coerce")
    expiry = pd.to_datetime(row["doc__doc_expiry_date"], dayfirst=True, errors="coerce")
    cur.execute(
        """
        insert into doc (imo_number, reporting_period, doc_issue_date, doc_expiry_date)
        values (%s,%s,%s,%s)
        on conflict (imo_number, reporting_period) do nothing
        """,
        (imo, year,
         issue.date() if pd.notna(issue) else None,
         expiry.date() if pd.notna(expiry) else None),
    )

    cur.execute(
        """
        insert into verifier
            (imo_number, reporting_period, verifier_number, verifier_name,
             verifier_nab, verifier_address, verifier_city,
             verifier_accreditation_number, verifier_country)
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        on conflict (imo_number, reporting_period) do nothing
        """,
        (imo, year,
         get_col(row, "verifier__verifier_number"),
         row["verifier__verifier_name"],
         row["verifier__verifier_nab"],
         row["verifier__verifier_address"],
         row["verifier__verifier_city"],
         row["verifier__verifier_accreditation_number"],
         row["verifier__verifier_country"]),
    )

    cur.execute(
        """
        insert into monitoring_methods (imo_number, reporting_period, a, b, c, d, d_1)
        values (%s,%s,%s,%s,%s,%s,%s)
        on conflict (imo_number, reporting_period) do nothing
        """,
        (imo, year,
         row["monitoring_methods__a"], row["monitoring_methods__b"],
         row["monitoring_methods__c"], row["monitoring_methods__d"],
         row["monitoring_methods__d_1"]),
    )

    total_fuel = clean_numeric(get_col(
        row,
        f"{AMR}__fuel_consumption__total_fuel_consumption_[m_tonnes]",
        f"{AMR}__totals__total_fuel_consumption_[m_tonnes]",
    ))
    total_co2 = clean_numeric(get_col(
        row,
        f"{AMR}__co2_emissions__total_co2_emissions_[m_tonnes]",
        f"{AMR}__total_co2_emissions_[m_tonnes]",
    ))
    time_at_sea = clean_numeric(get_col(
        row,
        f"{AMR}__time_spent_at_sea_[hours]",
        f"{AMR}__annual_time_spent_at_sea_[hours]",
        f"{AMR}__annual_total_time_spent_at_sea_[hours]",
    ))
    fuel_per_dist = clean_numeric(get_col(
        row,
        f"{AMR}__average_energy_efficiency__fuel_consumption_per_distance_[kg_/_n_mile]",
        f"{AMR}__average_energy_efficiency__annual_average_fuel_consumption_per_distance_[kg_/_n_mile]",
    ))
    fuel_per_mass = clean_numeric(get_col(
        row,
        f"{AMR}__fuel_consumption_per_transport_work_(mass)_[g_/_m_tonnes_·_n_miles]",
        f"{AMR}__annual_average_fuel_consumption_per_transport_work_(mass)_[g_/_m_tonnes_·_n_miles]",
    ))
    fuel_per_vol = clean_numeric(get_col(
        row,
        f"{AMR}__fuel_consumption_per_transport_work_(volume)_[g_/_m³_·_n_miles]",
        f"{AMR}__annual_average_fuel_consumption_per_transport_work_(volume)_[g_/_m³_·_n_miles]",
    ))
    fuel_per_dwt = clean_numeric(get_col(
        row,
        f"{AMR}__fuel_consumption_per_transport_work_(dwt)_[g_/_dwt_carried_·_n_miles]",
        f"{AMR}__annual_average_fuel_consumption_per_transport_work_(dwt)_[g_/_dwt_carried_·_n_miles]",
    ))
    fuel_per_pax = clean_numeric(get_col(
        row,
        f"{AMR}__fuel_consumption_per_transport_work_(pax)_[g_/_pax_·_n_miles]",
        f"{AMR}__annual_average_fuel_consumption_per_transport_work_(pax)_[g_/_pax_·_n_miles]",
    ))
    fuel_per_freight = clean_numeric(get_col(
        row,
        f"{AMR}__fuel_consumption_per_transport_work_(freight)_[g_/_m_tonnes_·_n_miles]",
        f"{AMR}__annual_average_fuel_consumption_per_transport_work_(freight)_[g_/_m_tonnes_·_n_miles]",
    ))
    co2_per_dist = clean_numeric(get_col(
        row,
        f"{AMR}__co2_emissions_per_distance_[kg_co2_/_n_mile]",
        f"{AMR}__annual_average_co2_emissions_per_distance_[kg_co2_/_n_mile]",
    ))
    co2_per_mass = clean_numeric(get_col(
        row,
        f"{AMR}__co2_emissions_per_transport_work_(mass)_[g_co2_/_m_tonnes_·_n_miles]",
        f"{AMR}__annual_average_co2_emissions_per_transport_work_(mass)_[g_co2_/_m_tonnes_·_n_miles]",
    ))
    co2_per_vol = clean_numeric(get_col(
        row,
        f"{AMR}__co2_emissions_per_transport_work_(volume)_[g_co2_/_m³_·_n_miles]",
        f"{AMR}__annual_average_co2_emissions_per_transport_work_(volume)_[g_co2_/_m³_·_n_miles]",
    ))
    co2_per_dwt = clean_numeric(get_col(
        row,
        f"{AMR}__co2_emissions_per_transport_work_(dwt)_[g_co2_/_dwt_carried_·_n_miles]",
        f"{AMR}__annual_average_co2_emissions_per_transport_work_(dwt)_[g_co2_/_dwt_carried_·_n_miles]",
    ))
    co2_per_pax = clean_numeric(get_col(
        row,
        f"{AMR}__co2_emissions_per_transport_work_(pax)_[g_co2_/_pax_·_n_miles]",
        f"{AMR}__annual_average_co2_emissions_per_transport_work_(pax)_[g_co2_/_pax_·_n_miles]",
    ))
    co2_per_freight = clean_numeric(get_col(
        row,
        f"{AMR}__co2_emissions_per_transport_work_(freight)_[g_co2_/_m_tonnes_·_n_miles]",
        f"{AMR}__annual_average_co2_emissions_per_transport_work_(freight)_[g_co2_/_m_tonnes_·_n_miles]",
    ))

    additional_info = get_col(
        row,
        f"{AMR}__additional_voluntary_reporting__additional_information_to_facilitate_the_understanding_of_the_reported_average_operational_energy_efficiency_indicators",
    ) or None
    avg_cargo_density = clean_numeric(get_col(
        row, f"{AMR}__average_density_of_the_cargo_transported_[m_tonnes_/_m³]",
    ))

    cur.execute(
        f"""
        insert into annual_monitoring_results (
            imo_number, reporting_period,
            total_fuel_consumption_m_tonnes,
            fuel_consumption_on_laden_m_tonnes,
            fuel_consumption_derogation_m_tonnes,
            fuel_consumption_cargo_heating_m_tonnes,
            fuel_consumption_dynamic_positioning_m_tonnes,
            total_co2_emissions_m_tonnes,
            annual_total_time_spent_at_sea_hours,
            co2_between_ms_ports_m_tonnes,
            co2_from_ms_ports_m_tonnes,
            co2_to_ms_ports_m_tonnes,
            co2_at_berth_m_tonnes,
            co2_at_ms_ports_m_tonnes,
            co2_passenger_m_tonnes,
            co2_freight_m_tonnes,
            co2_on_laden_m_tonnes,
            co2_ets_m_tonnes,
            total_ch4_emissions_m_tonnes,
            ch4_between_ms_ports_m_tonnes,
            ch4_from_ms_ports_m_tonnes,
            ch4_to_ms_ports_m_tonnes,
            ch4_at_berth_m_tonnes,
            ch4_at_ms_ports_m_tonnes,
            ch4_on_laden_m_tonnes,
            ch4_passenger_m_tonnes,
            ch4_freight_m_tonnes,
            ch4_ets_m_tonnes,
            total_n2o_emissions_m_tonnes,
            n2o_between_ms_ports_m_tonnes,
            n2o_from_ms_ports_m_tonnes,
            n2o_to_ms_ports_m_tonnes,
            n2o_at_berth_m_tonnes,
            n2o_at_ms_ports_m_tonnes,
            n2o_on_laden_m_tonnes,
            n2o_passenger_m_tonnes,
            n2o_freight_m_tonnes,
            n2o_ets_m_tonnes,
            total_co2eq_emissions_m_tonnes,
            co2eq_between_ms_ports_m_tonnes,
            co2eq_from_ms_ports_m_tonnes,
            co2eq_to_ms_ports_m_tonnes,
            co2eq_at_berth_m_tonnes,
            co2eq_at_ms_ports_m_tonnes,
            co2eq_on_laden_m_tonnes,
            co2eq_passenger_m_tonnes,
            co2eq_freight_m_tonnes,
            co2eq_ets_m_tonnes,
            co2eq_derogation_m_tonnes,
            distance_through_ice_n_miles,
            time_spent_at_sea_through_ice_hours,
            avg_fuel_per_distance_kg_n_mile,
            avg_fuel_per_distance_on_laden_kg_n_mile,
            avg_fuel_per_transport_mass_g,
            avg_fuel_per_transport_mass_on_laden_g,
            avg_fuel_per_transport_volume_g,
            avg_fuel_per_transport_volume_on_laden_g,
            avg_fuel_per_transport_dwt_g,
            avg_fuel_per_transport_dwt_on_laden_g,
            avg_fuel_per_transport_pax_g,
            avg_fuel_per_transport_pax_on_laden_g,
            avg_fuel_per_transport_freight_g,
            avg_fuel_per_transport_freight_on_laden_g,
            avg_fuel_per_time_at_sea_m_tonnes_hour,
            avg_co2_per_distance_kg_n_mile,
            avg_co2_per_distance_on_laden_kg_n_mile,
            avg_co2_per_transport_mass_g,
            avg_co2_per_transport_mass_on_laden_g,
            avg_co2_per_transport_volume_g,
            avg_co2_per_transport_volume_on_laden_g,
            avg_co2_per_transport_dwt_g,
            avg_co2_per_transport_dwt_on_laden_g,
            avg_co2_per_transport_pax_g,
            avg_co2_per_transport_pax_on_laden_g,
            avg_co2_per_transport_freight_g,
            avg_co2_per_transport_freight_on_laden_g,
            avg_co2_per_time_at_sea_m_tonnes_hour,
            avg_co2eq_per_distance_kg_n_mile,
            avg_co2eq_per_distance_on_laden_kg_n_mile,
            avg_co2eq_per_transport_mass_g,
            avg_co2eq_per_transport_mass_on_laden_g,
            avg_co2eq_per_transport_volume_g,
            avg_co2eq_per_transport_volume_on_laden_g,
            avg_co2eq_per_transport_dwt_g,
            avg_co2eq_per_transport_dwt_on_laden_g,
            avg_co2eq_per_transport_pax_g,
            avg_co2eq_per_transport_pax_on_laden_g,
            avg_co2eq_per_transport_freight_g,
            avg_co2eq_per_transport_freight_on_laden_g,
            avg_co2eq_per_time_at_sea,
            additional_info,
            avg_cargo_density_m_tonnes_m3
        )
        values (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
            %s,%s
        )
        on conflict (imo_number, reporting_period) do nothing
        """,
        (
            imo, year,
            total_fuel,
            clean_numeric(row[f"{AMR}__fuel_consumptions_assigned_to_on_laden_[m_tonnes]"]),
            clean_numeric(get_col(row, f"{AMR}__total_fuel_benefitting_from_a_derogation_in_accordance_with_part_c,_point_1.2,_of_annex_ii_to_regulation_(eu)_2015/757_(voluntary)_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__fuel_consumptions_assigned_to_cargo_heating_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__fuel_consumptions_assigned_to_dynamic_positioning_[m_tonnes]")),
            total_co2,
            time_at_sea,
            clean_numeric(row[f"{AMR}__co2_emissions_from_all_voyages_between_ports_under_a_ms_jurisdiction_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__co2_emissions_from_all_voyages_which_departed_from_ports_under_a_ms_jurisdiction_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__co2_emissions_from_all_voyages_to_ports_under_a_ms_jurisdiction_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__co2_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_at_berth_[m_tonnes]"]),
            clean_numeric(get_col(row, f"{AMR}__co2_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_[m_tonnes]")),
            clean_numeric(row[f"{AMR}__co2_emissions_assigned_to_passenger_transport_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__co2_emissions_assigned_to_freight_transport_[m_tonnes]"]),
            clean_numeric(row[f"{AMR}__co2_emissions_assigned_to_on_laden_[m_tonnes]"]),
            clean_numeric(get_col(row, f"{AMR}__co2_emissions_to_be_reported_under_directive_2003/87/ec_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__ch4_emissions__total_ch4_emissions_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__ch4_emissions_from_all_voyages_between_ports_under_a_ms_jurisdiction_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__ch4_emissions_from_all_voyages_which_departed_from_ports_under_a_ms_jurisdiction_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__ch4_emissions_from_all_voyages_to_ports_under_a_ms_jurisdiction_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__ch4_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_at_berth_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__ch4_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__ch4_emissions_assigned_to_on_laden_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__ch4_emissions_assigned_to_passenger_transport_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__ch4_emissions_assigned_to_freight_transport_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__ch4_emissions_to_be_reported_under_directive_2003/87/ec_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__n2o_emissions__total_n2o_emissions_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__n2o_emissions_from_all_voyages_between_ports_under_a_ms_jurisdiction_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__n2o_emissions_from_all_voyages_which_departed_from_ports_under_a_ms_jurisdiction_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__n2o_emissions_from_all_voyages_to_ports_under_a_ms_jurisdiction_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__n2o_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_at_berth_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__n2o_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__n2o_emissions_assigned_to_on_laden_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__n2o_emissions_assigned_to_passenger_transport_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__n2o_emissions_assigned_to_freight_transport_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__n2o_emissions_to_be_reported_under_directive_2003/87/ec_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions__total_co2eq_emissions_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_from_all_voyages_between_ports_under_a_ms_jurisdiction_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_from_all_voyages_which_departed_from_ports_under_a_ms_jurisdiction_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_from_all_voyages_to_ports_under_a_ms_jurisdiction_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_at_berth_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_which_occurred_within_ports_under_a_ms_jurisdiction_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_assigned_to_on_laden_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_assigned_to_passenger_transport_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_assigned_to_freight_transport_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_to_be_reported_under_directive_2003/87/ec_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_benefitting_from_a_derogation_in_accordance_with_part_c,_point_1.2,_of_annex_ii_to_regulation_(eu)_2015/757_(voluntary)_[m_tonnes]")),
            clean_numeric(get_col(row, f"{AMR}__distance_and_time__distance_through_ice_[n_miles]")),
            clean_numeric(get_col(row, f"{AMR}__time_spent_at_sea_through_ice_[hours]")),
            fuel_per_dist,
            clean_numeric(get_col(row, f"{AMR}__fuel_consumption_per_distance_on_laden_voyages_[kg_/_n_mile]")),
            fuel_per_mass,
            clean_numeric(get_col(row, f"{AMR}__fuel_consumption_per_transport_work_(mass)_on_laden_voyages_[g_/_m_tonnes_·_n_miles]")),
            fuel_per_vol,
            clean_numeric(get_col(row, f"{AMR}__fuel_consumption_per_transport_work_(volume)_on_laden_voyages_[g_/_m³_·_n_miles]")),
            fuel_per_dwt,
            clean_numeric(get_col(row, f"{AMR}__fuel_consumption_per_transport_work_(dwt)_on_laden_voyages_[g_/_dwt_carried_·_n_miles]")),
            fuel_per_pax,
            clean_numeric(get_col(row, f"{AMR}__fuel_consumption_per_transport_work_(pax)_on_laden_voyages_[g_/_pax_·_n_miles]")),
            fuel_per_freight,
            clean_numeric(get_col(row, f"{AMR}__fuel_consumption_per_transport_work_(freight)_on_laden_voyages_[g_/_m_tonnes_·_n_miles]")),
            clean_numeric(get_col(row, f"{AMR}__fuel_consumption_per_time_spent_at_sea_[m_tonnes_/_hour]")),
            co2_per_dist,
            clean_numeric(get_col(row, f"{AMR}__co2_emissions_per_distance_on_laden_voyages_[kg_co2_/_n_mile]")),
            co2_per_mass,
            clean_numeric(get_col(row, f"{AMR}__co2_emissions_per_transport_work_(mass)_on_laden_voyages_[g_co2_/_m_tonnes_·_n_miles]")),
            co2_per_vol,
            clean_numeric(get_col(row, f"{AMR}__co2_emissions_per_transport_work_(volume)_on_laden_voyages_[g_co2_/_m³_·_n_miles]")),
            co2_per_dwt,
            clean_numeric(get_col(row, f"{AMR}__co2_emissions_per_transport_work_(dwt)_on_laden_voyages_[g_co2_/_dwt_carried_·_n_miles]")),
            co2_per_pax,
            clean_numeric(get_col(row, f"{AMR}__co2_emissions_per_transport_work_(pax)_on_laden_voyages_[g_co2_/_pax_·_n_miles]")),
            co2_per_freight,
            clean_numeric(get_col(row, f"{AMR}__co2_emissions_per_transport_work_(freight)_on_laden_voyages_[g_co2_/_m_tonnes_·_n_miles]")),
            clean_numeric(get_col(row, f"{AMR}__co2_emissions_per_time_spent_at_sea_[m_tonnes_co2_/_hour]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_per_distance_[kg_co2eq_/_n_mile]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_per_distance_on_laden_voyages_[kg_co2eq_/_n_mile]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_per_transport_work_(mass)_[g_co2eq_/_m_tonnes_·_n_miles]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_per_transport_work_(mass)_on_laden_voyages_[g_co2eq_/_m_tonnes_·_n_miles]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_per_transport_work_(volume)_[g_co2eq_/_m³_·_n_miles]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_per_transport_work_(volume)_on_laden_voyages_[g_co2eq_/_m³_·_n_miles]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_per_transport_work_(dwt)_[g_co2eq_/_dwt_carried_·_n_miles]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_per_transport_work_(dwt)_on_laden_voyages_[g_co2eq_/_dwt_carried_·_n_miles]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_per_transport_work_(pax)_[g_co2eq_/_pax_·_n_miles]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_per_transport_work_(pax)_on_laden_voyages_[g_co2eq_/_pax_·_n_miles]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_per_transport_work_(freight)_[g_co2eq_/_m_tonnes_·_n_miles]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_per_transport_work_(freight)_on_laden_voyages_[g_co2eq_/_m_tonnes_·_n_miles]")),
            clean_numeric(get_col(row, f"{AMR}__co2eq_emissions_per_time_spent_at_sea_[m_tonnes_co2eq_/_m_tonnes_·_n_miles]")),
            additional_info,
            avg_cargo_density,
        ),
    )

    if is_new_format:
        return

    cur.execute(
        f"""
        insert into voluntary_reporting (
            imo_number, reporting_period,
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
            avg_cargo_density_m_tonnes_m3
        )
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        on conflict (imo_number, reporting_period) do nothing
        """,
        (imo, year,
         clean_numeric(row[f"{VR}__distance_and_time__through_ice_[n_miles]"]),
         clean_numeric(get_col(
             row,
             f"{VR}__total_time_spent_at_sea_[hours]",
             f"{VR}__time_spent_at_sea_[hours]",
         )),
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


def fetch_available_files():
    resp = requests.get(FILES_URL, timeout=30)
    resp.raise_for_status()
    return {r["reportingPeriod"]: r["version"] for r in resp.json()["results"]}


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    available = fetch_available_files()
    print(f"Available years: {sorted(available.keys())}")

    for year, version in sorted(available.items()):
        print(f"\n[{year}] Checking (version {version})...")

        url = DOWNLOAD_URL.format(year=year, version=version)
        resp = requests.get(url, timeout=120)
        print(f"  Download status: {resp.status_code}, size: {len(resp.content)} bytes")
        if resp.status_code != 200:
            print(f"  WARNING: skipping {year}")
            continue

        excel_bytes = resp.content
        file_hash = hashlib.sha256(excel_bytes).hexdigest()

        stored_hash = get_stored_hash(cur, year)
        if stored_hash == file_hash:
            print(f"  No change — skipping")
            continue

        print(f"  New version detected — importing...")
        df = load_df(excel_bytes)
        check_unknown_columns(df.columns.tolist(), year)
        delete_year(cur, year)

        for i, (_, row) in enumerate(df.iterrows()):
            import_row(cur, row)
            if (i + 1) % 500 == 0:
                print(f"  {i + 1} rows...")

        save_hash(cur, year, file_hash)
        conn.commit()
        print(f"  Done — {len(df)} rows imported")

    cur.close()
    conn.close()
    print("\nSync complete")


if __name__ == "__main__":
    main()
