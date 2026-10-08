"""
GraphQL types for Discord data.

These types expose the Discord database models for querying user activity,
messages, voice sessions, and other Discord-related data.
"""

from typing import Annotated, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from enum import Enum
import strawberry
from sqlmodel import select, func, and_
from sqlalchemy import case
from app.graphql.arguments import Limit, ChannelId, Days, StartDate, EndDate
from app.graphql.context import GraphQLContext
from app.discord.models import (
    User, Channel, MessageActivity, VoiceSession, VoiceStateLog,
    PresenceStatusLog, ActivityLog, CustomStatus, UserNameHistory
)


def parse_date_filter(
    days: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Convert flexible date filter params into a (start, end) datetime pair.
    start_date/end_date (ISO strings) take precedence over days."""
    start = None
    end = None
    if start_date:
        start = datetime.fromisoformat(start_date)
    if end_date:
        end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
    if start is None and days is not None:
        start = datetime.now(timezone.utc) - timedelta(days=days)
    return start, end


# Enums
@strawberry.enum(name="MessageType", description=(
    "Discord message type. DEFAULT is a normal message and REPLY a reply, "
    "most others are system messages."
))
class MessageTypeEnum(Enum):
    DEFAULT = strawberry.enum_value("default", description="Normal message")
    RECIPIENT_ADD = strawberry.enum_value(
        "recipient_add", description="Someone was added to a thread"
    )
    RECIPIENT_REMOVE = strawberry.enum_value(
        "recipient_remove", description="Someone was removed from or left a thread"
    )
    CALL = strawberry.enum_value("call", description="A call was started")
    CHANNEL_NAME_CHANGE = strawberry.enum_value(
        "channel_name_change", description="A thread was renamed"
    )
    CHANNEL_ICON_CHANGE = strawberry.enum_value(
        "channel_icon_change", description="A group DM icon was changed"
    )
    CHANNEL_PINNED_MESSAGE = strawberry.enum_value(
        "channel_pinned_message", description="Someone pinned a message"
    )
    USER_JOIN = strawberry.enum_value("user_join", description="Welcome message for a new member")
    GUILD_BOOST = strawberry.enum_value("guild_boost", description="Someone boosted the server")
    GUILD_BOOST_TIER_1 = strawberry.enum_value(
        "guild_boost_tier_1", description="A boost brought the server to level 1"
    )
    GUILD_BOOST_TIER_2 = strawberry.enum_value(
        "guild_boost_tier_2", description="A boost brought the server to level 2"
    )
    GUILD_BOOST_TIER_3 = strawberry.enum_value(
        "guild_boost_tier_3", description="A boost brought the server to level 3"
    )
    CHANNEL_FOLLOW_ADD = strawberry.enum_value(
        "channel_follow_add", description="An announcement channel was followed into this channel"
    )
    GUILD_STREAM = strawberry.enum_value(
        "guild_stream", description="Someone went live in a voice channel"
    )
    GUILD_DISCOVERY_DISQUALIFIED = strawberry.enum_value(
        "guild_discovery_disqualified", description="The server was removed from Server Discovery"
    )
    GUILD_DISCOVERY_REQUALIFIED = strawberry.enum_value(
        "guild_discovery_requalified", description="The server can be in Server Discovery again"
    )
    GUILD_DISCOVERY_GRACE_PERIOD_INITIAL_WARNING = strawberry.enum_value(
        "guild_discovery_grace_period_initial_warning",
        description="First warning that the server may be removed from Server Discovery",
    )
    GUILD_DISCOVERY_GRACE_PERIOD_FINAL_WARNING = strawberry.enum_value(
        "guild_discovery_grace_period_final_warning",
        description="Last warning that the server may be removed from Server Discovery",
    )
    THREAD_CREATED = strawberry.enum_value("thread_created", description="Someone started a thread")
    REPLY = strawberry.enum_value("reply", description="Reply to another message")
    CHAT_INPUT_COMMAND = strawberry.enum_value(
        "chat_input_command", description="A bot's answer to a slash command"
    )
    THREAD_STARTER_MESSAGE = strawberry.enum_value(
        "thread_starter_message",
        description="First message of a thread, showing the message it was started from",
    )
    GUILD_INVITE_REMINDER = strawberry.enum_value(
        "guild_invite_reminder", description="Reminder to invite people to the server"
    )
    CONTEXT_MENU_COMMAND = strawberry.enum_value(
        "context_menu_command", description="A bot's answer to a right-click (context menu) command"
    )
    AUTO_MODERATION_ACTION = strawberry.enum_value(
        "auto_moderation_action", description="AutoMod blocked or flagged a message"
    )
    ROLE_SUBSCRIPTION_PURCHASE = strawberry.enum_value(
        "role_subscription_purchase", description="Someone bought or renewed a role subscription"
    )
    INTERACTION_PREMIUM_UPSELL = strawberry.enum_value(
        "interaction_premium_upsell", description="A bot asked for a premium purchase"
    )
    STAGE_START = strawberry.enum_value("stage_start", description="A stage started")
    STAGE_END = strawberry.enum_value("stage_end", description="A stage ended")
    STAGE_SPEAKER = strawberry.enum_value(
        "stage_speaker", description="Someone became a speaker on a stage"
    )
    STAGE_RAISE_HAND = strawberry.enum_value(
        "stage_raise_hand", description="Someone raised their hand on a stage"
    )
    STAGE_TOPIC = strawberry.enum_value("stage_topic", description="The topic of a stage changed")
    GUILD_APPLICATION_PREMIUM_SUBSCRIPTION = strawberry.enum_value(
        "guild_application_premium_subscription",
        description="Someone bought a bot's premium subscription for the server",
    )
    GUILD_INCIDENT_ALERT_MODE_ENABLED = strawberry.enum_value(
        "guild_incident_alert_mode_enabled",
        description="Moderators paused invites or DMs, e.g. because of a raid",
    )
    GUILD_INCIDENT_ALERT_MODE_DISABLED = strawberry.enum_value(
        "guild_incident_alert_mode_disabled", description="Moderators resumed invites or DMs"
    )
    GUILD_INCIDENT_REPORT_RAID = strawberry.enum_value(
        "guild_incident_report_raid", description="Someone reported a raid"
    )
    GUILD_INCIDENT_REPORT_FALSE_ALARM = strawberry.enum_value(
        "guild_incident_report_false_alarm",
        description="A raid report turned out to be a false alarm",
    )
    PURCHASE_NOTIFICATION = strawberry.enum_value(
        "purchase_notification", description="Someone bought something in the server shop"
    )
    POLL_RESULT = strawberry.enum_value(
        "poll_result", description="A poll ended and shows its results"
    )
    EMOJI_ADDED = strawberry.enum_value(
        "emoji_added", description="A new emoji was added to the server"
    )


@strawberry.enum(
    name="ActivityType",
    description="What kind of activity a user is doing, as shown in Discord.",
)
class ActivityTypeEnum(Enum):
    COMPETING = strawberry.enum_value("competing", description="Competing in something")
    CUSTOM = strawberry.enum_value("custom", description="Custom status")
    LISTENING = strawberry.enum_value("listening", description="Listening, e.g. to Spotify")
    PLAYING = strawberry.enum_value("playing", description="Playing a game")
    STREAMING = strawberry.enum_value("streaming", description="Streaming, e.g. on Twitch")
    WATCHING = strawberry.enum_value("watching", description="Watching something")


@strawberry.enum(name="DiscordStatus", description="Online status of a user.")
class DiscordStatusEnum(Enum):
    ONLINE = strawberry.enum_value("online", description="Online")
    IDLE = strawberry.enum_value("idle", description="Idle (away)")
    DND = strawberry.enum_value("dnd", description="Do not disturb")
    OFFLINE = strawberry.enum_value("offline", description="Offline or invisible")
    STREAMING = strawberry.enum_value("streaming", description="Streaming, e.g. on Twitch")


@strawberry.enum(
    name="VoiceStateType",
    description="Voice channel state, like being muted or streaming.",
)
class VoiceStateTypeEnum(Enum):
    DEAF = strawberry.enum_value("deaf", description="Deafened by a moderator")
    MUTE = strawberry.enum_value("mute", description="Muted by a moderator")
    SELF_DEAF = strawberry.enum_value("self_deaf", description="Deafened themselves")
    SELF_MUTE = strawberry.enum_value("self_mute", description="Muted themselves")
    SELF_STREAM = strawberry.enum_value("self_stream", description="Sharing their screen (Go Live)")
    SELF_VIDEO = strawberry.enum_value("self_video", description="Camera on")


# Core Types
@strawberry.type(name="UserName", description=(
    "One name a user had for some time. "
    "A new entry starts whenever their username, display name or global name changes."
))
class UserNameHistoryType:
    id: int = strawberry.field(description="Internal ID of this entry.")
    user_id: str = strawberry.field(description="Discord user ID.")
    username: str = strawberry.field(description="Unique Discord username (the @ handle).")
    display_name: Optional[str] = strawberry.field(description="Name shown on this server.")
    global_name: Optional[str] = strawberry.field(
        description="Display name set on the Discord account."
    )
    effective_from: datetime = strawberry.field(
        description="When the user started using this name."
    )
    effective_until: Optional[datetime] = strawberry.field(
        description="When the name changed again. null means it is the current name."
    )

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


@strawberry.type(name="Message", description="A sent message. The content itself is never stored.")
class MessageActivityType:
    message_id: str = strawberry.field(description="Discord message ID.")
    user_id: str = strawberry.field(description="Discord user ID of the author.")
    channel_id: str = strawberry.field(description="Discord channel ID.")
    message_type: MessageTypeEnum = strawberry.field(
        description="Normal message, reply or a kind of system message."
    )
    has_attachments: bool = strawberry.field(description="Whether files or images were attached.")
    has_embeds: bool = strawberry.field(description="Whether it had embeds, e.g. link previews.")
    character_count: Optional[int] = strawberry.field(
        description="Length of the text in characters."
    )
    sent_at: datetime = strawberry.field(description="When the message was sent.")

    @strawberry.field(description="Channel name. null if the bot never saw the channel.")
    def channel_name(self, info: strawberry.Info[GraphQLContext, None]) -> Optional[str]:
        return info.context.channel_name(self.channel_id)

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


@strawberry.type(
    name="VoiceStateLog",
    description="A period during a voice session in which the user was e.g. muted or streaming.",
)
class VoiceStateLogType:
    id: int = strawberry.field(description="Internal ID of this entry.")
    session_id: int = strawberry.field(description="ID of the voice session this belongs to.")
    state_type: VoiceStateTypeEnum = strawberry.field(description="Which state, e.g. SELF_MUTE.")
    started_at: datetime = strawberry.field(description="When the state started.")
    ended_at: Optional[datetime] = strawberry.field(
        description="null while the state is still active."
    )

    @strawberry.field(
        description="How long the state lasted, in whole minutes. null while still active."
    )
    def duration_minutes(self) -> Optional[int]:
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


@strawberry.type(
    name="VoiceSession",
    description="One visit to a voice channel, from joining to leaving.",
)
class VoiceSessionType:
    id: int = strawberry.field(description="Internal ID of this visit.")
    user_id: str = strawberry.field(description="Discord user ID.")
    channel_id: str = strawberry.field(description="Discord ID of the voice channel.")
    joined_at: datetime = strawberry.field(description="When the user joined the channel.")
    left_at: Optional[datetime] = strawberry.field(
        description="null while the user is still in the channel."
    )

    @strawberry.field(
        description="How long the visit lasted, in whole minutes. null while still in the channel."
    )
    def duration_minutes(self) -> Optional[int]:
        if self.joined_at and self.left_at:
            duration = self.left_at - self.joined_at
            return max(0, int(duration.total_seconds() / 60))
        return None

    @strawberry.field(description="Whether the user is still in the channel.")
    def is_ongoing(self) -> bool:
        return self.left_at is None

    @strawberry.field(description="Channel name. null if the bot never saw the channel.")
    def channel_name(self, info: strawberry.Info[GraphQLContext, None]) -> Optional[str]:
        return info.context.channel_name(self.channel_id)

    @strawberry.field(description="Muting, streaming etc. during this visit, in order.")
    def voice_states(
        self,
        info: strawberry.Info[GraphQLContext, None]
    ) -> List[VoiceStateLogType]:
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


@strawberry.type(
    name="Activity",
    description="One activity of a user, e.g. a game session or Spotify listening.",
)
class ActivityLogType:
    id: int = strawberry.field(description="Internal ID of this entry.")
    user_id: str = strawberry.field(description="Discord user ID.")
    activity_type: ActivityTypeEnum = strawberry.field(description="Playing, listening etc.")
    activity_name: str = strawberry.field(
        description='Name of the game, app etc., e.g. "Minecraft".'
    )
    started_at: datetime = strawberry.field(description="When the activity started.")
    ended_at: Optional[datetime] = strawberry.field(description="null while still going on.")

    @strawberry.field(
        description="How long it lasted, in whole minutes. null while still going on."
    )
    def duration_minutes(self) -> Optional[int]:
        if self.started_at and self.ended_at:
            duration = self.ended_at - self.started_at
            return max(0, int(duration.total_seconds() / 60))
        return None

    @strawberry.field(description="Whether the activity is still going on.")
    def is_ongoing(self) -> bool:
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


@strawberry.type(
    name="PresenceStatus",
    description="A period in which a user had one online status.",
)
class PresenceStatusLogType:
    id: int = strawberry.field(description="Internal ID of this entry.")
    user_id: str = strawberry.field(description="Discord user ID.")
    status_type: DiscordStatusEnum = strawberry.field(description="Online, idle etc.")
    set_at: datetime = strawberry.field(description="When the user got this status.")
    changed_at: Optional[datetime] = strawberry.field(
        description="When the status changed again. null for the current status."
    )

    @strawberry.field(
        description="How long the status lasted, in whole minutes. null for the current status."
    )
    def duration_minutes(self) -> Optional[int]:
        if self.set_at and self.changed_at:
            duration = self.changed_at - self.set_at
            return max(0, int(duration.total_seconds() / 60))
        return None

    @strawberry.field(description="Whether this is the user's current status.")
    def is_current(self) -> bool:
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


@strawberry.type(
    name="CustomStatus",
    description="A custom status a user set (the text and emoji shown under their name).",
)
class CustomStatusType:
    id: int = strawberry.field(description="Internal ID of this entry.")
    user_id: str = strawberry.field(description="Discord user ID.")
    status_text: Optional[str] = strawberry.field(description="The text. null if there is none.")
    emoji: Optional[str] = strawberry.field(
        description="Unicode emoji, or the name of a custom emoji. null if there is none."
    )
    set_at: datetime = strawberry.field(description="When the user set this status.")

    @strawberry.field(description="Whether the status has an emoji.")
    def has_emoji(self) -> bool:
        return self.emoji is not None and len(self.emoji.strip()) > 0

    @strawberry.field(description="Whether the status has text.")
    def has_text(self) -> bool:
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


@strawberry.type(name="UserStats", description="Summary of one user's activity.")
class UserStatsType:
    user_id: str = strawberry.field(description="Discord user ID.")
    total_messages: int = strawberry.field(description="Number of messages sent.")
    total_voice_time_minutes: int = strawberry.field(
        description="Total time in voice channels. Only finished visits count."
    )
    total_activities: int = strawberry.field(description="Number of activities started.")
    most_active_hour: Optional[int] = strawberry.field(
        description="Hour of the day (0-23, UTC) in which the user sends the most messages."
    )
    favorite_activity: Optional[str] = strawberry.field(
        description="Activity the user started most often."
    )
    most_used_channel: Optional[str] = strawberry.field(
        description="ID of the channel the user sends the most messages in."
    )

    @strawberry.field(description="Name of the channel the user sends the most messages in.")
    def most_used_channel_name(self, info: strawberry.Info[GraphQLContext, None]) -> Optional[str]:
        return info.context.channel_name(self.most_used_channel) if self.most_used_channel else None


@strawberry.type(
    name="UniqueActivity",
    description="An activity a user has done, added up over all times.",
)
class UniqueActivityType:
    activity_name: str = strawberry.field(
        description='Name of the game, app etc., e.g. "Minecraft".'
    )
    total_hours: float = strawberry.field(
        description="Total hours. Activities still going on count as 0."
    )
    count: int = strawberry.field(description="How often the user started it.")


@strawberry.type(name="User", description="A Discord user the bot has seen on the server.")
class UserType:
    user_id: str = strawberry.field(description="Discord user ID.")
    first_seen: datetime = strawberry.field(description="When the user joined the server.")

    @strawberry.field(description="The user's current names.")
    def current_name(
        self,
        info: strawberry.Info[GraphQLContext, None]
    ) -> Optional[UserNameHistoryType]:
        current_name = info.context.discord_db.exec(
            select(UserNameHistory)
            .where(UserNameHistory.user_id == int(self.user_id))
            .where(UserNameHistory.effective_until.is_(None))
        ).first()

        return UserNameHistoryType.from_model(current_name) if current_name else None

    @strawberry.field(description="All names the user had, newest first.")
    def name_history(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: Limit = 10
    ) -> List[UserNameHistoryType]:
        names = info.context.discord_db.exec(
            select(UserNameHistory)
            .where(UserNameHistory.user_id == int(self.user_id))
            .order_by(UserNameHistory.effective_from.desc())
            .limit(limit)
        ).all()

        return [UserNameHistoryType.from_model(name) for name in names]

    @strawberry.field(description="The user's messages, newest first.")
    def messages(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: Limit = 50,
        channel_id: ChannelId = None,
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[MessageActivityType]:
        query = select(MessageActivity).where(MessageActivity.user_id == int(self.user_id))
        if channel_id:
            query = query.where(MessageActivity.channel_id == int(channel_id))

        start, end = parse_date_filter(days, start_date, end_date)
        if start:
            query = query.where(MessageActivity.sent_at >= start)
        if end:
            query = query.where(MessageActivity.sent_at <= end)

        messages = info.context.discord_db.exec(
            query.order_by(MessageActivity.sent_at.desc()).limit(limit)
        ).all()

        return [MessageActivityType.from_model(msg) for msg in messages]

    @strawberry.field(description="Number of messages the user sent.")
    def message_count(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: Days = None,
        channel_id: ChannelId = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> int:
        query = select(func.count(MessageActivity.message_id)).where(
            MessageActivity.user_id == int(self.user_id)
        )
        if channel_id:
            query = query.where(MessageActivity.channel_id == int(channel_id))

        start, end = parse_date_filter(days, start_date, end_date)
        if start:
            query = query.where(MessageActivity.sent_at >= start)
        if end:
            query = query.where(MessageActivity.sent_at <= end)

        count = info.context.discord_db.exec(query).first()
        return count or 0

    @strawberry.field(description="The user's voice channel visits, newest first.")
    def voice_sessions(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: Limit = 50,
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[VoiceSessionType]:
        query = select(VoiceSession).where(VoiceSession.user_id == int(self.user_id))

        start, end = parse_date_filter(days, start_date, end_date)
        if start:
            query = query.where(VoiceSession.joined_at >= start)
        if end:
            query = query.where(VoiceSession.joined_at <= end)

        sessions = info.context.discord_db.exec(
            query.order_by(VoiceSession.joined_at.desc()).limit(limit)
        ).all()

        return [VoiceSessionType.from_model(session) for session in sessions]

    @strawberry.field(description="The user's activities, newest first.")
    def activities(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: Limit = 50,
        activity_type: Annotated[Optional[ActivityTypeEnum], strawberry.argument(
            description="Only activities of this type."
        )] = None,
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[ActivityLogType]:
        query = select(ActivityLog).where(ActivityLog.user_id == int(self.user_id))
        if activity_type:
            query = query.where(ActivityLog.activity_type == activity_type.value)

        start, end = parse_date_filter(days, start_date, end_date)
        if start:
            query = query.where(ActivityLog.started_at >= start)
        if end:
            query = query.where(ActivityLog.started_at <= end)

        activities = info.context.discord_db.exec(
            query.order_by(ActivityLog.started_at.desc()).limit(limit)
        ).all()

        return [ActivityLogType.from_model(activity) for activity in activities]

    @strawberry.field(description="The user's online status history, newest first.")
    def presence_status(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: Limit = 50,
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[PresenceStatusLogType]:
        query = select(PresenceStatusLog).where(PresenceStatusLog.user_id == int(self.user_id))

        start, end = parse_date_filter(days, start_date, end_date)
        if start:
            query = query.where(PresenceStatusLog.set_at >= start)
        if end:
            query = query.where(PresenceStatusLog.set_at <= end)

        statuses = info.context.discord_db.exec(
            query.order_by(PresenceStatusLog.set_at.desc()).limit(limit)
        ).all()

        return [PresenceStatusLogType.from_model(status) for status in statuses]

    @strawberry.field(description="The user's custom statuses, newest first.")
    def custom_statuses(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: Limit = 50,
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[CustomStatusType]:
        query = select(CustomStatus).where(CustomStatus.user_id == int(self.user_id))

        start, end = parse_date_filter(days, start_date, end_date)
        if start:
            query = query.where(CustomStatus.set_at >= start)
        if end:
            query = query.where(CustomStatus.set_at <= end)

        statuses = info.context.discord_db.exec(
            query.order_by(CustomStatus.set_at.desc()).limit(limit)
        ).all()

        return [CustomStatusType.from_model(status) for status in statuses]

    @strawberry.field(
        description="Every activity the user has done, with total hours, most hours first."
    )
    def unique_activities(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[UniqueActivityType]:
        hours_expr = func.coalesce(
            func.sum(
                case(
                    (ActivityLog.ended_at.isnot(None),
                     func.extract("epoch", ActivityLog.ended_at - ActivityLog.started_at) / 3600),
                    else_=0,
                )
            ), 0.0
        )

        query = select(
            ActivityLog.activity_name,
            func.count(ActivityLog.id).label("cnt"),
            hours_expr.label("hours"),
        ).where(ActivityLog.user_id == int(self.user_id))

        start, end = parse_date_filter(days, start_date, end_date)
        if start:
            query = query.where(ActivityLog.started_at >= start)
        if end:
            query = query.where(ActivityLog.started_at <= end)

        query = query.group_by(ActivityLog.activity_name).order_by(hours_expr.desc())

        results = info.context.discord_db.exec(query).all()
        return [
            UniqueActivityType(
                activity_name=r.activity_name,
                total_hours=round(float(r.hours or 0), 2),
                count=r.cnt,
            )
            for r in results
        ]

    @strawberry.field(description="Summary of the user's activity.")
    def stats(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> UserStatsType:
        start, end = parse_date_filter(days, start_date, end_date)

        message_query = select(func.count(MessageActivity.message_id)).where(
            MessageActivity.user_id == int(self.user_id)
        )
        voice_query = select(func.sum(
            func.extract('epoch', VoiceSession.left_at - VoiceSession.joined_at) / 60
        )).where(
            and_(
                VoiceSession.user_id == int(self.user_id),
                VoiceSession.left_at.isnot(None)
            )
        )
        activity_query = select(func.count(ActivityLog.id)).where(
            ActivityLog.user_id == int(self.user_id)
        )

        if start:
            message_query = message_query.where(MessageActivity.sent_at >= start)
            voice_query = voice_query.where(VoiceSession.joined_at >= start)
            activity_query = activity_query.where(ActivityLog.started_at >= start)
        if end:
            message_query = message_query.where(MessageActivity.sent_at <= end)
            voice_query = voice_query.where(VoiceSession.joined_at <= end)
            activity_query = activity_query.where(ActivityLog.started_at <= end)

        total_messages = info.context.discord_db.exec(message_query).first() or 0
        total_voice_time = info.context.discord_db.exec(voice_query).first() or 0
        total_activities = info.context.discord_db.exec(activity_query).first() or 0

        hour_query = select(
            func.extract('hour', MessageActivity.sent_at).label('hour'),
            func.count(MessageActivity.message_id).label('count')
        ).where(MessageActivity.user_id == int(self.user_id))
        if start:
            hour_query = hour_query.where(MessageActivity.sent_at >= start)
        if end:
            hour_query = hour_query.where(MessageActivity.sent_at <= end)

        hour_data = info.context.discord_db.exec(
            hour_query.group_by('hour').order_by(func.count(MessageActivity.message_id).desc()).limit(1)
        ).first()
        most_active_hour = int(hour_data.hour) if hour_data else None

        fav_activity_query = select(
            ActivityLog.activity_name,
            func.count(ActivityLog.id).label('count')
        ).where(ActivityLog.user_id == int(self.user_id))
        if start:
            fav_activity_query = fav_activity_query.where(ActivityLog.started_at >= start)
        if end:
            fav_activity_query = fav_activity_query.where(ActivityLog.started_at <= end)

        activity_data = info.context.discord_db.exec(
            fav_activity_query.group_by(ActivityLog.activity_name)
            .order_by(func.count(ActivityLog.id).desc()).limit(1)
        ).first()
        favorite_activity = activity_data.activity_name if activity_data else None

        channel_query = select(
            MessageActivity.channel_id,
            func.count(MessageActivity.message_id).label('count')
        ).where(MessageActivity.user_id == int(self.user_id))
        if start:
            channel_query = channel_query.where(MessageActivity.sent_at >= start)
        if end:
            channel_query = channel_query.where(MessageActivity.sent_at <= end)

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


@strawberry.type(name="Channel", description="A Discord channel or thread.")
class ChannelType:
    channel_id: str = strawberry.field(description="Discord channel ID.")
    name: str = strawberry.field(
        description="Current channel name, or the last known one if deleted."
    )
    channel_type: str = strawberry.field(
        description="Discord channel type, e.g. text, voice, stage_voice, category, public_thread."
    )
    parent_id: Optional[str] = strawberry.field(
        description="Category of a channel, or the channel a thread belongs to."
    )
    deleted_at: Optional[datetime] = strawberry.field(
        description="When the channel was deleted. null if it still exists."
    )

    @classmethod
    def from_model(cls, channel: Channel) -> "ChannelType":
        """Create GraphQL type from database model."""
        return cls(
            channel_id=str(channel.channel_id),
            name=channel.name,
            channel_type=channel.channel_type,
            parent_id=str(channel.parent_id) if channel.parent_id else None,
            deleted_at=channel.deleted_at,
        )


# Statistics Types
@strawberry.type(name="ChannelStats", description="Message statistics of one text channel.")
class ChannelStatsType:
    channel_id: str = strawberry.field(description="Discord channel ID.")
    total_messages: int = strawberry.field(description="Number of messages sent in it.")
    unique_users: int = strawberry.field(description="Number of different users who wrote in it.")
    most_active_user_id: Optional[str] = strawberry.field(
        description="ID of the user who wrote the most. Not affected by the userId filter."
    )

    @strawberry.field(description="Channel name. null if the bot never saw the channel.")
    def channel_name(self, info: strawberry.Info[GraphQLContext, None]) -> Optional[str]:
        return info.context.channel_name(self.channel_id)


@strawberry.type(name="ServerStats", description="Totals for the whole server.")
class ServerStatsType:
    total_users: int = strawberry.field(
        description="Number of users who joined in the selected period."
    )
    total_messages: int = strawberry.field(description="Number of messages sent.")
    total_voice_time_hours: float = strawberry.field(
        description="Hours spent in voice, all users added up. Only finished visits count."
    )
    total_activities: int = strawberry.field(description="Number of activities started.")
    most_active_channel_id: Optional[str] = strawberry.field(
        description="ID of the text channel with the most messages."
    )
    most_common_activity: Optional[str] = strawberry.field(
        description="Activity started most often."
    )

    @strawberry.field(description="Name of the text channel with the most messages.")
    def most_active_channel_name(self, info: strawberry.Info[GraphQLContext, None]) -> Optional[str]:
        if not self.most_active_channel_id:
            return None
        return info.context.channel_name(self.most_active_channel_id)


@strawberry.type(name="DailyStats", description="Activity on one day.")
class DailyStatsType:
    date: str = strawberry.field(description='The day (UTC), e.g. "2026-01-31".')
    message_count: int = strawberry.field(description="Number of messages sent.")
    voice_hours: float = strawberry.field(
        description=(
            "Hours spent in voice, all users added up. "
            "Only finished visits count, by the day they started."
        )
    )
    activity_count: int = strawberry.field(description="Number of activities started.")
    active_users: int = strawberry.field(
        description="Number of users who sent at least one message."
    )


@strawberry.type(
    name="HourlyDistribution",
    description="Number of messages sent in one hour of the day.",
)
class HourlyDistributionType:
    hour: int = strawberry.field(description="Hour of the day, 0-23 (UTC).")
    count: int = strawberry.field(description="Number of messages sent in this hour.")


@strawberry.type(
    name="TopItem",
    description="A ranked channel or activity. See the query for what name and count mean.",
)
class TopItemType:
    name: str = strawberry.field(description="Channel or activity name.")
    count: int = strawberry.field(description="Number of channel visits or activity starts.")
    hours: float = strawberry.field(default=0.0, description="Total hours.")


@strawberry.type(
    name="TopUser",
    description="A ranked user. See topUsers for how the score is calculated.",
)
class TopUserType:
    user_id: str = strawberry.field(description="Discord user ID.")
    name: str = strawberry.field(description="Current display name.")
    message_count: int = strawberry.field(description="Number of messages sent.")
    voice_hours: float = strawberry.field(
        description="Hours spent in voice. Only finished visits count."
    )
    score: float = strawberry.field(default=0.0, description="Voice minutes + messages.")


@strawberry.type(
    name="TopVoiceStateUser",
    description="A user and how long they spent in one voice state.",
)
class TopVoiceStateUserType:
    state_type: VoiceStateTypeEnum = strawberry.field(description="Which state, e.g. SELF_MUTE.")
    user_id: str = strawberry.field(description="Discord user ID.")
    name: str = strawberry.field(description="Current display name.")
    hours: float = strawberry.field(description="Hours spent in this state.")


@strawberry.type(
    name="VoiceConnection",
    description="Two users and how long they were in the same voice channel at the same time.",
)
class VoiceConnectionType:
    user1_id: str = strawberry.field(description="Discord user ID of the first user.")
    user1_name: str = strawberry.field(description="Current display name of the first user.")
    user2_id: str = strawberry.field(description="Discord user ID of the second user.")
    user2_name: str = strawberry.field(description="Current display name of the second user.")
    shared_hours: float = strawberry.field(description="Hours both were in the same channel.")
    session_count: int = strawberry.field(
        description="Number of times they were in a channel together."
    )
