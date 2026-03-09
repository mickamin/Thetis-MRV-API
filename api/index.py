import os
from contextlib import contextmanager
from typing import Optional

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(
    title="THETIS-MRV API",
    description="EU ship GHG emissions data 2018–2024",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

VALID_GROUP_BY = {"ship_type", "year", "flag", "ice_class"}


@contextmanager
def get_conn():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        yield conn
    finally:
        conn.close()


def q(conn, sql, params=()):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def q1(conn, sql, params=()):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        r = cur.fetchone()
        return dict(r) if r else None


def strip_pk(row):
    if row:
        row.pop("imo_number", None)
        row.pop("reporting_period", None)
    return row


@app.get("/")
def root():
    return {
        "name": "THETIS-MRV API",
        "version": "1.0.0",
        "description": "EU ship GHG emissions data 2018–2024",
        "docs": "/docs",
        "endpoints": [
            "GET /years",
            "GET /ship_types",
            "GET /fleet",
            "GET /aggregate",
            "GET /ships",
            "GET /ships/{imo}",
            "GET /ships/{imo}/emissions",
            "GET /ships/{imo}/efficiency",
            "GET /ships/{imo}/{year}",
        ],
    }


@app.get("/years")
def get_years():
    with get_conn() as conn:
        return q(conn, """
            select dv.year, dv.imported_at,
                   count(s.imo_number) as ship_count
            from data_versions dv
            left join ship s on s.reporting_period = dv.year
            group by dv.year, dv.imported_at
            order by dv.year
        """)


@app.get("/ship_types")
def get_ship_types(year: Optional[int] = None):
    conditions, params = [], []
    if year:
        conditions.append("reporting_period = %s")
        params.append(year)
    where = ("where " + " and ".join(conditions)) if conditions else ""
    with get_conn() as conn:
        return q(conn, f"""
            select ship_type,
                   count(distinct imo_number) as unique_ships,
                   count(*) as total_records
            from ship
            {where}
            group by ship_type
            order by unique_ships desc
        """, params)


@app.get("/fleet")
def fleet_summary(ship_type: Optional[str] = None):
    conditions, params = [], []
    if ship_type:
        conditions.append("s.ship_type ilike %s")
        params.append(f"%{ship_type}%")
    where = ("where " + " and ".join(conditions)) if conditions else ""
    with get_conn() as conn:
        return q(conn, f"""
            select
                s.reporting_period as year,
                count(distinct s.imo_number) as ship_count,
                round(sum(amr.total_co2_emissions_m_tonnes)::numeric, 2) as total_co2_m_tonnes,
                round(avg(amr.total_co2_emissions_m_tonnes)::numeric, 2) as avg_co2_per_ship_m_tonnes,
                round(sum(amr.total_fuel_consumption_m_tonnes)::numeric, 2) as total_fuel_m_tonnes,
                round(avg(amr.total_fuel_consumption_m_tonnes)::numeric, 2) as avg_fuel_per_ship_m_tonnes,
                round(sum(amr.total_ch4_emissions_m_tonnes)::numeric, 4) as total_ch4_m_tonnes,
                round(sum(amr.total_n2o_emissions_m_tonnes)::numeric, 4) as total_n2o_m_tonnes,
                round(sum(amr.total_co2eq_emissions_m_tonnes)::numeric, 2) as total_co2eq_m_tonnes,
                round(avg(amr.avg_co2_per_distance_kg_n_mile)::numeric, 4) as fleet_avg_co2_per_distance,
                round(avg(amr.avg_fuel_per_distance_kg_n_mile)::numeric, 4) as fleet_avg_fuel_per_distance
            from ship s
            join annual_monitoring_results amr
                on amr.imo_number = s.imo_number
                and amr.reporting_period = s.reporting_period
            {where}
            group by s.reporting_period
            order by s.reporting_period
        """, params)


@app.get("/aggregate")
def aggregate(
    group_by: str = Query("ship_type", description="ship_type | year | flag | ice_class"),
    year: Optional[int] = None,
    ship_type: Optional[str] = None,
):
    if group_by not in VALID_GROUP_BY:
        raise HTTPException(400, f"group_by must be one of: {', '.join(VALID_GROUP_BY)}")

    group_col = {
        "ship_type": "s.ship_type",
        "year": "s.reporting_period",
        "flag": "s.port_of_registry",
        "ice_class": "s.ice_class",
    }[group_by]

    conditions, params = [], []
    if year:
        conditions.append("s.reporting_period = %s")
        params.append(year)
    if ship_type:
        conditions.append("s.ship_type ilike %s")
        params.append(f"%{ship_type}%")
    where = ("where " + " and ".join(conditions)) if conditions else ""

    with get_conn() as conn:
        return q(conn, f"""
            select
                {group_col} as group_value,
                count(distinct s.imo_number) as ship_count,
                round(avg(amr.total_co2_emissions_m_tonnes)::numeric, 2) as avg_co2_m_tonnes,
                round(sum(amr.total_co2_emissions_m_tonnes)::numeric, 2) as total_co2_m_tonnes,
                round(avg(amr.total_fuel_consumption_m_tonnes)::numeric, 2) as avg_fuel_m_tonnes,
                round(sum(amr.total_fuel_consumption_m_tonnes)::numeric, 2) as total_fuel_m_tonnes,
                round(avg(amr.annual_total_time_spent_at_sea_hours)::numeric, 1) as avg_time_at_sea_hours,
                round(avg(amr.avg_co2_per_distance_kg_n_mile)::numeric, 4) as avg_co2_per_distance,
                round(avg(amr.avg_fuel_per_distance_kg_n_mile)::numeric, 4) as avg_fuel_per_distance,
                round(sum(amr.total_ch4_emissions_m_tonnes)::numeric, 4) as total_ch4_m_tonnes,
                round(sum(amr.total_n2o_emissions_m_tonnes)::numeric, 4) as total_n2o_m_tonnes,
                round(sum(amr.total_co2eq_emissions_m_tonnes)::numeric, 2) as total_co2eq_m_tonnes
            from ship s
            join annual_monitoring_results amr
                on amr.imo_number = s.imo_number
                and amr.reporting_period = s.reporting_period
            {where}
            group by {group_col}
            order by total_co2_m_tonnes desc nulls last
        """, params)


@app.get("/ships")
def list_ships(
    year: Optional[int] = None,
    ship_type: Optional[str] = None,
    flag: Optional[str] = None,
    ice_class: Optional[str] = None,
    name: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    conditions, params = [], []
    if year:
        conditions.append("s.reporting_period = %s")
        params.append(year)
    if ship_type:
        conditions.append("s.ship_type ilike %s")
        params.append(f"%{ship_type}%")
    if flag:
        conditions.append("s.port_of_registry ilike %s")
        params.append(f"%{flag}%")
    if ice_class:
        conditions.append("s.ice_class ilike %s")
        params.append(f"%{ice_class}%")
    if name:
        conditions.append("s.name ilike %s")
        params.append(f"%{name}%")
    where = ("where " + " and ".join(conditions)) if conditions else ""
    params += [limit, offset]

    with get_conn() as conn:
        data = q(conn, f"""
            select s.imo_number, s.reporting_period as year, s.name, s.ship_type,
                   s.technical_efficiency, s.port_of_registry, s.home_port, s.ice_class,
                   amr.total_co2_emissions_m_tonnes,
                   amr.total_fuel_consumption_m_tonnes,
                   amr.annual_total_time_spent_at_sea_hours
            from ship s
            left join annual_monitoring_results amr
                on amr.imo_number = s.imo_number
                and amr.reporting_period = s.reporting_period
            {where}
            order by s.imo_number, s.reporting_period
            limit %s offset %s
        """, params)
        return {"count": len(data), "offset": offset, "results": data}


@app.get("/ships/{imo}/emissions")
def get_ship_emissions(imo: int):
    with get_conn() as conn:
        ship = q1(conn, "select name, ship_type from ship where imo_number = %s limit 1", (imo,))
        if not ship:
            raise HTTPException(404, "Ship not found")
        data = q(conn, """
            select
                s.reporting_period as year,
                amr.total_fuel_consumption_m_tonnes,
                amr.fuel_consumption_on_laden_m_tonnes,
                amr.total_co2_emissions_m_tonnes,
                amr.total_ch4_emissions_m_tonnes,
                amr.total_n2o_emissions_m_tonnes,
                amr.total_co2eq_emissions_m_tonnes,
                amr.annual_total_time_spent_at_sea_hours,
                amr.co2_ets_m_tonnes,
                amr.co2_between_ms_ports_m_tonnes,
                amr.co2_from_ms_ports_m_tonnes,
                amr.co2_to_ms_ports_m_tonnes,
                amr.co2_at_berth_m_tonnes,
                amr.co2_on_laden_m_tonnes,
                amr.ch4_ets_m_tonnes,
                amr.n2o_ets_m_tonnes,
                amr.co2eq_ets_m_tonnes,
                amr.distance_through_ice_n_miles,
                amr.time_spent_at_sea_through_ice_hours
            from ship s
            join annual_monitoring_results amr
                on amr.imo_number = s.imo_number
                and amr.reporting_period = s.reporting_period
            where s.imo_number = %s
            order by s.reporting_period
        """, (imo,))
        return {"imo_number": imo, "name": ship["name"], "ship_type": ship["ship_type"], "series": data}


@app.get("/ships/{imo}/efficiency")
def get_ship_efficiency(imo: int):
    with get_conn() as conn:
        ship = q1(conn, "select name, ship_type, technical_efficiency from ship where imo_number = %s limit 1", (imo,))
        if not ship:
            raise HTTPException(404, "Ship not found")
        data = q(conn, """
            select
                s.reporting_period as year,
                s.technical_efficiency,
                amr.avg_fuel_per_distance_kg_n_mile,
                amr.avg_fuel_per_distance_on_laden_kg_n_mile,
                amr.avg_fuel_per_transport_mass_g,
                amr.avg_fuel_per_transport_mass_on_laden_g,
                amr.avg_fuel_per_transport_dwt_g,
                amr.avg_fuel_per_transport_dwt_on_laden_g,
                amr.avg_fuel_per_transport_pax_g,
                amr.avg_fuel_per_transport_pax_on_laden_g,
                amr.avg_fuel_per_transport_freight_g,
                amr.avg_fuel_per_transport_freight_on_laden_g,
                amr.avg_fuel_per_time_at_sea_m_tonnes_hour,
                amr.avg_co2_per_distance_kg_n_mile,
                amr.avg_co2_per_distance_on_laden_kg_n_mile,
                amr.avg_co2_per_transport_mass_g,
                amr.avg_co2_per_transport_dwt_g,
                amr.avg_co2_per_transport_pax_g,
                amr.avg_co2_per_transport_freight_g,
                amr.avg_co2_per_time_at_sea_m_tonnes_hour,
                amr.avg_co2eq_per_distance_kg_n_mile,
                amr.avg_co2eq_per_distance_on_laden_kg_n_mile,
                amr.avg_co2eq_per_time_at_sea,
                vr.fuel_per_distance_on_laden_kg_n_mile as vr_fuel_per_distance_on_laden,
                vr.co2_per_distance_on_laden_kg_n_mile as vr_co2_per_distance_on_laden
            from ship s
            join annual_monitoring_results amr
                on amr.imo_number = s.imo_number
                and amr.reporting_period = s.reporting_period
            left join voluntary_reporting vr
                on vr.imo_number = s.imo_number
                and vr.reporting_period = s.reporting_period
            where s.imo_number = %s
            order by s.reporting_period
        """, (imo,))
        return {
            "imo_number": imo,
            "name": ship["name"],
            "ship_type": ship["ship_type"],
            "technical_efficiency": ship["technical_efficiency"],
            "series": data,
        }


@app.get("/ships/{imo}/{year}")
def get_ship_year(imo: int, year: int):
    with get_conn() as conn:
        ship = q1(conn, "select * from ship where imo_number = %s and reporting_period = %s", (imo, year))
        if not ship:
            raise HTTPException(404, "Record not found")
        amr = strip_pk(q1(conn, "select * from annual_monitoring_results where imo_number = %s and reporting_period = %s", (imo, year)))
        vr = strip_pk(q1(conn, "select * from voluntary_reporting where imo_number = %s and reporting_period = %s", (imo, year)))
        doc = strip_pk(q1(conn, "select * from doc where imo_number = %s and reporting_period = %s", (imo, year)))
        ver = strip_pk(q1(conn, "select * from verifier where imo_number = %s and reporting_period = %s", (imo, year)))
        mm = strip_pk(q1(conn, "select * from monitoring_methods where imo_number = %s and reporting_period = %s", (imo, year)))
        co = strip_pk(q1(conn, "select * from company where imo_number = %s and reporting_period = %s", (imo, year)))
        return {
            "imo_number": imo,
            "year": year,
            "name": ship["name"],
            "ship_type": ship["ship_type"],
            "technical_efficiency": ship["technical_efficiency"],
            "port_of_registry": ship["port_of_registry"],
            "home_port": ship["home_port"],
            "ice_class": ship["ice_class"],
            "company": co,
            "doc": doc,
            "verifier": ver,
            "monitoring_methods": mm,
            "annual_monitoring_results": amr,
            "voluntary_reporting": vr,
        }


@app.get("/ships/{imo}")
def get_ship(imo: int):
    with get_conn() as conn:
        ships = q(conn, "select * from ship where imo_number = %s order by reporting_period", (imo,))
        if not ships:
            raise HTTPException(404, "Ship not found")

        amr_map = {r["reporting_period"]: strip_pk(r) for r in q(conn, "select * from annual_monitoring_results where imo_number = %s", (imo,))}
        vr_map = {r["reporting_period"]: strip_pk(r) for r in q(conn, "select * from voluntary_reporting where imo_number = %s", (imo,))}
        doc_map = {r["reporting_period"]: strip_pk(r) for r in q(conn, "select * from doc where imo_number = %s", (imo,))}
        ver_map = {r["reporting_period"]: strip_pk(r) for r in q(conn, "select * from verifier where imo_number = %s", (imo,))}
        mm_map = {r["reporting_period"]: strip_pk(r) for r in q(conn, "select * from monitoring_methods where imo_number = %s", (imo,))}
        co_map = {r["reporting_period"]: strip_pk(r) for r in q(conn, "select * from company where imo_number = %s", (imo,))}

        records = []
        for ship in ships:
            year = ship["reporting_period"]
            records.append({
                "year": year,
                "name": ship["name"],
                "ship_type": ship["ship_type"],
                "technical_efficiency": ship["technical_efficiency"],
                "port_of_registry": ship["port_of_registry"],
                "home_port": ship["home_port"],
                "ice_class": ship["ice_class"],
                "company": co_map.get(year),
                "doc": doc_map.get(year),
                "verifier": ver_map.get(year),
                "monitoring_methods": mm_map.get(year),
                "annual_monitoring_results": amr_map.get(year),
                "voluntary_reporting": vr_map.get(year),
            })

        return {"imo_number": imo, "records": records}
