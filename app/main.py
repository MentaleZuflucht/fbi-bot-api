"""
Main FastAPI application.

This is the entry point for the FBI Bot API. It sets up the FastAPI app,
includes all routers, configures middleware, and handles startup/shutdown events.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
from app.config import settings
from app.auth.database import create_auth_tables
from app.graphql.schema import graphql_app

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.

    Handles startup and shutdown tasks like database initialization.
    """
    logger.info("Starting FBI Bot API (GraphQL)...")

    try:
        create_auth_tables()
        logger.info("Auth database tables ready")
    except Exception as e:
        logger.error(f"Auth database setup failed: {e}")
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
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
