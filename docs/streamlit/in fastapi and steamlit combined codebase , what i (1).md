<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# in fastapi and steamlit combined codebase , what is the best practices

Excellent! I found comprehensive resources on this topic. Let me create a detailed guide on best practices for FastAPI + Streamlit combined codebases:

## Best Practices for FastAPI + Streamlit Combined Codebase

Based on current production patterns and architectural best practices, here's a comprehensive guide:

### **1. Architecture \& Separation of Concerns**

**Two-Tier Architecture is Essential**[^1]

- **FastAPI (Backend)**: High-performance API layer for business logic, data processing, ML models
- **Streamlit (Frontend)**: Interactive UI layer for visualization and user interaction
- **Benefits**:
  - Changes to frontend don't affect backend
  - Independently scalable components
  - Reusable backend for multiple frontends
  - Better security (expose only frontend to internet)

**Project Structure**[^2]

```
streamlit-fastapi-app/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── requirements.txt
│   ├── Dockerfile
│   └── app/
│       ├── routes/          # API endpoints
│       ├── models/          # Pydantic models
│       ├── services/        # Business logic
│       └── config.py        # Configuration
│
├── frontend/
│   ├── app.py               # Streamlit main app
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pages/               # Multi-page Streamlit apps
│       ├── page1.py
│       └── page2.py
│
├── docker-compose.yml       # Orchestration
├── .env.default             # Environment template
└── .env                      # Actual secrets (gitignored)
```

---

### **2. Configuration Management**

**Use Environment Variables Securely**[^3][^4]

```python
# backend/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_URL: str
    DATABASE_URL: str
    API_KEY: str
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()

# Get settings across backend
def get_settings() -> Settings:
    return settings
```

**Frontend Configuration**[^3]

```python
# frontend/config.py
import streamlit as st
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_URL: str

    class Config:
        env_file = ".env"

def load_settings() -> Settings:
    if "database" in st.secrets:  # Streamlit Cloud
        return Settings(API_URL=st.secrets["api"]["API_URL"])
    return Settings()  # Local/dev uses .env file

settings = load_settings()
```

**Never** store credentials in code or git repository. Always use `.env` file (gitignored).

---

### **3. Backend Development (FastAPI)**

**API Design Best Practices**[^3]

```python
# backend/app/routes/data.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

router = APIRouter(prefix="/api/v1/data", tags=["data"])

@router.get("/items")
async def get_items(skip: int = 0, limit: int = 10):
    """Retrieve items with pagination"""
    # Implementation
    pass

@router.post("/items")
async def create_item(item: ItemSchema):
    """Create new item"""
    # Implementation
    pass

@router.get("/items/{item_id}")
async def get_item(item_id: int):
    """Get specific item by ID"""
    # Implementation
    pass
```

**Enable CORS for Streamlit**[^4][^3]

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # Local Streamlit
        "https://your-streamlit-app.streamlit.app",  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Your routes here
```

**Use Async for Performance**[^5]

```python
# Leverage asyncio for background tasks
import asyncio
from fastapi import BackgroundTasks

@app.post("/process")
async def process_data(data: DataSchema, background_tasks: BackgroundTasks):
    # Return quick response
    result = await quick_process(data)

    # Run expensive operation in background
    background_tasks.add_task(expensive_operation, data)

    return {"status": "processing", "result": result}
```

---

### **4. Frontend Development (Streamlit)**

**Session State Management**[^6]

```python
# frontend/app.py
import streamlit as st
import httpx
from config import settings

# Initialize session state
if "api_connected" not in st.session_state:
    st.session_state.api_connected = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# Session state persists throughout app lifecycle
# Use it for: API clients, cached data, user preferences
```

**API Client with Error Handling**[^6][^3]

```python
# frontend/services/api_client.py
import httpx
import streamlit as st
from config import settings

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.timeout = 60  # Increase timeout for slow operations

    async def get_items(self):
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/items"
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            st.error(f"API Error: {str(e)}")
            return None

    async def post_item(self, item_data: dict):
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/items",
                    json=item_data,
                    headers={"Authorization": f"Bearer {st.session_state.token}"}
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            st.error(f"Failed to create item: {str(e)}")
            return None

# Initialize client
api_client = APIClient(settings.API_URL)
```

**Page Structure (Multi-page Apps)**[^6]

```
frontend/
├── app.py              # Main entry point
└── pages/
    ├── 01_home.py
    ├── 02_dashboard.py
    ├── 03_settings.py
    └── utils/
        ├── api_client.py
        └── helpers.py
```

---

### **5. Docker \& Containerization**

**Backend Dockerfile**[^4][^5]

```dockerfile
# backend/Dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile**[^5]

```dockerfile
# frontend/Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

# Configure Streamlit
RUN mkdir -p ~/.streamlit && \
    echo "[server]" > ~/.streamlit/config.toml && \
    echo "headless = true" >> ~/.streamlit/config.toml && \
    echo "port = 8501" >> ~/.streamlit/config.toml

CMD ["streamlit", "run", "app.py"]
```

**Docker Compose Orchestration**[^7][^5]

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build:
      context: backend
      dockerfile: Dockerfile
    container_name: fastapi-backend
    ports:
      - '8000:8000'
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - API_KEY=${API_KEY}
      - DEBUG=${DEBUG}
    networks:
      - app-network
    volumes:
      - ./backend:/app # Hot reload during development
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: frontend
      dockerfile: Dockerfile
    container_name: streamlit-frontend
    depends_on:
      - backend
    ports:
      - '8501:8501'
    environment:
      - API_URL=http://backend:8000 # Use service name in Docker network
    networks:
      - app-network
    volumes:
      - ./frontend:/app

  # Optional: PostgreSQL database
  postgres:
    image: postgres:15-alpine
    container_name: postgres-db
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    ports:
      - '5432:5432'
    networks:
      - app-network
    volumes:
      - postgres_data:/var/lib/postgresql/data

networks:
  app-network:
    driver: bridge

volumes:
  postgres_data:
```

**Key Points**:

- Use service name (`http://backend:8000`) for internal communication
- Set `depends_on` to ensure backend starts first
- Use volumes for hot reloading during development
- Share data via volumes if needed

---

### **6. Data Validation**

**Pydantic Models**[^4]

```python
# backend/app/models/schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    price: float = Field(..., gt=0)

    @validator('name')
    def name_cannot_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()

class Item(ItemCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # For ORM models
```

**Data Validation in Streamlit**[^4]

```python
# frontend/app.py
import streamlit as st

st.title("Create Item")

with st.form("item_form"):
    name = st.text_input("Item Name", max_chars=100)
    price = st.number_input("Price", min_value=0.01, step=0.01)

    submitted = st.form_submit_button("Create")

    if submitted:
        # Client-side validation
        if not name or not name.strip():
            st.error("Name cannot be empty")
        elif price <= 0:
            st.error("Price must be positive")
        else:
            # Send to API (server-side validation also happens)
            result = await api_client.post_item({
                "name": name,
                "price": price
            })
            if result:
                st.success("Item created!")
```

---

### **7. Authentication \& Security**

**JWT Authentication**[^2]

```python
# backend/app/security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredential
import jwt

security = HTTPBearer()

def verify_token(credentials: HTTPAuthCredential = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, "YOUR_SECRET", algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401)
        return user_id
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401)

# Use in routes
@app.get("/secured")
def secured_data(user_id: int = Depends(verify_token)):
    return {"message": "You are authorized!"}
```

**Streamlit Frontend Auth**[^2]

```python
# frontend/app.py
import streamlit as st
import httpx

if "token" not in st.session_state:
    st.session_state.token = None

# Login section
if not st.session_state.token:
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        # Call backend auth endpoint
        response = requests.post(
            f"{API_URL}/auth/login",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            st.session_state.token = response.json()["access_token"]
            st.success("Logged in!")
        else:
            st.error("Invalid credentials")
else:
    # Authenticated endpoints
    st.sidebar.button("Logout", on_click=lambda: st.session_state.clear())
```

---

### **8. Error Handling \& Logging**

**Backend Logging**[^4]

```python
# backend/main.py
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
file_handler = RotatingFileHandler('app.log', maxBytes=10485760, backupCount=5)
logger.addHandler(file_handler)

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

**Frontend Error Handling**[^6]

```python
# frontend/app.py
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    response = await api_client.get_items()
except Exception as e:
    logger.error(f"API call failed: {str(e)}")
    st.error("Failed to load data")
```

---

### **9. Deployment Strategies**

**Local Development**[^5]

```bash
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:8501
```

**Production Deployment**[^8]

1. **Backend**: Deploy to Fly.io, Railway, or AWS ECS
2. **Frontend**: Deploy to Streamlit Cloud or separate server
3. **Database**: Use managed PostgreSQL (AWS RDS, Supabase, etc.)

**Streamlit Cloud + External FastAPI**[^3]

```python
# .streamlit/secrets.toml in Streamlit Cloud
[api]
API_URL = "https://your-fastapi-backend.com"
```

---

### **10. Performance Optimization**

**Caching in Streamlit**[^3]

```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_data_from_api():
    response = requests.get(f"{API_URL}/items")
    return response.json()
```

**Async Operations in FastAPI**[^5]

```python
@app.post("/process-batch")
async def process_batch(items: List[ItemSchema]):
    # Process multiple items concurrently
    tasks = [process_item(item) for item in items]
    results = await asyncio.gather(*tasks)
    return results
```

---

### **11. Data Exchange Best Practices**

**Shared Volumes for Files**[^5]

```yaml
# docker-compose.yml
volumes:
  - ./storage:/storage  # Shared storage

# Backend writes
cv2.imwrite('/storage/output.jpg', image)

# Frontend reads
image = Image.open('/storage/output.jpg')
```

---

### **Summary Checklist**

✅ **Architecture**: Separate FastAPI backend + Streamlit frontend
✅ **Configuration**: Environment variables (`.env` file)
✅ **Security**: CORS setup, JWT tokens, HTTPS in production
✅ **API Design**: RESTful endpoints with proper HTTP methods
✅ **Error Handling**: Try-catch blocks + user feedback
✅ **Logging**: Backend and frontend logging to files
✅ **Containerization**: Docker + Docker Compose for orchestration
✅ **Data Validation**: Pydantic models on backend
✅ **Performance**: Async operations, caching, timeouts
✅ **Testing**: Unit tests for API, integration tests for frontend
✅ **Deployment**: Separate deployment of frontend and backend

---

These practices ensure your combined codebase is scalable, maintainable, and production-ready.[^1][^7][^2][^6][^3][^4][^5]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^24][^25][^26][^27][^28][^9]</span>

<div align="center">⁂</div>

[^1]: https://prepvector.substack.com/p/deploying-a-two-tier-rag-chatbot

[^2]: https://ryanandmattdatascience.com/streamlit-fastapi/

[^3]: https://pybit.es/articles/from-backend-to-frontend-connecting-fastapi-and-streamlit/

[^4]: https://towardsdatascience.com/fastapi-and-streamlit-the-python-duo-you-must-know-about-72825def1243/

[^5]: https://testdriven.io/blog/fastapi-streamlit/

[^6]: https://www.youtube.com/watch?v=C2Pg0nWMWew

[^7]: https://davidefiocco.github.io/streamlit-fastapi-ml-serving/

[^8]: https://www.linkedin.com/posts/prajwal-waykos_easiest-way-to-deploy-your-fastapi-or-activity-7299437204257304576-zFD0

[^9]: https://link.springer.com/10.1007/s10462-024-10865-5

[^10]: https://pubs.acs.org/doi/10.1021/acs.est.4c02933

[^11]: https://xlink.rsc.org/?DOI=D4CP01792G

[^12]: https://link.springer.com/10.1007/s11119-024-10168-3

[^13]: https://www.nature.com/articles/s42003-025-08027-6

[^14]: https://amt.copernicus.org/articles/18/4631/2025/

[^15]: https://ijsrcseit.com/index.php/home/article/view/CSEIT251112177

[^16]: https://panor.ru/articles/luchshie-mirovye-praktiki-razvitiya-akvakultury-v-ramkakh-realizatsii-proektov-mnogotselevogo-ispolzovaniya-infrastruktury-toplivno-energeticheskogo-kompleksa/95832.html

[^17]: https://zenodo.org/records/10097480

[^18]: https://index.ieomsociety.org/index.cfm/article/view/ID/12739/

[^19]: https://zenodo.org/record/7994295/files/2023131243.pdf

[^20]: http://arxiv.org/pdf/2402.09615.pdf

[^21]: http://arxiv.org/pdf/2410.15533.pdf

[^22]: https://zenodo.org/record/5163394/files/Preprint-TPDS-2021.pdf

[^23]: http://arxiv.org/pdf/2401.07053.pdf

[^24]: http://arxiv.org/pdf/2501.08207.pdf

[^25]: https://arxiv.org/pdf/2502.09766.pdf

[^26]: https://arxiv.org/pdf/2211.01473.pdf

[^27]: https://discuss.streamlit.io/t/fastapi-backend-streamlit-frontend/55460

[^28]: https://discuss.streamlit.io/t/deploying-a-dockerized-mlops-app-in-streamlit-cloud-with-streamlit-and-fastapi/45390
