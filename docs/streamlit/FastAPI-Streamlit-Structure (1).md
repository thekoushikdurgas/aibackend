# FastAPI + Streamlit Production-Ready File Structure

## Complete Directory Layout

```
project-root/
│
├── .github/
│   ├── workflows/
│   │   ├── ci-cd-backend.yml
│   │   ├── ci-cd-frontend.yml
│   │   └── deploy.yml
│   └── ISSUE_TEMPLATE/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── config.py                  # Configuration & settings
│   │   ├── dependencies.py            # Shared dependencies (DB, auth)
│   │   ├── exceptions.py              # Custom exceptions
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── auth.py        # /auth endpoints
│   │   │   │   │   ├── users.py       # /users endpoints
│   │   │   │   │   ├── items.py       # /items endpoints
│   │   │   │   │   └── data.py        # /data endpoints
│   │   │   │   └── router.py          # Aggregate all v1 routes
│   │   │   └── v2/                    # Future API version
│   │   │       └── endpoints/
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py            # JWT, password hashing, auth logic
│   │   │   ├── logging.py             # Logging configuration
│   │   │   └── constants.py           # App-wide constants
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py             # Pydantic models for API
│   │   │   └── database.py            # SQLAlchemy models
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── user_service.py        # User business logic
│   │   │   ├── item_service.py        # Item business logic
│   │   │   ├── auth_service.py        # Authentication logic
│   │   │   └── email_service.py       # Email operations
│   │   │
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── session.py             # Database session management
│   │   │   ├── base.py                # Base model for all tables
│   │   │   └── migrations/            # Alembic migrations
│   │   │       ├── versions/
│   │   │       └── env.py
│   │   │
│   │   ├── middlewares/
│   │   │   ├── __init__.py
│   │   │   ├── cors.py                # CORS configuration
│   │   │   ├── logging.py             # Request/response logging
│   │   │   └── error_handler.py       # Global error handling
│   │   │
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── validators.py          # Custom validation functions
│   │   │   ├── formatters.py          # Data formatting utilities
│   │   │   ├── decorators.py          # Custom decorators
│   │   │   └── helpers.py             # Helper functions
│   │   │
│   │   └── tasks/
│   │       ├── __init__.py
│   │       ├── celery_app.py          # Celery configuration (if needed)
│   │       └── background_tasks.py    # Async background jobs
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                # Pytest fixtures
│   │   ├── test_main.py               # Main app tests
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── test_auth.py
│   │   │   ├── test_users.py
│   │   │   ├── test_items.py
│   │   │   └── test_data.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── test_user_service.py
│   │   │   └── test_auth_service.py
│   │   │
│   │   └── unit/
│   │       ├── __init__.py
│   │       ├── test_validators.py
│   │       └── test_helpers.py
│   │
│   ├── logs/                          # Log directory (gitignored)
│   │
│   ├── .env.example                   # Environment template
│   ├── .env                           # Actual secrets (gitignored)
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements-dev.txt           # Development dependencies
│   ├── pytest.ini
│   ├── setup.py
│   └── alembic.ini                    # Database migration config
│
├── frontend/
│   ├── app.py                         # Main Streamlit entry point
│   ├── config.py                      # Frontend configuration
│   ├── requirements.txt
│   ├── .env.example
│   ├── .env                           # Secrets (gitignored)
│   ├── .streamlit/
│   │   └── config.toml                # Streamlit configuration
│   │
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── 01_🏠_home.py              # Home page
│   │   ├── 02_📊_dashboard.py         # Dashboard page
│   │   ├── 03_👤_profile.py           # User profile page
│   │   ├── 04_⚙️_settings.py          # Settings page
│   │   └── 05_📝_admin.py             # Admin panel (if applicable)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── api_client.py              # API client with error handling
│   │   ├── auth_service.py            # Authentication logic
│   │   └── cache_service.py           # Caching utilities
│   │
│   ├── components/
│   │   ├── __init__.py
│   │   ├── sidebar.py                 # Sidebar component
│   │   ├── header.py                  # Header component
│   │   ├── forms.py                   # Reusable form components
│   │   ├── tables.py                  # Data table component
│   │   ├── charts.py                  # Chart components
│   │   └── modals.py                  # Modal dialogs
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validators.py              # Input validation
│   │   ├── formatters.py              # Data formatting
│   │   ├── helpers.py                 # Helper functions
│   │   └── constants.py               # App constants
│   │
│   ├── state/
│   │   ├── __init__.py
│   │   ├── session_state.py           # Session state management
│   │   └── cache.py                   # Cache management
│   │
│   ├── pages_logic/                   # Logic for each page (optional)
│   │   ├── __init__.py
│   │   ├── home_logic.py
│   │   ├── dashboard_logic.py
│   │   └── profile_logic.py
│   │
│   ├── assets/
│   │   ├── images/
│   │   ├── icons/
│   │   └── styles.css                 # Custom CSS
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_app.py
│   │   ├── test_api_client.py
│   │   └── test_components/
│   │
│   ├── logs/                          # Log directory (gitignored)
│   │
│   └── .dockerignore
│   └── Dockerfile
│
├── docs/
│   ├── API.md                         # API documentation
│   ├── SETUP.md                       # Setup instructions
│   ├── DEPLOYMENT.md                  # Deployment guide
│   ├── ARCHITECTURE.md                # Architecture overview
│   └── CONTRIBUTING.md                # Contribution guidelines
│
├── .env.example                       # Root level environment template
├── .env                               # Root level secrets (gitignored)
├── .gitignore
├── .dockerignore
│
├── docker-compose.yml                 # Development docker compose
├── docker-compose.prod.yml            # Production docker compose
│
├── Makefile                           # Development commands
├── scripts/
│   ├── init_db.py                     # Database initialization
│   ├── seed_db.py                     # Database seeding
│   ├── migrate.sh                     # Migration script
│   └── deploy.sh                      # Deployment script
│
├── nginx/                             # Nginx configuration (optional)
│   ├── nginx.conf
│   └── Dockerfile
│
├── README.md
├── LICENSE
└── setup.py                           # Python package setup
```

---

## Key Files with Best Practices

### 1. **Backend Main Entry Point** (`backend/app/main.py`)

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.core.logging import setup_logging
from app.middlewares.cors import setup_cors
from app.middlewares.error_handler import setup_error_handlers
from app.api.v1.router import api_router
from app.database.session import engine, Base

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Application starting...")
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    logger.info("Application shutting down...")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="FastAPI Backend for Data Management",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Add middlewares
setup_cors(app)
app.add_middleware(GZIPMiddleware, minimum_size=1000)

# Setup error handlers
setup_error_handlers(app)

# Include routes
app.include_router(api_router, prefix="/api/v1")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to FastAPI Backend",
        "docs": "/api/docs",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
```

---

### 2. **Configuration** (`backend/app/config.py`)

```python
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "FastAPI Backend"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/dbname"
    )
    SQLALCHEMY_ECHO: bool = False

    # CORS
    ALLOWED_ORIGINS: list = ["http://localhost:8501", "http://localhost:3000"]
    ALLOW_CREDENTIALS: bool = True
    ALLOW_METHODS: list = ["*"]
    ALLOW_HEADERS: list = ["*"]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # External APIs
    EMAIL_FROM: str = "noreply@example.com"
    SENDGRID_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()
```

---

### 3. **API Router** (`backend/app/api/v1/router.py`)

```python
from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, items, data

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(items.router, prefix="/items", tags=["Items"])
api_router.include_router(data.router, prefix="/data", tags=["Data"])
```

---

### 4. **Example Endpoint** (`backend/app/api/v1/endpoints/items.py`)

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
import logging

from app.models.schemas import ItemCreate, ItemUpdate, ItemResponse
from app.services.item_service import ItemService
from app.database.session import get_db
from app.core.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/", response_model=List[ItemResponse])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all items with pagination"""
    try:
        service = ItemService(db)
        items = service.get_items(skip=skip, limit=limit, user_id=current_user.id)
        return items
    except Exception as e:
        logger.error(f"Error fetching items: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch items")

@router.post("/", response_model=ItemResponse)
async def create_item(
    item: ItemCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new item"""
    try:
        service = ItemService(db)
        db_item = service.create_item(item, user_id=current_user.id)
        logger.info(f"Item created: {db_item.id}")
        return db_item
    except ValueError as e:
        logger.warning(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating item: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create item")

@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific item by ID"""
    service = ItemService(db)
    item = service.get_item(item_id, user_id=current_user.id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    item: ItemUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an item"""
    service = ItemService(db)
    db_item = service.update_item(item_id, item, user_id=current_user.id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    logger.info(f"Item updated: {item_id}")
    return db_item

@router.delete("/{item_id}")
async def delete_item(
    item_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an item"""
    service = ItemService(db)
    success = service.delete_item(item_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    logger.info(f"Item deleted: {item_id}")
    return {"message": "Item deleted successfully"}
```

---

### 5. **Service Layer** (`backend/app/services/item_service.py`)

```python
from sqlalchemy.orm import Session
from app.models.database import Item
from app.models.schemas import ItemCreate, ItemUpdate

class ItemService:
    def __init__(self, db: Session):
        self.db = db

    def get_items(self, skip: int = 0, limit: int = 10, user_id: int = None):
        query = self.db.query(Item)
        if user_id:
            query = query.filter(Item.user_id == user_id)
        return query.offset(skip).limit(limit).all()

    def get_item(self, item_id: int, user_id: int = None):
        query = self.db.query(Item).filter(Item.id == item_id)
        if user_id:
            query = query.filter(Item.user_id == user_id)
        return query.first()

    def create_item(self, item: ItemCreate, user_id: int):
        db_item = Item(
            **item.model_dump(),
            user_id=user_id
        )
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def update_item(self, item_id: int, item: ItemUpdate, user_id: int):
        db_item = self.get_item(item_id, user_id)
        if not db_item:
            return None

        update_data = item.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_item, field, value)

        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def delete_item(self, item_id: int, user_id: int):
        db_item = self.get_item(item_id, user_id)
        if not db_item:
            return False

        self.db.delete(db_item)
        self.db.commit()
        return True
```

---

### 6. **Pydantic Models** (`backend/app/models/schemas.py`)

```python
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
from datetime import datetime

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Item name")
    description: Optional[str] = Field(None, max_length=500, description="Item description")
    price: float = Field(..., gt=0, description="Item price")

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()

class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)

class ItemResponse(ItemCreate):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
```

---

### 7. **Frontend Main App** (`frontend/app.py`)

```python
import streamlit as st
from pathlib import Path
import sys

# Add services to path
sys.path.append(str(Path(__file__).parent))

from config import settings
from state.session_state import init_session_state
from services.api_client import APIClient

# Page configuration
st.set_page_config(
    page_title="Data Management Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
init_session_state()

# Load custom CSS
def load_css():
    with open("assets/styles.css", "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Sidebar
with st.sidebar:
    st.image("assets/images/logo.png", width=200)
    st.title("Navigation")

    if st.session_state.get("authenticated"):
        st.write(f"Welcome, {st.session_state.user_email}")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()
    else:
        st.write("Please login to continue")

# Main content
st.title("📊 Data Management Platform")
st.markdown("---")

if not st.session_state.get("authenticated"):
    st.info("Please navigate to the Home page and login")
else:
    st.success("You are logged in!")
```

---

### 8. **Frontend API Client** (`frontend/services/api_client.py`)

```python
import httpx
import streamlit as st
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.timeout = 30

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if token := st.session_state.get("access_token"):
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def get(self, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}{endpoint}",
                    headers=self._get_headers(),
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"API GET Error: {str(e)}")
            st.error(f"Failed to fetch data: {str(e)}")
            return None

    async def post(self, endpoint: str, data: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    json=data,
                    headers=self._get_headers(),
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"API POST Error: {str(e)}")
            st.error(f"Failed to create: {str(e)}")
            return None

    async def put(self, endpoint: str, data: Dict[str, Any], **kwargs) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    f"{self.base_url}{endpoint}",
                    json=data,
                    headers=self._get_headers(),
                    **kwargs
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"API PUT Error: {str(e)}")
            st.error(f"Failed to update: {str(e)}")
            return None

    async def delete(self, endpoint: str, **kwargs) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}{endpoint}",
                    headers=self._get_headers(),
                    **kwargs
                )
                response.raise_for_status()
                return True
        except httpx.HTTPError as e:
            logger.error(f"API DELETE Error: {str(e)}")
            st.error(f"Failed to delete: {str(e)}")
            return False

# Global client instance
api_client = APIClient(base_url="http://localhost:8000/api/v1")
```

---

### 9. **Session State Management** (`frontend/state/session_state.py`)

```python
import streamlit as st

def init_session_state():
    """Initialize all session state variables"""

    # Authentication
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "access_token" not in st.session_state:
        st.session_state.access_token = None

    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if "user_email" not in st.session_state:
        st.session_state.user_email = None

    # Data cache
    if "items" not in st.session_state:
        st.session_state.items = []

    if "users" not in st.session_state:
        st.session_state.users = []

    # UI state
    if "page" not in st.session_state:
        st.session_state.page = "home"

    if "refresh_data" not in st.session_state:
        st.session_state.refresh_data = False

def clear_session():
    """Clear all session data"""
    st.session_state.clear()

def set_authenticated(user_email: str, access_token: str, user_id: int):
    """Set authenticated state"""
    st.session_state.authenticated = True
    st.session_state.user_email = user_email
    st.session_state.access_token = access_token
    st.session_state.user_id = user_id
```

---

### 10. **Docker Compose** (`docker-compose.yml`)

```yaml
version: '3.9'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: fastapi-backend
    ports:
      - '8000:8000'
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/appdb
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=True
      - ALLOWED_ORIGINS=["http://localhost:8501"]
    depends_on:
      - postgres
    volumes:
      - ./backend:/app
    networks:
      - app-network
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: streamlit-frontend
    ports:
      - '8501:8501'
    environment:
      - API_URL=http://backend:8000/api/v1
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
    networks:
      - app-network
    command: streamlit run app.py --logger.level=debug

  postgres:
    image: postgres:15-alpine
    container_name: postgres-db
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=appdb
    ports:
      - '5432:5432'
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app-network
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U user']
      interval: 10s
      timeout: 5s
      retries: 5

  adminer:
    image: adminer
    container_name: adminer
    ports:
      - '8080:8080'
    networks:
      - app-network

networks:
  app-network:
    driver: bridge

volumes:
  postgres_data:
```

---

### 11. **Requirements Files**

**backend/requirements.txt**

```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
email-validator==2.1.0
httpx==0.25.1
python-dotenv==1.0.0
alembic==1.12.1
```

**frontend/requirements.txt**

```
streamlit==1.28.1
httpx==0.25.1
pandas==2.1.3
plotly==5.18.0
pillow==10.1.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
altair==5.1.2
```

---

### 12. **Environment Configuration** (`.env.example`)

```env
# Backend
DATABASE_URL=postgresql://user:password@localhost:5432/appdb
SECRET_KEY=your-super-secret-key-change-in-production
DEBUG=True
ENVIRONMENT=development
ALLOWED_ORIGINS=["http://localhost:8501","http://localhost:3000"]

# Frontend
API_URL=http://localhost:8000/api/v1

# Email (if using)
SENDGRID_API_KEY=your-sendgrid-key
EMAIL_FROM=noreply@example.com

# Database
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=appdb
```

---

## Best Practices Summary

✅ **Separation of Concerns**: Backend logic vs Frontend UI  
✅ **Service Layer**: Business logic isolated from API endpoints  
✅ **Pydantic Models**: Type-safe data validation  
✅ **Session Management**: Secure user state management  
✅ **Error Handling**: Comprehensive error handling & logging  
✅ **Configuration**: Environment-based settings management  
✅ **Docker**: Containerized development & deployment  
✅ **Testing**: Organized test structure  
✅ **Security**: JWT authentication, CORS configuration  
✅ **Documentation**: Clear file organization & comments  
✅ **Scalability**: Modular architecture for easy expansion  
✅ **Logging**: Structured logging throughout

---

## Quick Start Commands

```bash
# Setup
docker-compose up --build

# Backend only
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend only
cd frontend
pip install -r requirements.txt
streamlit run app.py

# Database migrations
alembic upgrade head

# Tests
pytest backend/tests/
```
