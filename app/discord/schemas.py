"""
Pydantic schemas for Discord data API responses.

These schemas define the shape of data returned by the API,
providing a clean interface for your friends to consume Discord data.
"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, computed_field, field_validator, ConfigDict
from pydantic.alias_generators import to_camel

from app.discord.models import MessageType, ActivityType, DiscordStatus


# Base schemas for common patterns
class BaseDiscordResponse(BaseModel):
    """Base schema for Discord API responses with common configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
        use_enum_values=True,
        str_strip_whitespace=True,
        validate_assignment=True
    )

    @field_validator('*', mode='before')
    @classmethod
    def validate_discord_id(cls, v, info):
        """Validate Discord snowflake IDs."""
        if info.field_name and info.field_name.endswith('_id') and isinstance(v, (int, str)):
            try:
                id_val = int(v)
                # Discord snowflakes should be positive and within reasonable bounds
                if id_val <= 0 or id_val > 2**63 - 1:
                    raise ValueError(f"Invalid Discord ID: {id_val}")
                return id_val
            except (ValueError, TypeError):
                raise ValueError(f"Invalid Discord ID format: {v}")
        return v


class TimestampMixin(BaseModel):
    """Mixin for schemas that need timestamp validation."""

    @field_validator('*', mode='before')
    @classmethod
    def validate_timestamps(cls, v, info):
        """Ensure timestamps are timezone-aware."""
        if info.field_name and ('_at' in info.field_name or 'first_seen' in info.field_name):
            if isinstance(v, datetime) and v.tzinfo is None:
                raise ValueError(f"Timestamp {info.field_name} must be timezone-aware")
        return v


# Discord User schemas
class DiscordUserResponse(BaseDiscordResponse, TimestampMixin):
    """Schema for Discord user data responses."""
    user_id: int = Field(..., description="Discord user ID (snowflake)", ge=1)
    first_seen: datetime = Field(..., description="When the user first joined the Discord server")

    class Config:
        json_schema_extra = {
            "example": {
                "userId": 123456789012345678,
                "firstSeen": "2023-01-15T10:30:00Z"
            }
        }


class DiscordUserWithStatsResponse(DiscordUserResponse):
    """Discord user with aggregated statistics."""
    total_messages: int = Field(..., description="Total number of messages sent", ge=0)
    total_voice_time_minutes: int = Field(..., description="Total voice time in minutes", ge=0)
    most_active_hour: Optional[int] = Field(None, description="Most active hour (0-23)", ge=0, le=23)
    favorite_activity: Optional[str] = Field(None, description="Most frequently used activity", max_length=128)

    class Config:
        json_schema_extra = {
            "example": {
                "userId": 123456789012345678,
                "firstSeen": "2023-01-15T10:30:00Z",
                "totalMessages": 1250,
                "totalVoiceTimeMinutes": 3600,
                "mostActiveHour": 20,
                "favoriteActivity": "Playing Valorant"
            }
        }


# Discord Message schemas
class DiscordMessageResponse(BaseDiscordResponse, TimestampMixin):
    """Schema for Discord message data responses."""
    message_id: int = Field(..., description="Discord message ID (snowflake)", ge=1)
    user_id: int = Field(..., description="Discord user ID who sent the message", ge=1)
    channel_id: int = Field(..., description="Discord channel ID where message was sent", ge=1)
    sent_at: datetime = Field(..., description="When the message was sent")
    message_type: MessageType = Field(default=MessageType.DEFAULT, description="Type of Discord message")
    character_count: int = Field(..., description="Length of message content in characters", ge=0)
    word_count: int = Field(0, description="Number of words in the message", ge=0)
    has_attachments: bool = Field(default=False, description="Whether message had file attachments")
    has_embeds: bool = Field(default=False, description="Whether message had rich embeds")

    @computed_field
    @property
    def estimated_word_count(self) -> int:
        """Estimate word count if not provided based on character count."""
        if self.word_count > 0:
            return self.word_count
        # Rough estimate: average 5 characters per word
        return max(1, self.character_count // 5) if self.character_count > 0 else 0

    class Config:
        json_schema_extra = {
            "example": {
                "messageId": 987654321098765432,
                "userId": 123456789012345678,
                "channelId": 456789012345678901,
                "sentAt": "2023-01-15T14:30:00Z",
                "messageType": "default",
                "characterCount": 45,
                "wordCount": 8,
                "hasAttachments": False,
                "hasEmbeds": False
            }
        }


class MessageStatsResponse(BaseDiscordResponse):
    """Schema for message statistics."""
    total_messages: int = Field(..., description="Total number of messages", ge=0)
    total_characters: int = Field(..., description="Total character count across all messages", ge=0)
    total_words: int = Field(..., description="Total word count across all messages", ge=0)
    messages_with_attachments: int = Field(..., description="Number of messages with attachments", ge=0)
    messages_with_embeds: int = Field(..., description="Number of messages with embeds", ge=0)
    most_active_channel: Optional[int] = Field(None, description="Channel ID with most messages", ge=1)
    messages_by_type: Dict[str, int] = Field(default_factory=dict, description="Message count by type")

    @computed_field
    @property
    def average_message_length(self) -> float:
        """Calculate average message length in characters."""
        return self.total_characters / self.total_messages if self.total_messages > 0 else 0.0

    @computed_field
    @property
    def attachment_rate(self) -> float:
        """Calculate percentage of messages with attachments."""
        return (self.messages_with_attachments / self.total_messages * 100) if self.total_messages > 0 else 0.0

    class Config:
        json_schema_extra = {
            "example": {
                "totalMessages": 1250,
                "totalCharacters": 45000,
                "totalWords": 9000,
                "messagesWithAttachments": 125,
                "messagesWithEmbeds": 50,
                "mostActiveChannel": 456789012345678901,
                "messagesByType": {
                    "default": 1200,
                    "reply": 45,
                    "thread_created": 5
                }
            }
        }


# Discord Activity schemas
class DiscordActivityResponse(BaseDiscordResponse, TimestampMixin):
    """Schema for Discord activity responses."""
    user_id: int = Field(..., description="Discord user ID", ge=1)
    activity_type: ActivityType = Field(..., description="Type of activity")
    activity_name: str = Field(..., description="Name of the activity", max_length=128)
    started_at: datetime = Field(..., description="When the activity started")
    ended_at: Optional[datetime] = Field(None, description="When the activity ended (null if ongoing)")

    @computed_field
    @property
    def duration_minutes(self) -> Optional[int]:
        """Calculate duration in minutes if activity has ended."""
        if self.started_at and self.ended_at:
            duration = self.ended_at - self.started_at
            return max(0, int(duration.total_seconds() / 60))
        return None

    @computed_field
    @property
    def is_ongoing(self) -> bool:
        """Check if the activity is currently ongoing."""
        return self.ended_at is None

    @field_validator('ended_at')
    @classmethod
    def validate_ended_at(cls, v, info):
        """Ensure ended_at is after started_at."""
        if v is not None and 'started_at' in info.data and info.data['started_at'] is not None:
            if v <= info.data['started_at']:
                raise ValueError("ended_at must be after started_at")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "userId": 123456789012345678,
                "activityType": "playing",
                "activityName": "Valorant",
                "startedAt": "2023-01-15T20:00:00Z",
                "endedAt": "2023-01-15T22:30:00Z"
            }
        }


class ActivityStatsResponse(BaseDiscordResponse):
    """Schema for activity statistics."""
    total_activities: int = Field(..., description="Total number of activities", ge=0)
    most_common_activity: Optional[str] = Field(None, description="Most frequently used activity", max_length=128)
    total_gaming_time_minutes: int = Field(..., description="Total time spent gaming", ge=0)
    total_listening_time_minutes: int = Field(..., description="Total time spent listening to music", ge=0)
    activities_by_type: Dict[str, int] = Field(default_factory=dict, description="Activity count by type")

    @computed_field
    @property
    def total_activity_time_minutes(self) -> int:
        """Calculate total activity time across all types."""
        return sum(self.activities_by_type.values()) if self.activities_by_type else 0

    @computed_field
    @property
    def gaming_percentage(self) -> float:
        """Calculate percentage of time spent gaming."""
        total_time = self.total_gaming_time_minutes + self.total_listening_time_minutes
        return (self.total_gaming_time_minutes / total_time * 100) if total_time > 0 else 0.0

    class Config:
        json_schema_extra = {
            "example": {
                "totalActivities": 450,
                "mostCommonActivity": "Valorant",
                "totalGamingTimeMinutes": 7200,
                "totalListeningTimeMinutes": 3600,
                "activitiesByType": {
                    "playing": 300,
                    "listening": 120,
                    "streaming": 30
                }
            }
        }


# Voice Session schemas
class VoiceSessionResponse(BaseDiscordResponse, TimestampMixin):
    """Schema for voice session responses."""
    user_id: int = Field(..., description="Discord user ID", ge=1)
    channel_id: int = Field(..., description="Discord voice channel ID", ge=1)
    joined_at: datetime = Field(..., description="When user joined the voice channel")
    left_at: Optional[datetime] = Field(None, description="When user left the voice channel (null if still in channel)")
    was_muted: bool = Field(default=False, description="Whether user was muted during any part of the session")
    was_deafened: bool = Field(default=False, description="Whether user was deafened during any part of the session")

    @computed_field
    @property
    def duration_minutes(self) -> Optional[int]:
        """Calculate session duration in minutes if session has ended."""
        if self.joined_at and self.left_at:
            duration = self.left_at - self.joined_at
            return max(0, int(duration.total_seconds() / 60))
        return None

    @computed_field
    @property
    def is_ongoing(self) -> bool:
        """Check if the voice session is currently ongoing."""
        return self.left_at is None

    @field_validator('left_at')
    @classmethod
    def validate_left_at(cls, v, info):
        """Ensure left_at is after joined_at."""
        if v is not None and 'joined_at' in info.data and info.data['joined_at'] is not None:
            if v <= info.data['joined_at']:
                raise ValueError("left_at must be after joined_at")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "userId": 123456789012345678,
                "channelId": 456789012345678901,
                "joinedAt": "2023-01-15T20:00:00Z",
                "leftAt": "2023-01-15T22:30:00Z",
                "wasMuted": False,
                "wasDeafened": False
            }
        }


class VoiceStatsResponse(BaseDiscordResponse):
    """Schema for voice statistics."""
    total_sessions: int = Field(..., description="Total number of voice sessions", ge=0)
    total_voice_time_minutes: int = Field(..., description="Total time spent in voice channels", ge=0)
    average_session_minutes: float = Field(..., description="Average session duration in minutes", ge=0)
    most_used_channel: Optional[int] = Field(None, description="Most frequently used voice channel ID", ge=1)
    time_muted_minutes: int = Field(..., description="Total time spent muted", ge=0)
    time_deafened_minutes: int = Field(..., description="Total time spent deafened", ge=0)

    @computed_field
    @property
    def mute_percentage(self) -> float:
        """Calculate percentage of voice time spent muted."""
        return (
            (self.time_muted_minutes / self.total_voice_time_minutes * 100)
            if self.total_voice_time_minutes > 0 else 0.0
        )

    @computed_field
    @property
    def deafen_percentage(self) -> float:
        """Calculate percentage of voice time spent deafened."""
        return (
            (self.time_deafened_minutes / self.total_voice_time_minutes * 100)
            if self.total_voice_time_minutes > 0 else 0.0
        )

    @computed_field
    @property
    def total_voice_time_hours(self) -> float:
        """Convert total voice time to hours for easier reading."""
        return round(self.total_voice_time_minutes / 60, 2)

    class Config:
        json_schema_extra = {
            "example": {
                "totalSessions": 85,
                "totalVoiceTimeMinutes": 3600,
                "averageSessionMinutes": 42.4,
                "mostUsedChannel": 456789012345678901,
                "timeMutedMinutes": 180,
                "timeDeafenedMinutes": 90
            }
        }


# Combined statistics schemas
class UserActivitySummaryResponse(BaseDiscordResponse):
    """Complete activity summary for a user."""
    user: DiscordUserResponse = Field(..., description="Basic user information")
    message_stats: MessageStatsResponse = Field(..., description="User's messaging statistics")
    activity_stats: ActivityStatsResponse = Field(..., description="User's activity statistics")
    voice_stats: VoiceStatsResponse = Field(..., description="User's voice channel statistics")

    @computed_field
    @property
    def overall_activity_score(self) -> float:
        """Calculate an overall activity score based on messages, voice time, and activities."""
        # Simple scoring algorithm: messages (weight 1) + voice hours (weight 2) + activities (weight 0.5)
        message_score = self.message_stats.total_messages
        voice_score = self.voice_stats.total_voice_time_minutes / 60 * 2  # Convert to hours and weight
        activity_score = self.activity_stats.total_activities * 0.5
        return round(message_score + voice_score + activity_score, 2)

    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "userId": 123456789012345678,
                    "firstSeen": "2023-01-15T10:30:00Z"
                },
                "messageStats": {
                    "totalMessages": 1250,
                    "totalCharacters": 45000,
                    "totalWords": 9000,
                    "messagesWithAttachments": 125,
                    "messagesWithEmbeds": 50,
                    "mostActiveChannel": 456789012345678901,
                    "messagesByType": {"default": 1200, "reply": 45, "thread_created": 5}
                },
                "activityStats": {
                    "totalActivities": 450,
                    "mostCommonActivity": "Valorant",
                    "totalGamingTimeMinutes": 7200,
                    "totalListeningTimeMinutes": 3600,
                    "activitiesByType": {"playing": 300, "listening": 120, "streaming": 30}
                },
                "voiceStats": {
                    "totalSessions": 85,
                    "totalVoiceTimeMinutes": 3600,
                    "averageSessionMinutes": 42.4,
                    "mostUsedChannel": 456789012345678901,
                    "timeMutedMinutes": 180,
                    "timeDeafenedMinutes": 90
                }
            }
        }


class TopUserStats(BaseModel):
    """Schema for top user statistics."""
    user_id: int = Field(..., description="Discord user ID", ge=1)
    username: Optional[str] = Field(None, description="Current username", max_length=32)
    total_messages: int = Field(..., description="Total messages sent", ge=0)
    total_voice_minutes: int = Field(..., description="Total voice time in minutes", ge=0)
    activity_score: float = Field(..., description="Overall activity score", ge=0)


class ChannelStats(BaseModel):
    """Schema for channel statistics."""
    channel_id: int = Field(..., description="Discord channel ID", ge=1)
    total_messages: int = Field(..., description="Total messages in channel", ge=0)
    unique_users: int = Field(..., description="Number of unique users who posted", ge=0)
    average_messages_per_user: float = Field(..., description="Average messages per user", ge=0)


class ServerStatsResponse(BaseDiscordResponse):
    """Overall server statistics."""
    total_users: int = Field(..., description="Total number of users", ge=0)
    total_messages: int = Field(..., description="Total messages across all channels", ge=0)
    total_voice_time_hours: float = Field(..., description="Total voice time in hours", ge=0)
    most_active_users: List[TopUserStats] = Field(default_factory=list, description="Top 10 most active users")
    most_active_channels: List[ChannelStats] = Field(default_factory=list, description="Top 10 most active channels")
    activity_breakdown: Dict[str, int] = Field(default_factory=dict, description="Activity count by type")

    @computed_field
    @property
    def average_messages_per_user(self) -> float:
        """Calculate average messages per user."""
        return self.total_messages / self.total_users if self.total_users > 0 else 0.0

    @computed_field
    @property
    def total_voice_time_days(self) -> float:
        """Convert total voice time to days for easier reading."""
        return round(self.total_voice_time_hours / 24, 2)

    class Config:
        json_schema_extra = {
            "example": {
                "totalUsers": 150,
                "totalMessages": 50000,
                "totalVoiceTimeHours": 2400.5,
                "mostActiveUsers": [
                    {
                        "userId": 123456789012345678,
                        "username": "john_doe",
                        "totalMessages": 2500,
                        "totalVoiceMinutes": 7200,
                        "activityScore": 3850.5
                    }
                ],
                "mostActiveChannels": [
                    {
                        "channelId": 456789012345678901,
                        "totalMessages": 15000,
                        "uniqueUsers": 85,
                        "averageMessagesPerUser": 176.5
                    }
                ],
                "activityBreakdown": {
                    "playing": 15000,
                    "listening": 8000,
                    "streaming": 1200
                }
            }
        }


# Additional schemas for presence and custom status
class PresenceStatusResponse(BaseDiscordResponse, TimestampMixin):
    """Schema for presence status responses."""
    user_id: int = Field(..., description="Discord user ID", ge=1)
    status_type: DiscordStatus = Field(..., description="Discord presence status")
    set_at: datetime = Field(..., description="When this status became active")
    changed_at: Optional[datetime] = Field(None, description="When this status ended (null if current)")

    @computed_field
    @property
    def duration_minutes(self) -> Optional[int]:
        """Calculate status duration in minutes if status has changed."""
        if self.set_at and self.changed_at:
            duration = self.changed_at - self.set_at
            return max(0, int(duration.total_seconds() / 60))
        return None

    @computed_field
    @property
    def is_current(self) -> bool:
        """Check if this is the current status."""
        return self.changed_at is None

    class Config:
        json_schema_extra = {
            "example": {
                "userId": 123456789012345678,
                "statusType": "online",
                "setAt": "2023-01-15T20:00:00Z",
                "changedAt": "2023-01-15T22:30:00Z"
            }
        }


class CustomStatusResponse(BaseDiscordResponse, TimestampMixin):
    """Schema for custom status responses."""
    user_id: int = Field(..., description="Discord user ID", ge=1)
    status_text: Optional[str] = Field(None, description="Custom status message text", max_length=128)
    emoji: Optional[str] = Field(None, description="Emoji used in custom status", max_length=64)
    set_at: datetime = Field(..., description="When the custom status was set")

    @computed_field
    @property
    def has_emoji(self) -> bool:
        """Check if the custom status has an emoji."""
        return self.emoji is not None and len(self.emoji.strip()) > 0

    @computed_field
    @property
    def has_text(self) -> bool:
        """Check if the custom status has text."""
        return self.status_text is not None and len(self.status_text.strip()) > 0

    class Config:
        json_schema_extra = {
            "example": {
                "userId": 123456789012345678,
                "statusText": "Coding the future",
                "emoji": "💻",
                "setAt": "2023-01-15T20:00:00Z"
            }
        }
