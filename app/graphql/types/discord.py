"""
GraphQL types for Discord data.

These types expose the Discord database models for querying user activity,
messages, voice sessions, and other Discord-related data.
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum
import strawberry
from sqlmodel import select, func, and_
from app.graphql.context import GraphQLContext
from app.discord.models import (
    User, MessageActivity, VoiceSession, VoiceStateLog,
    PresenceStatusLog, ActivityLog, CustomStatus, UserNameHistory
)


# Enums
@strawberry.enum
class MessageTypeEnum(Enum):
    """GraphQL enum for Discord message types."""
    DEFAULT = "default"
    RECIPIENT_ADD = "recipient_add"
    RECIPIENT_REMOVE = "recipient_remove"
    CALL = "call"
    CHANNEL_NAME_CHANGE = "channel_name_change"
    CHANNEL_ICON_CHANGE = "channel_icon_change"
    CHANNEL_PINNED_MESSAGE = "channel_pinned_message"
    USER_JOIN = "user_join"
    GUILD_BOOST = "guild_boost"
    GUILD_BOOST_TIER_1 = "guild_boost_tier_1"
    GUILD_BOOST_TIER_2 = "guild_boost_tier_2"
    GUILD_BOOST_TIER_3 = "guild_boost_tier_3"
    CHANNEL_FOLLOW_ADD = "channel_follow_add"
    GUILD_DISCOVERY_DISQUALIFIED = "guild_discovery_disqualified"
    GUILD_DISCOVERY_REQUALIFIED = "guild_discovery_requalified"
    GUILD_DISCOVERY_GRACE_PERIOD_INITIAL_WARNING = "guild_discovery_grace_period_initial_warning"
    GUILD_DISCOVERY_GRACE_PERIOD_FINAL_WARNING = "guild_discovery_grace_period_final_warning"
    THREAD_CREATED = "thread_created"
    REPLY = "reply"
    CHAT_INPUT_COMMAND = "chat_input_command"
    THREAD_STARTER_MESSAGE = "thread_starter_message"
    GUILD_INVITE_REMINDER = "guild_invite_reminder"
    CONTEXT_MENU_COMMAND = "context_menu_command"
    ROLE_SUBSCRIPTION_PURCHASE = "role_subscription_purchase"
    INTERACTION_PREMIUM_UPSELL = "interaction_premium_upsell"
    STAGE_START = "stage_start"
    STAGE_END = "stage_end"
    STAGE_SPEAKER = "stage_speaker"
    STAGE_RAISE_HAND = "stage_raise_hand"
    STAGE_TOPIC = "stage_topic"
    GUILD_APPLICATION_PREMIUM_SUBSCRIPTION = "guild_application_premium_subscription"
    GUILD_INCIDENT_ALERT_MODE_ENABLED = "guild_incident_alert_mode_enabled"
    GUILD_INCIDENT_ALERT_MODE_DISABLED = "guild_incident_alert_mode_disabled"
    GUILD_INCIDENT_REPORT_RAID = "guild_incident_report_raid"
    GUILD_INCIDENT_REPORT_FALSE_ALARM = "guild_incident_report_false_alarm"
    PURCHASE_NOTIFICATION = "purchase_notification"
    POLL_RESULT = "poll_result"


@strawberry.enum
class ActivityTypeEnum(Enum):
    """GraphQL enum for Discord activity types."""
    COMPETING = "competing"
    CUSTOM = "custom"
    LISTENING = "listening"
    PLAYING = "playing"
    STREAMING = "streaming"
    WATCHING = "watching"


@strawberry.enum
class DiscordStatusEnum(Enum):
    """GraphQL enum for Discord status types."""
    ONLINE = "online"
    IDLE = "idle"
    DND = "dnd"
    OFFLINE = "offline"
    STREAMING = "streaming"


@strawberry.enum
class VoiceStateTypeEnum(Enum):
    """GraphQL enum for voice state types."""
    DEAF = "deaf"
    MUTE = "mute"
    SELF_DEAF = "self_deaf"
    SELF_MUTE = "self_mute"
    SELF_STREAM = "self_stream"
    SELF_VIDEO = "self_video"


# Core Types
@strawberry.type
class UserNameHistoryType:
    """GraphQL type for user name history."""
    id: int
    user_id: str
    username: str
    display_name: Optional[str]
    global_name: Optional[str]
    effective_from: datetime
    effective_until: Optional[datetime]

    @classmethod
    def from_model(cls, name_history: UserNameHistory) -> "UserNameHistoryType":
        """Create GraphQL type from database model."""
        return cls(
            id=name_history.id,
            user_id=str(name_history.user_id),
            username=name_history.username,
            display_name=name_history.display_name,
            global_name=name_history.global_name,
            effective_from=name_history.effective_from,
            effective_until=name_history.effective_until
        )


@strawberry.type
class MessageActivityType:
    """GraphQL type for message activity."""
    message_id: str
    user_id: str
    channel_id: str
    message_type: MessageTypeEnum
    has_attachments: bool
    has_embeds: bool
    character_count: Optional[int]
    sent_at: datetime

    @classmethod
    def from_model(cls, message: MessageActivity) -> "MessageActivityType":
        """Create GraphQL type from database model."""
        return cls(
            message_id=str(message.message_id),
            user_id=str(message.user_id),
            channel_id=str(message.channel_id),
            message_type=MessageTypeEnum(message.message_type.value),
            has_attachments=message.has_attachments,
            has_embeds=message.has_embeds,
            character_count=message.character_count,
            sent_at=message.sent_at
        )


@strawberry.type
class VoiceStateLogType:
    """GraphQL type for voice state logs."""
    id: int
    session_id: int
    state_type: VoiceStateTypeEnum
    started_at: datetime
    ended_at: Optional[datetime]

    @strawberry.field
    def duration_minutes(self) -> Optional[int]:
        """Calculate duration in minutes if state has ended."""
        if self.started_at and self.ended_at:
            duration = self.ended_at - self.started_at
            return max(0, int(duration.total_seconds() / 60))
        return None

    @classmethod
    def from_model(cls, voice_state: VoiceStateLog) -> "VoiceStateLogType":
        """Create GraphQL type from database model."""
        return cls(
            id=voice_state.id,
            session_id=voice_state.session_id,
            state_type=VoiceStateTypeEnum(voice_state.state_type.value),
            started_at=voice_state.started_at,
            ended_at=voice_state.ended_at
        )


@strawberry.type
class VoiceSessionType:
    """GraphQL type for voice sessions."""
    id: int
    user_id: str
    channel_id: str
    joined_at: datetime
    left_at: Optional[datetime]

    @strawberry.field
    def duration_minutes(self) -> Optional[int]:
        """Calculate session duration in minutes if session has ended."""
        if self.joined_at and self.left_at:
            duration = self.left_at - self.joined_at
            return max(0, int(duration.total_seconds() / 60))
        return None

    @strawberry.field
    def is_ongoing(self) -> bool:
        """Check if the voice session is currently ongoing."""
        return self.left_at is None

    @strawberry.field
    def voice_states(
        self,
        info: strawberry.Info[GraphQLContext, None]
    ) -> List[VoiceStateLogType]:
        """Get voice states for this session."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        voice_states = info.context.discord_db.exec(
            select(VoiceStateLog)
            .where(VoiceStateLog.session_id == self.id)
            .order_by(VoiceStateLog.started_at)
        ).all()

        return [VoiceStateLogType.from_model(state) for state in voice_states]

    @classmethod
    def from_model(cls, session: VoiceSession) -> "VoiceSessionType":
        """Create GraphQL type from database model."""
        return cls(
            id=session.id,
            user_id=str(session.user_id),
            channel_id=str(session.channel_id),
            joined_at=session.joined_at,
            left_at=session.left_at
        )


@strawberry.type
class ActivityLogType:
    """GraphQL type for activity logs."""
    id: int
    user_id: str
    activity_type: ActivityTypeEnum
    activity_name: str
    started_at: datetime
    ended_at: Optional[datetime]

    @strawberry.field
    def duration_minutes(self) -> Optional[int]:
        """Calculate duration in minutes if activity has ended."""
        if self.started_at and self.ended_at:
            duration = self.ended_at - self.started_at
            return max(0, int(duration.total_seconds() / 60))
        return None

    @strawberry.field
    def is_ongoing(self) -> bool:
        """Check if the activity is currently ongoing."""
        return self.ended_at is None

    @classmethod
    def from_model(cls, activity: ActivityLog) -> "ActivityLogType":
        """Create GraphQL type from database model."""
        return cls(
            id=activity.id,
            user_id=str(activity.user_id),
            activity_type=ActivityTypeEnum(activity.activity_type.value),
            activity_name=activity.activity_name,
            started_at=activity.started_at,
            ended_at=activity.ended_at
        )


@strawberry.type
class PresenceStatusLogType:
    """GraphQL type for presence status logs."""
    id: int
    user_id: str
    status_type: DiscordStatusEnum
    set_at: datetime
    changed_at: Optional[datetime]

    @strawberry.field
    def duration_minutes(self) -> Optional[int]:
        """Calculate status duration in minutes if status has changed."""
        if self.set_at and self.changed_at:
            duration = self.changed_at - self.set_at
            return max(0, int(duration.total_seconds() / 60))
        return None

    @strawberry.field
    def is_current(self) -> bool:
        """Check if this is the current status."""
        return self.changed_at is None

    @classmethod
    def from_model(cls, status: PresenceStatusLog) -> "PresenceStatusLogType":
        """Create GraphQL type from database model."""
        return cls(
            id=status.id,
            user_id=str(status.user_id),
            status_type=DiscordStatusEnum(status.status_type.value),
            set_at=status.set_at,
            changed_at=status.changed_at
        )


@strawberry.type
class CustomStatusType:
    """GraphQL type for custom statuses."""
    id: int
    user_id: str
    status_text: Optional[str]
    emoji: Optional[str]
    set_at: datetime

    @strawberry.field
    def has_emoji(self) -> bool:
        """Check if the custom status has an emoji."""
        return self.emoji is not None and len(self.emoji.strip()) > 0

    @strawberry.field
    def has_text(self) -> bool:
        """Check if the custom status has text."""
        return self.status_text is not None and len(self.status_text.strip()) > 0

    @classmethod
    def from_model(cls, status: CustomStatus) -> "CustomStatusType":
        """Create GraphQL type from database model."""
        return cls(
            id=status.id,
            user_id=str(status.user_id),
            status_text=status.status_text,
            emoji=status.emoji,
            set_at=status.set_at
        )


@strawberry.type
class UserStatsType:
    """GraphQL type for user statistics."""
    user_id: str
    total_messages: int
    total_voice_time_minutes: int
    total_activities: int
    most_active_hour: Optional[int]
    favorite_activity: Optional[str]
    most_used_channel: Optional[str]


@strawberry.type
class UserType:
    """GraphQL type for Discord users."""
    user_id: str  # Discord snowflakes are too large for GraphQL Int
    first_seen: datetime

    @strawberry.field
    def current_name(
        self,
        info: strawberry.Info[GraphQLContext, None]
    ) -> Optional[UserNameHistoryType]:
        """Get the current name information for this user."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        current_name = info.context.discord_db.exec(
            select(UserNameHistory)
            .where(UserNameHistory.user_id == self.user_id)
            .where(UserNameHistory.effective_until.is_(None))
        ).first()

        return UserNameHistoryType.from_model(current_name) if current_name else None

    @strawberry.field
    def name_history(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: int = 10
    ) -> List[UserNameHistoryType]:
        """Get name history for this user."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        names = info.context.discord_db.exec(
            select(UserNameHistory)
            .where(UserNameHistory.user_id == self.user_id)
            .order_by(UserNameHistory.effective_from.desc())
            .limit(limit)
        ).all()

        return [UserNameHistoryType.from_model(name) for name in names]

    @strawberry.field
    def messages(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: int = 50,
        channel_id: Optional[int] = None,
        days: Optional[int] = None
    ) -> List[MessageActivityType]:
        """Get messages for this user."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        query = select(MessageActivity).where(MessageActivity.user_id == self.user_id)

        if channel_id:
            query = query.where(MessageActivity.channel_id == channel_id)

        if days:
            from datetime import timedelta
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.where(MessageActivity.sent_at >= start_date)

        messages = info.context.discord_db.exec(
            query.order_by(MessageActivity.sent_at.desc()).limit(limit)
        ).all()

        return [MessageActivityType.from_model(msg) for msg in messages]

    @strawberry.field
    def message_count(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: Optional[int] = None,
        channel_id: Optional[int] = None
    ) -> int:
        """Get total message count for this user."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        query = select(func.count(MessageActivity.message_id)).where(
            MessageActivity.user_id == self.user_id
        )

        if channel_id:
            query = query.where(MessageActivity.channel_id == channel_id)

        if days:
            from datetime import timedelta
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.where(MessageActivity.sent_at >= start_date)

        count = info.context.discord_db.exec(query).first()
        return count or 0

    @strawberry.field
    def voice_sessions(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: int = 50,
        days: Optional[int] = None
    ) -> List[VoiceSessionType]:
        """Get voice sessions for this user."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        query = select(VoiceSession).where(VoiceSession.user_id == self.user_id)

        if days:
            from datetime import timedelta
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.where(VoiceSession.joined_at >= start_date)

        sessions = info.context.discord_db.exec(
            query.order_by(VoiceSession.joined_at.desc()).limit(limit)
        ).all()

        return [VoiceSessionType.from_model(session) for session in sessions]

    @strawberry.field
    def activities(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: int = 50,
        activity_type: Optional[ActivityTypeEnum] = None,
        days: Optional[int] = None
    ) -> List[ActivityLogType]:
        """Get activities for this user."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        query = select(ActivityLog).where(ActivityLog.user_id == self.user_id)

        if activity_type:
            query = query.where(ActivityLog.activity_type == activity_type.value)

        if days:
            from datetime import timedelta
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.where(ActivityLog.started_at >= start_date)

        activities = info.context.discord_db.exec(
            query.order_by(ActivityLog.started_at.desc()).limit(limit)
        ).all()

        return [ActivityLogType.from_model(activity) for activity in activities]

    @strawberry.field
    def presence_status(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: int = 50,
        days: Optional[int] = None
    ) -> List[PresenceStatusLogType]:
        """Get presence status history for this user."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        query = select(PresenceStatusLog).where(PresenceStatusLog.user_id == self.user_id)

        if days:
            from datetime import timedelta
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.where(PresenceStatusLog.set_at >= start_date)

        statuses = info.context.discord_db.exec(
            query.order_by(PresenceStatusLog.set_at.desc()).limit(limit)
        ).all()

        return [PresenceStatusLogType.from_model(status) for status in statuses]

    @strawberry.field
    def custom_statuses(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: int = 50,
        days: Optional[int] = None
    ) -> List[CustomStatusType]:
        """Get custom statuses for this user."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        query = select(CustomStatus).where(CustomStatus.user_id == self.user_id)

        if days:
            from datetime import timedelta
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.where(CustomStatus.set_at >= start_date)

        statuses = info.context.discord_db.exec(
            query.order_by(CustomStatus.set_at.desc()).limit(limit)
        ).all()

        return [CustomStatusType.from_model(status) for status in statuses]

    @strawberry.field
    def stats(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: Optional[int] = None
    ) -> UserStatsType:
        """Get comprehensive statistics for this user."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        # Build base queries
        message_query = select(func.count(MessageActivity.message_id)).where(
            MessageActivity.user_id == self.user_id
        )
        voice_query = select(func.sum(
            func.extract('epoch', VoiceSession.left_at - VoiceSession.joined_at) / 60
        )).where(
            and_(
                VoiceSession.user_id == self.user_id,
                VoiceSession.left_at.isnot(None)
            )
        )
        activity_query = select(func.count(ActivityLog.id)).where(
            ActivityLog.user_id == self.user_id
        )

        # Apply time filter if specified
        if days:
            from datetime import timedelta
            start_date = datetime.utcnow() - timedelta(days=days)
            message_query = message_query.where(MessageActivity.sent_at >= start_date)
            voice_query = voice_query.where(VoiceSession.joined_at >= start_date)
            activity_query = activity_query.where(ActivityLog.started_at >= start_date)

        # Execute queries
        total_messages = info.context.discord_db.exec(message_query).first() or 0
        total_voice_time = info.context.discord_db.exec(voice_query).first() or 0
        total_activities = info.context.discord_db.exec(activity_query).first() or 0

        # Get most active hour
        hour_query = select(
            func.extract('hour', MessageActivity.sent_at).label('hour'),
            func.count(MessageActivity.message_id).label('count')
        ).where(MessageActivity.user_id == self.user_id)

        if days:
            hour_query = hour_query.where(MessageActivity.sent_at >= start_date)

        hour_data = info.context.discord_db.exec(
            hour_query.group_by('hour').order_by(func.count(MessageActivity.message_id).desc()).limit(1)
        ).first()

        most_active_hour = int(hour_data.hour) if hour_data else None

        # Get favorite activity
        activity_query = select(
            ActivityLog.activity_name,
            func.count(ActivityLog.id).label('count')
        ).where(ActivityLog.user_id == self.user_id)

        if days:
            activity_query = activity_query.where(ActivityLog.started_at >= start_date)

        activity_data = info.context.discord_db.exec(
            activity_query.group_by(ActivityLog.activity_name)
            .order_by(func.count(ActivityLog.id).desc()).limit(1)
        ).first()

        favorite_activity = activity_data.activity_name if activity_data else None

        # Get most used channel
        channel_query = select(
            MessageActivity.channel_id,
            func.count(MessageActivity.message_id).label('count')
        ).where(MessageActivity.user_id == self.user_id)

        if days:
            channel_query = channel_query.where(MessageActivity.sent_at >= start_date)

        channel_data = info.context.discord_db.exec(
            channel_query.group_by(MessageActivity.channel_id)
            .order_by(func.count(MessageActivity.message_id).desc()).limit(1)
        ).first()

        most_used_channel = str(channel_data.channel_id) if channel_data else None

        return UserStatsType(
            user_id=str(self.user_id),
            total_messages=total_messages,
            total_voice_time_minutes=int(total_voice_time),
            total_activities=total_activities,
            most_active_hour=most_active_hour,
            favorite_activity=favorite_activity,
            most_used_channel=most_used_channel
        )

    @classmethod
    def from_model(cls, user: User) -> "UserType":
        """Create GraphQL type from database model."""
        return cls(
            user_id=str(user.user_id),
            first_seen=user.first_seen
        )


# Statistics Types
@strawberry.type
class ChannelStatsType:
    """GraphQL type for channel statistics."""
    channel_id: str
    total_messages: int
    unique_users: int
    most_active_user_id: Optional[str]


@strawberry.type
class ServerStatsType:
    """GraphQL type for server-wide statistics."""
    total_users: int
    total_messages: int
    total_voice_time_hours: float
    total_activities: int
    most_active_channel_id: Optional[str]
    most_common_activity: Optional[str]
