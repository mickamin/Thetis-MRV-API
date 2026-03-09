# THETIS-MRV API

I'm doing research on shipping GHG emissions and kept having to download Excel files from EMSA's THETIS-MRV portal every time I needed data. Seven years worth, inconsistent column names across years, manually filtering things. It was doing my head in so I just built an API around it.

~87k records across 2018-2024. CO₂, CH₄, N₂O, fuel consumption, efficiency metrics, verifier info. Data syncs automatically every Monday from EMSA's portal.

**Live at [thetis-mrv-api.vercel.app](https://thetis-mrv-api.vercel.app) — docs at [/docs](https://thetis-mrv-api.vercel.app/docs)**

## Endpoints

| Endpoint | Description |
|---|---|
| `GET /years` | Available years + ship counts |
| `GET /ship_types` | Ship types with record counts |
| `GET /fleet` | Fleet-wide totals per year |
| `GET /aggregate?group_by=ship_type\|year\|flag\|ice_class` | Aggregated emissions stats |
| `GET /ships` | Filter by year, ship type, flag, name |
| `GET /ships/{imo}` | Full history for a ship |
| `GET /ships/{imo}/emissions` | Emissions time series |
| `GET /ships/{imo}/efficiency` | Efficiency metrics time series |
| `GET /ships/{imo}/{year}` | Full record for a specific ship/year |

## Stack

- Data: EMSA THETIS-MRV portal
- DB: Supabase (PostgreSQL)
- API: FastAPI on Vercel
- Sync: GitHub Actions (weekly)

## Run locally

```bash
pip install -r requirements.txt
uvicorn api.index:app --reload
```

Needs `DATABASE_URL` in `.env`.
