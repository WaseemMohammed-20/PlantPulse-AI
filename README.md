# PlantPulse AI

PlantPulse AI is a portfolio project for a manufacturing intelligence and
analytics platform. It is intended to help manufacturing teams understand
production performance, investigate machine downtime, spot quality issues, and
make better operational decisions.

> **Data notice:** All manufacturing data used by this project will be
> simulated. The application will identify simulated data clearly and will not
> present hardcoded sample metrics as calculated production results.

## Project goals

- Build a production-style application with a clear separation between its
  frontend, API, data, and analytics.
- Calculate operational metrics from their underlying data.
- Demonstrate practical skills in Python, SQL, Pandas, React, and data
  visualization.
- Keep configuration out of source code and make the project suitable for
  public hosting and eventual deployment.

## Planned technology stack

| Area | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite |
| UI | Tailwind CSS |
| API | Python, FastAPI |
| Database | PostgreSQL |
| Analytics | SQL, Python, Pandas |
| Business intelligence | Apache Superset |
| Containerization | Docker, Docker Compose |
| Version control | Git, GitHub |

## Planned features

- A plant overview with production and operational performance indicators.
- Production analysis with trends over time.
- Machine downtime analysis, including downtime duration and reason breakdowns.
- Quality analysis for defects and scrap.
- Validated API endpoints backed by PostgreSQL data.
- Analytics calculated from simulated source data rather than hardcoded API
  responses.
- An optional Apache Superset layer for business intelligence exploration.

Features are planned, not implemented yet.

## Proposed project structure

```text
plantpulse-ai/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routes
│   │   ├── core/            # Configuration and shared application setup
│   │   ├── db/              # Database connection and session management
│   │   ├── models/          # Database models
│   │   ├── schemas/         # Request and response validation schemas
│   │   └── services/        # Business logic and analytics
│   └── tests/
├── data/
│   ├── raw/                 # Versioned simulated source fixtures, if useful
│   └── generated/           # Locally generated data (not committed)
├── docs/
├── frontend/
│   ├── public/
│   └── src/
│       ├── components/
│       ├── features/
│       ├── lib/
│       ├── pages/
│       └── types/
├── infra/
│   └── superset/            # Superset configuration, if needed
├── .env.example
├── .gitignore
└── README.md
```

This is a proposed layout, not a claim that these directories or application
features already exist. Add components incrementally as they become necessary.

## Development roadmap

1. Establish the repository foundation and agree on the project structure.
2. Design the manufacturing data model and create clearly labeled simulated
   data.
3. Build and test the FastAPI service and PostgreSQL integration.
4. Add frontend pages and connect them to the API.
5. Add analytics and visualizations, calculating metrics from the data.
6. Add Docker Compose and, if useful, Apache Superset.

## Configuration

Copy `.env.example` to `.env` when application configuration is introduced,
then fill in local values. Do not commit `.env` or put real credentials in
`.env.example`.

## Verify the foundation

No application server or test suite exists yet. From the project folder, these
commands check the foundation files, confirm that local secrets are ignored,
and display the development-tool versions:

```powershell
Get-ChildItem -Force
Get-Content .\README.md
git check-ignore -v .env
python --version
node --version
npm --version
docker --version
docker compose version
```

At this foundation stage, Git, Python, Node.js/npm, and Docker with Compose are
useful prerequisites; no project dependencies need to be installed yet.
