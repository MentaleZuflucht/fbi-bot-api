"""
GraphQL resolvers for Discord data.

These resolvers handle queries for Discord user data, messages, voice sessions,
and other Discord-related information with proper authentication.
"""

from typing import Optional, List
from datetime import datetime, timedelta
import strawberry
from sqlmodel import select, func, and_, or_
from app.graphql.context import GraphQLContext
from app.graphql.types.discord import (
    UserType, MessageActivityType, VoiceSessionType, ActivityLogType,
    PresenceStatusLogType, CustomStatusType, ChannelStatsType, ServerStatsType,
    ActivityTypeEnum, MessageTypeEnum, DiscordStatusEnum
)
from app.discord.models import (
    User, MessageActivity, VoiceSession, ActivityLog,
    PresenceStatusLog, CustomStatus, UserNameHistory
)


@strawberry.type
class Query:
    """GraphQL queries for Discord data."""

    @strawberry.field
    def user(
        self,
        info: strawberry.Info[GraphQLContext, None],
        user_id: str
    ) -> Optional[UserType]:
        """Get a specific Discord user by ID."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        user = info.context.discord_db.exec(
            select(User).where(User.user_id == int(user_id))
        ).first()

        return UserType.from_model(user) if user else None

    @strawberry.field
    def users(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None
    ) -> List[UserType]:
        """Get a list of Discord users."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        query = select(User)

        # If searching, join with name history and filter
        if search:
            query = query.join(UserNameHistory).where(
                and_(
                    UserNameHistory.effective_until.is_(None),  # Current name only
                    or_(
                        UserNameHistory.username.ilike(f"%{search}%"),
                        UserNameHistory.display_name.ilike(f"%{search}%"),
                        UserNameHistory.global_name.ilike(f"%{search}%")
                    )
                )
            )

        users = info.context.discord_db.exec(
            query.order_by(User.first_seen.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return [UserType.from_model(user) for user in users]

    @strawberry.field
    def messages(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        message_type: Optional[MessageTypeEnum] = None,
        days: Optional[int] = None
    ) -> List[MessageActivityType]:
        """Get messages with optional filtering."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        query = select(MessageActivity)

        # Apply filters
        if user_id:
            query = query.where(MessageActivity.user_id == int(user_id))
        if channel_id:
            query = query.where(MessageActivity.channel_id == int(channel_id))
        if message_type:
            query = query.where(MessageActivity.message_type == message_type.value)
        if days:
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.where(MessageActivity.sent_at >= start_date)

        messages = info.context.discord_db.exec(
            query.order_by(MessageActivity.sent_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return [MessageActivityType.from_model(msg) for msg in messages]

    @strawberry.field
    def voice_sessions(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        days: Optional[int] = None,
        ongoing_only: bool = False
    ) -> List[VoiceSessionType]:
        """Get voice sessions with optional filtering."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        query = select(VoiceSession)

        # Apply filters
        if user_id:
            query = query.where(VoiceSession.user_id == int(user_id))
        if channel_id:
            query = query.where(VoiceSession.channel_id == int(channel_id))
        if days:
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.where(VoiceSession.joined_at >= start_date)
        if ongoing_only:
            query = query.where(VoiceSession.left_at.is_(None))

        sessions = info.context.discord_db.exec(
            query.order_by(VoiceSession.joined_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return [VoiceSessionType.from_model(session) for session in sessions]

    @strawberry.field
    def activities(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[int] = None,
        activity_type: Optional[ActivityTypeEnum] = None,
        activity_name: Optional[str] = None,
        days: Optional[int] = None,
        ongoing_only: bool = False
    ) -> List[ActivityLogType]:
        """Get activities with optional filtering."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        query = select(ActivityLog)

        # Apply filters
        if user_id:
            query = query.where(ActivityLog.user_id == int(user_id))
        if activity_type:
            query = query.where(ActivityLog.activity_type == activity_type.value)
        if activity_name:
            query = query.where(ActivityLog.activity_name.ilike(f"%{activity_name}%"))
        if days:
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.where(ActivityLog.started_at >= start_date)
        if ongoing_only:
            query = query.where(ActivityLog.ended_at.is_(None))

        activities = info.context.discord_db.exec(
            query.order_by(ActivityLog.started_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return [ActivityLogType.from_model(activity) for activity in activities]

    @strawberry.field
    def presence_status(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[int] = None,
        status_type: Optional[DiscordStatusEnum] = None,
        days: Optional[int] = None,
        current_only: bool = False
    ) -> List[PresenceStatusLogType]:
        """Get presence status logs with optional filtering."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        query = select(PresenceStatusLog)

        # Apply filters
        if user_id:
            query = query.where(PresenceStatusLog.user_id == int(user_id))
        if status_type:
            query = query.where(PresenceStatusLog.status_type == status_type.value)
        if days:
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.where(PresenceStatusLog.set_at >= start_date)
        if current_only:
            query = query.where(PresenceStatusLog.changed_at.is_(None))

        statuses = info.context.discord_db.exec(
            query.order_by(PresenceStatusLog.set_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return [PresenceStatusLogType.from_model(status) for status in statuses]

    @strawberry.field
    def custom_statuses(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[int] = None,
        has_text: Optional[bool] = None,
        has_emoji: Optional[bool] = None,
        days: Optional[int] = None
    ) -> List[CustomStatusType]:
        """Get custom statuses with optional filtering."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        query = select(CustomStatus)

        # Apply filters
        if user_id:
            query = query.where(CustomStatus.user_id == int(user_id))
        if has_text is not None:
            if has_text:
                query = query.where(CustomStatus.status_text.isnot(None))
            else:
                query = query.where(CustomStatus.status_text.is_(None))
        if has_emoji is not None:
            if has_emoji:
                query = query.where(CustomStatus.emoji.isnot(None))
            else:
                query = query.where(CustomStatus.emoji.is_(None))
        if days:
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.where(CustomStatus.set_at >= start_date)

        statuses = info.context.discord_db.exec(
            query.order_by(CustomStatus.set_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return [CustomStatusType.from_model(status) for status in statuses]

    @strawberry.field
    def channel_stats(
        self,
        info: strawberry.Info[GraphQLContext, None],
        channel_id: Optional[str] = None,
        limit: int = 10,
        days: Optional[int] = None
    ) -> List[ChannelStatsType]:
        """Get channel statistics."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        # Base query for channel message stats
        query = select(
            MessageActivity.channel_id,
            func.count(MessageActivity.message_id).label('total_messages'),
            func.count(func.distinct(MessageActivity.user_id)).label('unique_users')
        )

        # Apply time filter if specified
        if days:
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.where(MessageActivity.sent_at >= start_date)

        # Filter by specific channel if requested
        if channel_id:
            query = query.where(MessageActivity.channel_id == int(channel_id))

        # Group and order
        query = query.group_by(MessageActivity.channel_id).order_by(
            func.count(MessageActivity.message_id).desc()
        ).limit(limit)

        results = info.context.discord_db.exec(query).all()

        channel_stats = []
        for result in results:
            # Get most active user for this channel
            most_active_user_query = select(
                MessageActivity.user_id,
                func.count(MessageActivity.message_id).label('count')
            ).where(MessageActivity.channel_id == result.channel_id)

            if days:
                most_active_user_query = most_active_user_query.where(
                    MessageActivity.sent_at >= start_date
                )

            most_active_user = info.context.discord_db.exec(
                most_active_user_query.group_by(MessageActivity.user_id)
                .order_by(func.count(MessageActivity.message_id).desc())
                .limit(1)
            ).first()

            channel_stats.append(ChannelStatsType(
                channel_id=str(result.channel_id),
                total_messages=result.total_messages,
                unique_users=result.unique_users,
                most_active_user_id=str(most_active_user.user_id) if most_active_user else None
            ))

        return channel_stats

    @strawberry.field
    def server_stats(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: Optional[int] = None
    ) -> ServerStatsType:
        """Get overall server statistics."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        # Base time filter
        time_filter = None
        if days:
            start_date = datetime.utcnow() - timedelta(days=days)
            time_filter = start_date

        # Total users
        user_query = select(func.count(User.user_id))
        if time_filter:
            user_query = user_query.where(User.first_seen >= time_filter)
        total_users = info.context.discord_db.exec(user_query).first() or 0

        # Total messages
        message_query = select(func.count(MessageActivity.message_id))
        if time_filter:
            message_query = message_query.where(MessageActivity.sent_at >= time_filter)
        total_messages = info.context.discord_db.exec(message_query).first() or 0

        # Total voice time in hours
        voice_query = select(func.sum(
            func.extract('epoch', VoiceSession.left_at - VoiceSession.joined_at) / 3600
        )).where(VoiceSession.left_at.isnot(None))
        if time_filter:
            voice_query = voice_query.where(VoiceSession.joined_at >= time_filter)
        total_voice_hours = info.context.discord_db.exec(voice_query).first() or 0.0

        # Total activities
        activity_query = select(func.count(ActivityLog.id))
        if time_filter:
            activity_query = activity_query.where(ActivityLog.started_at >= time_filter)
        total_activities = info.context.discord_db.exec(activity_query).first() or 0

        # Most active channel
        channel_query = select(
            MessageActivity.channel_id,
            func.count(MessageActivity.message_id).label('count')
        )
        if time_filter:
            channel_query = channel_query.where(MessageActivity.sent_at >= time_filter)

        most_active_channel_data = info.context.discord_db.exec(
            channel_query.group_by(MessageActivity.channel_id)
            .order_by(func.count(MessageActivity.message_id).desc())
            .limit(1)
        ).first()

        most_active_channel_id = (
            str(most_active_channel_data.channel_id) if most_active_channel_data else None
        )

        # Most common activity
        common_activity_query = select(
            ActivityLog.activity_name,
            func.count(ActivityLog.id).label('count')
        )
        if time_filter:
            common_activity_query = common_activity_query.where(
                ActivityLog.started_at >= time_filter
            )

        most_common_activity_data = info.context.discord_db.exec(
            common_activity_query.group_by(ActivityLog.activity_name)
            .order_by(func.count(ActivityLog.id).desc())
            .limit(1)
        ).first()

        most_common_activity = (
            most_common_activity_data.activity_name if most_common_activity_data else None
        )

        return ServerStatsType(
            total_users=total_users,
            total_messages=total_messages,
            total_voice_time_hours=float(total_voice_hours),
            total_activities=total_activities,
            most_active_channel_id=most_active_channel_id,
            most_common_activity=most_common_activity
        )

    @strawberry.field
    def search_users(
        self,
        info: strawberry.Info[GraphQLContext, None],
        query: str,
        limit: int = 20
    ) -> List[UserType]:
        """Search users by username, display name, or global name."""
        if not info.context.is_authenticated:
            raise Exception("Authentication required")

        if not query or len(query.strip()) < 2:
            return []

        search_term = f"%{query.strip()}%"

        # Search in current names (effective_until is NULL)
        users = info.context.discord_db.exec(
            select(User)
            .join(UserNameHistory)
            .where(
                and_(
                    UserNameHistory.effective_until.is_(None),
                    or_(
                        UserNameHistory.username.ilike(search_term),
                        UserNameHistory.display_name.ilike(search_term),
                        UserNameHistory.global_name.ilike(search_term)
                    )
                )
            )
            .order_by(User.first_seen.desc())
            .limit(limit)
        ).all()

        return [UserType.from_model(user) for user in users]
