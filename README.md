# FBI Bot API - Discord Data Analytics GraphQL API

A powerful GraphQL API for accessing Discord server analytics data collected by your FBI Bot. Built with FastAPI and Strawberry GraphQL, this API provides flexible access to user activity, messages, voice sessions, and comprehensive server statistics.

## 🚀 Features

- **GraphQL API** - Flexible queries with GraphiQL interface
- **Discord Analytics** - User activity, messages, voice sessions, presence tracking
- **Authentication** - API key-based authentication with role-based access
- **Admin Dashboard** - API key management and usage statistics
- **Real-time Data** - Live Discord activity tracking
- **Comprehensive Stats** - User, channel, and server-wide analytics

## 🛠 Tech Stack

- **FastAPI** - Modern, fast web framework
- **Strawberry GraphQL** - Python GraphQL library
- **SQLModel** - SQL database ORM with type safety
- **PostgreSQL** - Primary database for Discord data
- **Alembic** - Database migrations
- **Docker** - Containerized deployment

## 📊 What Data Can You Query?

### User Data
- **Messages** - Message activity with attachments, embeds, character counts
- **Voice Sessions** - Voice channel activity with duration tracking
- **Activities** - Gaming, streaming, listening activities
- **Presence Status** - Online, idle, DND, offline tracking
- **Custom Statuses** - User custom status messages and emojis
- **Name History** - Username, display name, and global name changes

### Server Analytics
- **Channel Statistics** - Message counts, unique users per channel
- **Server Overview** - Total users, messages, voice time, activities
- **Activity Trends** - Most active channels, common activities
- **User Rankings** - Most active users by various metrics

### Administrative
- **API Key Management** - Create, view, manage API keys (admin only)
- **Usage Tracking** - API request logs and statistics
- **Authentication Stats** - Key usage and success rates

## 🔑 Authentication

All GraphQL queries require authentication using Bearer tokens:

```
Authorization: Bearer sk_live_your_api_key_here
```

### API Key Roles
- **`read`** - Access to all Discord data queries
- **`admin`** - Full access including API key management

## 🚦 Quick Start

### 1. Get an API Key
Contact your server admin to get an API key.

### 2. Explore the API
Visit `/graphql` in your browser to access the interactive GraphiQL interface.

### 3. Test Your Authentication
```graphql
query TestAuth {
  hello
}
```

### 4. Query User Data
```graphql
query GetUser {
  user(userId: "123456789") {
    userId
    firstSeen
    currentName {
      username
      displayName
      globalName
    }
    messageCount(days: 7)
    voiceSessions(limit: 5) {
      channelId
      joinedAt
      durationMinutes
    }
  }
}
```

## 📖 Example Queries

### Get Recent Messages
```graphql
query RecentMessages {
  messages(limit: 10, days: 1) {
    messageId
    userId
    channelId
    messageType
    hasAttachments
    sentAt
  }
}
```

### Server Statistics
```graphql
query ServerStats {
  serverStats(days: 30) {
    totalUsers
    totalMessages
    totalVoiceTimeHours
    mostActiveChannelId
    mostCommonActivity
  }
}
```

### User Activity Summary
```graphql
query UserActivity($userId: String!) {
  user(userId: $userId) {
    stats(days: 30) {
      totalMessages
      totalVoiceTimeMinutes
      totalActivities
      mostActiveHour
      favoriteActivity
    }
    activities(limit: 5) {
      activityType
      activityName
      startedAt
      durationMinutes
    }
  }
}
```

### Channel Rankings
```graphql
query ChannelStats {
  channelStats(limit: 10, days: 7) {
    channelId
    totalMessages
    uniqueUsers
    mostActiveUserId
  }
}
```

## 🏃‍♂️ Running the API

### Environment Variables
Create a `.env` file:
```env
AUTH_DATABASE_URL=postgresql://user:password@localhost/fbi_auth
DISCORD_DATABASE_URL=postgresql://user:password@localhost/discord_data
DEBUG=false
LOG_LEVEL=INFO
```

### Docker (Recommended but limited to unraid)
```bash
docker-compose up -d
```

### Local Development (with venv)
```bash
# Create venv
python3 -m venv .venv

# Activate venv (Windows)
.venv\Scripts\activate
# Or on Linux/Mac:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API (DB tables auto-created on first run)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Check logs for your initial admin API key!
```

**Database Initialization:**
- Tables are created automatically on startup
- Initial admin key is generated on first run
- No manual migrations needed (Alembic is optional)

## 📚 API Endpoints

- **GraphQL**: `POST /graphql` - Main GraphQL endpoint
- **GraphiQL**: `GET /graphql` - Interactive GraphQL explorer (browser)
- **Health**: `GET /health` - API health check
- **Docs**: `GET /docs` - OpenAPI documentation
- **Root**: `GET /` - API information

## 🔧 API Key Management

### First-Time Setup

On first startup, the API automatically creates an **initial admin key** and logs it:

```
🚨 IMPORTANT: Save this key immediately - it will not be shown again!
================================================================================
API KEY: sk_live_abc123...
================================================================================
```

**Check your Docker logs:**
```bash
docker logs fbi-bot-api | grep "API KEY:"
```

This admin key lets you create additional keys for your friends.

### Creating Keys for Friends

Use the admin REST API to create new keys:

```bash
curl -X POST http://your-api:8000/admin/api-keys/ \
  -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "John'\''s Key", "role": "read"}'
```

Response includes the new API key (save it!):
```json
{
  "id": 2,
  "name": "John's Key",
  "api_key": "sk_live_xyz789...",
  "role": "read"
}
```

### Admin REST Endpoints

All require an admin API key:

- **POST** `/admin/api-keys/` - Create new API key
- **GET** `/admin/api-keys/` - List all API keys
- **DELETE** `/admin/api-keys/{key_id}` - Revoke an API key
- **GET** `/admin/api-keys/{key_id}/stats?days=7` - View usage statistics

See `/docs` for full interactive documentation.

## 🔍 GraphQL Schema

The API provides comprehensive types for:

### Core Types
- `UserType` - Discord user with activity methods
- `MessageActivityType` - Message data with metadata
- `VoiceSessionType` - Voice channel sessions
- `ActivityLogType` - User activities (games, streaming, etc.)
- `PresenceStatusLogType` - Online status tracking
- `CustomStatusType` - Custom status messages

### Statistics Types
- `UserStatsType` - Comprehensive user analytics
- `ChannelStatsType` - Channel-specific statistics
- `ServerStatsType` - Server-wide analytics

### Authentication Types
- `ApiKeyType` - API key information
- `ApiUsageType` - Usage tracking data
- `AuthStatsType` - Authentication statistics

## 🚨 Error Handling

The API returns standard GraphQL errors:

```json
{
  "errors": [
    {
      "message": "Authentication required",
      "path": ["user"],
      "extensions": {
        "code": "UNAUTHENTICATED"
      }
    }
  ]
}
```
