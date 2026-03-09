-- Run each block separately in Supabase SQL editor

-- BLOCK 1: company table (2024+)
create table if not exists company (
    imo_number          integer not null,
    reporting_period    integer not null,
    company_imo_number  integer,
    company_name        text,
    primary key (imo_number, reporting_period)
);

-- BLOCK 2: annual_monitoring_results — 2024 fuel additions
alter table annual_monitoring_results
    add column if not exists fuel_consumption_derogation_m_tonnes        numeric,
    add column if not exists fuel_consumption_cargo_heating_m_tonnes      numeric,
    add column if not exists fuel_consumption_dynamic_positioning_m_tonnes numeric;

-- BLOCK 3: annual_monitoring_results — 2024 CO2 additions
alter table annual_monitoring_results
    add column if not exists co2_at_ms_ports_m_tonnes numeric,
    add column if not exists co2_ets_m_tonnes          numeric;

-- BLOCK 4: CH4 emissions
alter table annual_monitoring_results
    add column if not exists total_ch4_emissions_m_tonnes  numeric,
    add column if not exists ch4_between_ms_ports_m_tonnes numeric,
    add column if not exists ch4_from_ms_ports_m_tonnes    numeric,
    add column if not exists ch4_to_ms_ports_m_tonnes      numeric,
    add column if not exists ch4_at_berth_m_tonnes         numeric,
    add column if not exists ch4_at_ms_ports_m_tonnes      numeric,
    add column if not exists ch4_on_laden_m_tonnes         numeric,
    add column if not exists ch4_passenger_m_tonnes        numeric,
    add column if not exists ch4_freight_m_tonnes          numeric,
    add column if not exists ch4_ets_m_tonnes              numeric;

-- BLOCK 5: N2O emissions
alter table annual_monitoring_results
    add column if not exists total_n2o_emissions_m_tonnes  numeric,
    add column if not exists n2o_between_ms_ports_m_tonnes numeric,
    add column if not exists n2o_from_ms_ports_m_tonnes    numeric,
    add column if not exists n2o_to_ms_ports_m_tonnes      numeric,
    add column if not exists n2o_at_berth_m_tonnes         numeric,
    add column if not exists n2o_at_ms_ports_m_tonnes      numeric,
    add column if not exists n2o_on_laden_m_tonnes         numeric,
    add column if not exists n2o_passenger_m_tonnes        numeric,
    add column if not exists n2o_freight_m_tonnes          numeric,
    add column if not exists n2o_ets_m_tonnes              numeric;

-- BLOCK 6: CO2eq emissions
alter table annual_monitoring_results
    add column if not exists total_co2eq_emissions_m_tonnes  numeric,
    add column if not exists co2eq_between_ms_ports_m_tonnes numeric,
    add column if not exists co2eq_from_ms_ports_m_tonnes    numeric,
    add column if not exists co2eq_to_ms_ports_m_tonnes      numeric,
    add column if not exists co2eq_at_berth_m_tonnes         numeric,
    add column if not exists co2eq_at_ms_ports_m_tonnes      numeric,
    add column if not exists co2eq_on_laden_m_tonnes         numeric,
    add column if not exists co2eq_passenger_m_tonnes        numeric,
    add column if not exists co2eq_freight_m_tonnes          numeric,
    add column if not exists co2eq_ets_m_tonnes              numeric,
    add column if not exists co2eq_derogation_m_tonnes       numeric;

-- BLOCK 7: distance/time through ice (moved from VR to AMR in 2024)
alter table annual_monitoring_results
    add column if not exists distance_through_ice_n_miles        numeric,
    add column if not exists time_spent_at_sea_through_ice_hours numeric;

-- BLOCK 8: efficiency on-laden variants + time-based (2024)
alter table annual_monitoring_results
    add column if not exists avg_fuel_per_distance_on_laden_kg_n_mile  numeric,
    add column if not exists avg_fuel_per_transport_mass_on_laden_g    numeric,
    add column if not exists avg_fuel_per_transport_volume_on_laden_g  numeric,
    add column if not exists avg_fuel_per_transport_dwt_on_laden_g     numeric,
    add column if not exists avg_fuel_per_transport_pax_on_laden_g     numeric,
    add column if not exists avg_fuel_per_transport_freight_on_laden_g numeric,
    add column if not exists avg_fuel_per_time_at_sea_m_tonnes_hour    numeric,
    add column if not exists avg_co2_per_distance_on_laden_kg_n_mile   numeric,
    add column if not exists avg_co2_per_transport_mass_on_laden_g     numeric,
    add column if not exists avg_co2_per_transport_volume_on_laden_g   numeric,
    add column if not exists avg_co2_per_transport_dwt_on_laden_g      numeric,
    add column if not exists avg_co2_per_transport_pax_on_laden_g      numeric,
    add column if not exists avg_co2_per_transport_freight_on_laden_g  numeric,
    add column if not exists avg_co2_per_time_at_sea_m_tonnes_hour     numeric;

-- BLOCK 9: CO2eq efficiency metrics (2024)
alter table annual_monitoring_results
    add column if not exists avg_co2eq_per_distance_kg_n_mile           numeric,
    add column if not exists avg_co2eq_per_distance_on_laden_kg_n_mile  numeric,
    add column if not exists avg_co2eq_per_transport_mass_g             numeric,
    add column if not exists avg_co2eq_per_transport_mass_on_laden_g    numeric,
    add column if not exists avg_co2eq_per_transport_volume_g           numeric,
    add column if not exists avg_co2eq_per_transport_volume_on_laden_g  numeric,
    add column if not exists avg_co2eq_per_transport_dwt_g              numeric,
    add column if not exists avg_co2eq_per_transport_dwt_on_laden_g     numeric,
    add column if not exists avg_co2eq_per_transport_pax_g              numeric,
    add column if not exists avg_co2eq_per_transport_pax_on_laden_g     numeric,
    add column if not exists avg_co2eq_per_transport_freight_g          numeric,
    add column if not exists avg_co2eq_per_transport_freight_on_laden_g numeric,
    add column if not exists avg_co2eq_per_time_at_sea                  numeric;

-- BLOCK 10: voluntary data now embedded in AMR for 2024
alter table annual_monitoring_results
    add column if not exists additional_info               text,
    add column if not exists avg_cargo_density_m_tonnes_m3 numeric;

-- BLOCK 11: data_versions (safe to re-run)
create table if not exists data_versions (
    year        integer primary key,
    file_hash   text    not null,
    imported_at timestamptz not null default now()
);
