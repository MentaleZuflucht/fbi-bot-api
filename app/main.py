"""
Main FastAPI application.

This is the entry point for the FBI Bot API. It sets up the FastAPI app,
includes all routers, configures middleware, and handles startup/shutdown events.
"""
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
from app.config import settings, setup_logging
from app.auth.database import create_auth_tables
from app.graphql.schema import graphql_app

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.

    Handles startup and shutdown tasks like database initialization.
    """
    logger.info("Starting FBI Bot API (GraphQL)...")
    logger.info(f"Environment: {'development' if settings.debug else 'production'}")
    logger.info(f"Log level: {settings.log_level}")

    try:
        create_auth_tables()
        logger.info("Auth database tables ready")
    except Exception as e:
        logger.error(f"Auth database setup failed: {e}", exc_info=True)
        raise

    logger.info("Discord database connection ready (read-only)")
    logger.info("FBI Bot API started successfully!")

    yield

    logger.info("Shutting down FBI Bot API...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
     FBI Bot API - Discord Data Analytics GraphQL API

     This GraphQL API provides flexible access to Discord server data collected by your bot.
     Perfect for friends who want to build custom dashboards, analytics tools, or data visualizations.

     ## Authentication

     All GraphQL queries require authentication using API keys:

     ```
     Authorization: Bearer sk_live_your_api_key_here
     ```

     ## GraphQL Endpoint

     - **GraphQL**: `/graphql` - Flexible GraphQL queries and mutations
     - **GraphiQL**: `/graphql` (in browser) - Interactive GraphQL explorer

     ## Getting Started

     1. Contact the admin for an API key
     2. Visit `/graphql` in your browser to explore the schema
     3. Use any GraphQL client to query Discord data

     ## Example Query

     ```graphql
     query GetUserActivity($userId: Int!) {
        user(userId: $userId) {
           userId
           firstSeen
           messageCount(days: 30)
           messages(limit: 10) {
           sentAt
           characterCount
           messageType
           }
        }
     }
     ```
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure this properly in production
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all HTTP requests and responses."""
    start_time = time.time()

    # Log request
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Request: {request.method} {request.url.path} from {client_ip}")

    # Process request
    try:
        response = await call_next(request)

        # Log response
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} in {process_time:.3f}s")

        return response

    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path} - {str(e)} "
            f"in {process_time:.3f}s",
            exc_info=True
        )
        raise

app.include_router(
    graphql_app,
    prefix="/graphql",
    tags=["GraphQL"]
)


@app.get("/", tags=["Root"])
async def root():
    """
    API root endpoint.

    Provides basic information about the API and available endpoints.
    """
    return {
        "message": "Welcum, to the FBI Bot API",
        "version": settings.app_version,
        "docs": "/docs",
        "graphql": "/graphql",
        "endpoints": {
             "graphql": "/graphql",
             "graphiql": "/graphql (browser)",
             "admin_api": "/api/v1/auth/ (admin only)"
         },
        "description": "Discord data analytics API using GraphQL"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns the API status and basic system information.
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production"
    }


if __name__ == "__main__":
    # Configure uvicorn logging to use our logging setup
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        log_config=log_config
    )
