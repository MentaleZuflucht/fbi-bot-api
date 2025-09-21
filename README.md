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

# Activate venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 API Endpoints

- **GraphQL**: `POST /graphql` - Main GraphQL endpoint
- **GraphiQL**: `GET /graphql` - Interactive GraphQL explorer (browser)
- **Health**: `GET /health` - API health check
- **Docs**: `GET /docs` - OpenAPI documentation
- **Root**: `GET /` - API information

## 🔧 API Key Management

### Create API Key (Admin)
```bash
python scripts/manage_api_keys.py create "My App" read
```

### List API Keys (Admin)
```graphql
query AdminKeys {
  apiKeys {
    id
    name
    keyPrefix
    role
    createdAt
    lastUsedAt
  }
}
```

### View Usage Statistics (Admin)
```graphql
query Usage {
  apiUsage(limit: 50, days: 7) {
    timestamp
    endpoint
    method
    responseStatus
    apiKeyName
  }
  authStats {
    totalApiKeys
    adminKeys
    readKeys
    totalRequestsToday
  }
}
```

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
