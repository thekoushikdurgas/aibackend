<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

## FastAPI and Streamlit Combined File Structure with Best Practices

Here's a comprehensive file structure for a production-ready FastAPI and Streamlit application with best practices:[^1][^2][^3]

### Recommended Monorepo Structure

```
project-root/
├── backend/                          # FastAPI application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app entry point
│   │   ├── config.py                 # Configuration settings
│   │   ├── dependencies.py           # Shared dependencies
│   │   ├── api/                      # API routes
│   │   │   ├── __init__.py
│   │   │   ├── v1/                   # API versioning
│   │   │   │   ├── __init__.py
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── users.py
│   │   │   │   │   ├── items.py
│   │   │   │   │   └── auth.py
│   │   │   │   └── router.py         # Route aggregator
│   │   ├── core/                     # Core business logic
│   │   │   ├── __init__.py
│   │   │   ├── security.py
│   │   │   └── utils.py
│   │   ├── db/                       # Database related
│   │   │   ├── __init__.py
│   │   │   ├── database.py           # DB connection
│   │   │   ├── models.py             # SQLAlchemy models
│   │   │   └── crud.py               # CRUD operations
│   │   ├── schemas/                  # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── item.py
│   │   └── services/                 # Business logic layer
│   │       ├── __init__.py
│   │       ├── ml_service.py
│   │       └── data_service.py
│   ├── tests/                        # Backend tests
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── test_api.py
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                         # Streamlit application
│   ├── app.py                        # Main Streamlit entry
│   ├── pages/                        # Multi-page app
│   │   ├── 1_📊_Dashboard.py
│   │   ├── 2_📈_Analytics.py
│   │   └── 3_⚙️_Settings.py
│   ├── components/                   # Reusable UI components
│   │   ├── __init__.py
│   │   ├── charts.py
│   │   ├── forms.py
│   │   └── tables.py
│   ├── utils/                        # Frontend utilities
│   │   ├── __init__.py
│   │   ├── api_client.py             # API communication
│   │   └── helpers.py
│   ├── config/                       # Frontend config
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── assets/                       # Static assets
│   │   ├── images/
│   │   └── styles/
│   │       └── custom.css
│   ├── tests/                        # Frontend tests
│   │   └── test_components.py
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .streamlit/
│   │   └── config.toml               # Streamlit config
│   └── .env.example
│
├── shared/                           # Shared code between both
│   ├── __init__.py
│   ├── models/                       # Shared Pydantic models
│   │   ├── __init__.py
│   │   └── common.py
│   └── constants.py                  # Shared constants
│
├── scripts/                          # Utility scripts
│   ├── init_db.py
│   └── seed_data.py
│
├── docker-compose.yml                # Multi-container orchestration
├── docker-compose.dev.yml            # Development overrides
├── .gitignore
├── Makefile                          # Common commands
├── README.md
└── pyproject.toml                    # Optional: monorepo config
```

### Key File Contents

**docker-compose.yml**:[^4][^1]

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: fastapi-backend
    ports:
      - '8000:8000'
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --reload

  frontend:
    build: ./frontend
    container_name: streamlit-frontend
    ports:
      - '8501:8501'
    environment:
      - API_BASE_URL=http://backend:8000
    volumes:
      - ./frontend:/app
    depends_on:
      - backend
    command: streamlit run app.py
```

**backend/Dockerfile**:[^3]

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**frontend/utils/api_client.py**:

```python
import httpx
import os
from typing import Optional

class APIClient:
    def __init__(self):
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)

    def get(self, endpoint: str, params: Optional[dict] = None):
        response = self.client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: dict):
        response = self.client.post(endpoint, json=data)
        response.raise_for_status()
        return response.json()
```

### Best Practices Summary

**Separation of Concerns**: Keep backend and frontend completely independent with clear interfaces. This enables independent scaling and deployment.[^5][^2]

**Shared Models**: Use a `shared/` directory for Pydantic models used by both services. This ensures type consistency across the stack.[^2]

**Environment Configuration**: Use `.env` files for local development and environment variables for production. Never commit secrets to version control.[^1]

**Docker Multi-Stage Builds**: Use multi-stage builds to reduce image sizes and improve security. Keep development and production configurations separate.[^4][^3]

**API Versioning**: Structure FastAPI routes with versioning (`api/v1/`) to support backward compatibility.[^6][^5]

**Component Reusability**: Extract reusable Streamlit components into separate modules to avoid duplication.[^7][^8]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^9]</span>

<div align="center">⁂</div>

[^1]: https://tsourget.fr/posts/other/create-your-own-app/

[^2]: https://sqr-075.lsst.io

[^3]: https://github.com/VildMedPap/containerized-streamlit-and-fastapi-app

[^4]: https://blog.jcharistech.com/2022/08/05/deploying-streamlit-and-fastapi-apps-using-docker-and-docker-compose/

[^5]: https://fastapi.tiangolo.com/tutorial/bigger-applications/

[^6]: https://sociosclubiste.com/blog/best-fastapi-folder-structure-a

[^7]: https://discuss.streamlit.io/t/streamlit-project-folder-structure-for-medium-sized-apps/5272

[^8]: https://www.youtube.com/watch?v=MdjMC0PLJ2s

[^9]: http://tst.stu.cn.ua/article/view/323733

[^10]: https://ieeexplore.ieee.org/document/11053090/

[^11]: https://onlinelibrary.wiley.com/doi/10.1002/asi.10174

[^12]: https://arxiv.org/abs/2510.08850

[^13]: https://dl.acm.org/doi/10.1145/3746027.3761840

[^14]: https://riojournal.com/article/93940/

[^15]: https://www.protocols.io/view/photographing-agave-for-3d-reconstruction-using-st-bm67k9hn

[^16]: https://archive.nyu.edu/handle/2451/63333

[^17]: https://dl.acm.org/doi/10.1145/1056808.1056952

[^18]: https://www.repository.cam.ac.uk/handle/1810/288349

[^19]: http://arxiv.org/pdf/2410.10513.pdf

[^20]: https://joss.theoj.org/papers/10.21105/joss.05350.pdf

[^21]: https://zenodo.org/record/3387092/files/main.pdf

[^22]: https://www.mdpi.com/2306-5729/9/2/24/pdf?version=1706266221

[^23]: https://www.frontiersin.org/articles/10.3389/fgene.2022.868015/pdf

[^24]: https://www.mdpi.com/2078-2489/11/2/108/pdf

[^25]: http://arxiv.org/pdf/2411.13189.pdf

[^26]: https://arxiv.org/pdf/1309.0238.pdf

[^27]: https://pybit.es/articles/my-experience-building-a-fastapi-streamlit-app/

[^28]: https://github.com/jtayl222/fastapi_streamlit_example
