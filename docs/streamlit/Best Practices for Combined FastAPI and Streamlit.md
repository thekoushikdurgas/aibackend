<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

## Best Practices for Combined FastAPI and Streamlit Codebase

When building applications with FastAPI as the backend and Streamlit as the frontend, you should adopt a clean separation architecture that maximizes the strengths of both frameworks.[^1][^2]

### Project Architecture

**Separate Backend and Frontend**
Keep your FastAPI and Streamlit code in separate directories within your project structure. This enables independent scaling, deployment, and development workflows. A typical structure includes:[^3][^1]

- `/backend` - FastAPI application with business logic, ML models, and database interactions
- `/frontend` - Streamlit application handling UI components and user interactions
- `/shared` - Common models, utilities, or Pydantic schemas used by both

**API-First Design**
Design your FastAPI backend with clear RESTful endpoints that return structured data (JSON). This allows you to potentially swap the Streamlit frontend with production-ready alternatives like React or Dash later without changing backend code.[^4][^5]

### Communication Patterns

**HTTP Requests via Libraries**
Use `requests` or `httpx` (for async) in your Streamlit frontend to communicate with FastAPI endpoints. Handle API responses gracefully with proper error handling and loading states in your Streamlit interface.[^6][^3]

**Environment Configuration**
Manage API URLs and secrets using environment variables with fallback logic:[^1]

- Local development: `.env` files with `python-dotenv`
- Streamlit Cloud: `st.secrets` configuration
- Production: Environment variables or secret management services

### Deployment Strategies

**Containerization with Docker**
Containerize both services separately and orchestrate them using `docker-compose`. This enables:[^7][^5][^4]

- Consistent development and production environments
- Independent scaling of frontend and backend containers
- Easy local testing of the distributed system

**Flexible Deployment Options**
Your architecture should support multiple deployment scenarios:[^8]

- Monolithic local deployment for development
- Streamlit Cloud frontend + cloud-hosted FastAPI backend
- Fully distributed deployment on platforms like GCP, AWS, or Azure

### Security and Performance

**Backend Isolation**
Only expose the Streamlit frontend to public internet traffic while keeping FastAPI backend endpoints protected. Implement authentication, rate limiting, and input validation on the FastAPI side.[^2]

**State Management**
Use Streamlit's session state to manage chat history, user inputs, and API response caching. This prevents unnecessary API calls and improves user experience.[^3]

**Async Operations**
Leverage FastAPI's native async capabilities for I/O-bound operations like database queries or external API calls. For Streamlit, use async libraries like `httpx` when making backend requests to prevent blocking the UI.[^2]
<span style="display:none">[^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^20][^21][^22][^23][^9]</span>

<div align="center">⁂</div>

[^1]: https://pybit.es/articles/from-backend-to-frontend-connecting-fastapi-and-streamlit/

[^2]: https://prepvector.substack.com/p/deploying-a-two-tier-rag-chatbot

[^3]: https://www.youtube.com/watch?v=C2Pg0nWMWew

[^4]: https://testdriven.io/blog/fastapi-streamlit/

[^5]: https://davidefiocco.github.io/streamlit-fastapi-ml-serving/

[^6]: https://dev.to/cypriantinasheaarons/introduction-to-building-ai-powered-apps-with-streamlit-and-fastapi-73d

[^7]: https://towardsdatascience.com/fastapi-and-streamlit-the-python-duo-you-must-know-about-72825def1243/

[^8]: https://discuss.streamlit.io/t/hybrid-architecture-media-server-media-service-and-streamlit-client-app-using-fastapi-and-python/27587

[^9]: https://ajisresearch.com/index.php/ajis/article/view/13

[^10]: https://iea-pvps.org/key-topics/analysis-of-the-technological-innovation-system-for-bipv-in-austria/

[^11]: https://journals.sagepub.com/doi/10.1177/25166085251358941

[^12]: https://www.multiresearchjournal.com/arclist/list-2023.3.6/id-4323

[^13]: https://riojournal.com/article/54280/

[^14]: https://zenodo.org/record/7994295/files/2023131243.pdf

[^15]: http://arxiv.org/pdf/2410.16569.pdf

[^16]: https://www.mdpi.com/2078-2489/11/2/108/pdf

[^17]: https://arxiv.org/pdf/2303.11088.pdf

[^18]: https://www.mdpi.com/2078-2489/11/12/565/pdf

[^19]: http://arxiv.org/pdf/2410.00006.pdf

[^20]: https://arxiv.org/pdf/2502.09766.pdf

[^21]: http://arxiv.org/pdf/2407.07428.pdf

[^22]: https://discuss.streamlit.io/t/fastapi-backend-streamlit-frontend/55460

[^23]: https://github.com/karndeb/Fastapi-Streamlit-NLP-Microservice
