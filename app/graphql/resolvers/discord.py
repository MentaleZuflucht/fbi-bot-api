"""
GraphQL resolvers for Discord data.

These resolvers handle queries for Discord user data, messages, voice sessions,
and other Discord-related information with proper authentication.
"""

import logging
from typing import Annotated, Optional, List
from collections import defaultdict
import strawberry
from sqlmodel import select, func, and_, or_
from sqlalchemy.orm import aliased
from app.graphql.arguments import Limit, Offset, UserId, ChannelId, Days, StartDate, EndDate
from app.graphql.context import GraphQLContext
from app.graphql.permissions import IsAuthenticated
from app.graphql.types.discord import (
    UserType, MessageActivityType, VoiceSessionType, ActivityLogType,
    PresenceStatusLogType, CustomStatusType, ChannelStatsType, ServerStatsType,
    DailyStatsType, HourlyDistributionType, TopItemType, TopUserType,
    TopVoiceStateUserType, VoiceConnectionType, ChannelType,
    ActivityTypeEnum, MessageTypeEnum, DiscordStatusEnum, VoiceStateTypeEnum,
    parse_date_filter,
)
from app.discord.models import (
    User, Channel, MessageActivity, VoiceSession, VoiceStateLog, ActivityLog,
    PresenceStatusLog, CustomStatus, UserNameHistory
)

logger = logging.getLogger(__name__)


@strawberry.type
class Query:
    """GraphQL queries for Discord data."""

    @strawberry.field(
        description="One Discord user by ID, or null if the bot has never seen them.",
        permission_classes=[IsAuthenticated],
    )
    def user(
        self,
        info: strawberry.Info[GraphQLContext, None],
        user_id: Annotated[str, strawberry.argument(description="Discord user ID.")]
    ) -> Optional[UserType]:
        try:
            logger.debug(f"GraphQL query: user(user_id={user_id}) by {info.context.api_key.name}")

            user = info.context.discord_db.exec(
                select(User).where(User.user_id == int(user_id))
            ).first()

            if user:
                logger.debug(f"Found user {user_id}")
            else:
                logger.debug(f"User {user_id} not found")

            return UserType.from_model(user) if user else None
        except Exception as e:
            logger.error(f"Error in GraphQL user query: {e}", exc_info=True)
            raise

    @strawberry.field(
        description="All users the bot has seen, sorted by name.",
        permission_classes=[IsAuthenticated],
    )
    def users(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: Limit = 50,
        offset: Offset = 0,
        search: Annotated[Optional[str], strawberry.argument(
            description="Part of a username, display name or global name (case-insensitive)."
        )] = None
    ) -> List[UserType]:
        query = select(User)

        if search:
            query = query.join(UserNameHistory).where(
                and_(
                    UserNameHistory.effective_until.is_(None),
                    or_(
                        UserNameHistory.username.ilike(f"%{search}%"),
                        UserNameHistory.display_name.ilike(f"%{search}%"),
                        UserNameHistory.global_name.ilike(f"%{search}%")
                    )
                )
            )
        else:
            query = query.outerjoin(
                UserNameHistory,
                and_(
                    UserNameHistory.user_id == User.user_id,
                    UserNameHistory.effective_until.is_(None),
                ),
            )

        name_sort = func.coalesce(
            UserNameHistory.global_name,
            UserNameHistory.display_name,
            UserNameHistory.username,
            "",
        )
        users = info.context.discord_db.exec(
            query.order_by(name_sort.asc())
            .offset(offset)
            .limit(limit)
        ).all()

        return [UserType.from_model(user) for user in users]

    @strawberry.field(
        description=(
            "Sent messages, newest first. The bot never stores message content, "
            "only details like type, length and whether it had attachments."
        ),
        permission_classes=[IsAuthenticated],
    )
    def messages(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: Limit = 50,
        offset: Offset = 0,
        user_id: UserId = None,
        channel_id: ChannelId = None,
        message_type: Annotated[Optional[MessageTypeEnum], strawberry.argument(
            description="Only messages of this type."
        )] = None,
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[MessageActivityType]:
        query = select(MessageActivity)

        if user_id:
            query = query.where(MessageActivity.user_id == int(user_id))
        if channel_id:
            query = query.where(MessageActivity.channel_id == int(channel_id))
        if message_type:
            query = query.where(MessageActivity.message_type == message_type.value)

        start, end = parse_date_filter(days, start_date, end_date)
        if start:
            query = query.where(MessageActivity.sent_at >= start)
        if end:
            query = query.where(MessageActivity.sent_at <= end)

        messages = info.context.discord_db.exec(
            query.order_by(MessageActivity.sent_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return [MessageActivityType.from_model(msg) for msg in messages]

    @strawberry.field(
        description=(
            "Voice channel visits (from joining to leaving a channel), newest first. "
            "Dates filter on when the user joined."
        ),
        permission_classes=[IsAuthenticated],
    )
    def voice_sessions(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: Limit = 50,
        offset: Offset = 0,
        user_id: UserId = None,
        channel_id: ChannelId = None,
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
        ongoing_only: Annotated[bool, strawberry.argument(
            description="Only sessions of users who are in voice right now."
        )] = False
    ) -> List[VoiceSessionType]:
        query = select(VoiceSession)

        if user_id:
            query = query.where(VoiceSession.user_id == int(user_id))
        if channel_id:
            query = query.where(VoiceSession.channel_id == int(channel_id))
        if ongoing_only:
            query = query.where(VoiceSession.left_at.is_(None))

        start, end = parse_date_filter(days, start_date, end_date)
        if start:
            query = query.where(VoiceSession.joined_at >= start)
        if end:
            query = query.where(VoiceSession.joined_at <= end)

        sessions = info.context.discord_db.exec(
            query.order_by(VoiceSession.joined_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return [VoiceSessionType.from_model(session) for session in sessions]

    @strawberry.field(
        description=(
            "Discord activities (playing a game, listening to Spotify, streaming, ...), "
            "newest first. "
            "Dates filter on when the activity started."
        ),
        permission_classes=[IsAuthenticated],
    )
    def activities(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: Limit = 50,
        offset: Offset = 0,
        user_id: UserId = None,
        activity_type: Annotated[Optional[ActivityTypeEnum], strawberry.argument(
            description="Only activities of this type."
        )] = None,
        activity_name: Annotated[Optional[str], strawberry.argument(
            description='Part of the activity name (case-insensitive), e.g. "minecraft".'
        )] = None,
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
        ongoing_only: Annotated[bool, strawberry.argument(
            description="Only activities that are still going on."
        )] = False
    ) -> List[ActivityLogType]:
        query = select(ActivityLog)

        if user_id:
            query = query.where(ActivityLog.user_id == int(user_id))
        if activity_type:
            query = query.where(ActivityLog.activity_type == activity_type.value)
        if activity_name:
            query = query.where(ActivityLog.activity_name.ilike(f"%{activity_name}%"))
        if ongoing_only:
            query = query.where(ActivityLog.ended_at.is_(None))

        start, end = parse_date_filter(days, start_date, end_date)
        if start:
            query = query.where(ActivityLog.started_at >= start)
        if end:
            query = query.where(ActivityLog.started_at <= end)

        activities = info.context.discord_db.exec(
            query.order_by(ActivityLog.started_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return [ActivityLogType.from_model(activity) for activity in activities]

    @strawberry.field(
        description=(
            "Online status history (online, idle, do not disturb, offline), newest first. "
            "Each entry lasts from setAt until changedAt."
        ),
        permission_classes=[IsAuthenticated],
    )
    def presence_status(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: Limit = 50,
        offset: Offset = 0,
        user_id: UserId = None,
        status_type: Annotated[Optional[DiscordStatusEnum], strawberry.argument(
            description="Only this status."
        )] = None,
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
        current_only: Annotated[bool, strawberry.argument(
            description="Only the status each user has right now."
        )] = False
    ) -> List[PresenceStatusLogType]:
        query = select(PresenceStatusLog)

        if user_id:
            query = query.where(PresenceStatusLog.user_id == int(user_id))
        if status_type:
            query = query.where(PresenceStatusLog.status_type == status_type.value)
        if current_only:
            query = query.where(PresenceStatusLog.changed_at.is_(None))

        start, end = parse_date_filter(days, start_date, end_date)
        if start:
            query = query.where(PresenceStatusLog.set_at >= start)
        if end:
            query = query.where(PresenceStatusLog.set_at <= end)

        statuses = info.context.discord_db.exec(
            query.order_by(PresenceStatusLog.set_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return [PresenceStatusLogType.from_model(status) for status in statuses]

    @strawberry.field(
        description="Custom statuses (the text and emoji shown under a name), newest first.",
        permission_classes=[IsAuthenticated],
    )
    def custom_statuses(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: Limit = 50,
        offset: Offset = 0,
        user_id: UserId = None,
        has_text: Annotated[Optional[bool], strawberry.argument(
            description="true: only statuses with text. false: only statuses without text."
        )] = None,
        has_emoji: Annotated[Optional[bool], strawberry.argument(
            description="true: only statuses with an emoji. false: only statuses without one."
        )] = None,
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[CustomStatusType]:
        query = select(CustomStatus)

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

        start, end = parse_date_filter(days, start_date, end_date)
        if start:
            query = query.where(CustomStatus.set_at >= start)
        if end:
            query = query.where(CustomStatus.set_at <= end)

        statuses = info.context.discord_db.exec(
            query.order_by(CustomStatus.set_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()

        return [CustomStatusType.from_model(status) for status in statuses]

    @strawberry.field(
        description="Text channels ranked by number of messages.",
        permission_classes=[IsAuthenticated],
    )
    def channel_stats(
        self,
        info: strawberry.Info[GraphQLContext, None],
        channel_id: ChannelId = None,
        limit: Limit = 10,
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[ChannelStatsType]:
        start, end = parse_date_filter(days, start_date, end_date)

        query = select(
            MessageActivity.channel_id,
            func.count(MessageActivity.message_id).label('total_messages'),
            func.count(func.distinct(MessageActivity.user_id)).label('unique_users')
        )

        if start:
            query = query.where(MessageActivity.sent_at >= start)
        if end:
            query = query.where(MessageActivity.sent_at <= end)
        if channel_id:
            query = query.where(MessageActivity.channel_id == int(channel_id))

        query = query.group_by(MessageActivity.channel_id).order_by(
            func.count(MessageActivity.message_id).desc()
        ).limit(limit)

        results = info.context.discord_db.exec(query).all()

        channel_stats = []
        for result in results:
            most_active_user_query = select(
                MessageActivity.user_id,
                func.count(MessageActivity.message_id).label('count')
            ).where(MessageActivity.channel_id == result.channel_id)

            if start:
                most_active_user_query = most_active_user_query.where(MessageActivity.sent_at >= start)
            if end:
                most_active_user_query = most_active_user_query.where(MessageActivity.sent_at <= end)

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

    @strawberry.field(
        description="Totals for the whole server.",
        permission_classes=[IsAuthenticated],
    )
    def server_stats(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> ServerStatsType:
        start, end = parse_date_filter(days, start_date, end_date)

        user_query = select(func.count(User.user_id))
        if start:
            user_query = user_query.where(User.first_seen >= start)
        if end:
            user_query = user_query.where(User.first_seen <= end)
        total_users = info.context.discord_db.exec(user_query).first() or 0

        message_query = select(func.count(MessageActivity.message_id))
        if start:
            message_query = message_query.where(MessageActivity.sent_at >= start)
        if end:
            message_query = message_query.where(MessageActivity.sent_at <= end)
        total_messages = info.context.discord_db.exec(message_query).first() or 0

        voice_query = select(func.sum(
            func.extract('epoch', VoiceSession.left_at - VoiceSession.joined_at) / 3600
        )).where(VoiceSession.left_at.isnot(None))
        if start:
            voice_query = voice_query.where(VoiceSession.joined_at >= start)
        if end:
            voice_query = voice_query.where(VoiceSession.joined_at <= end)
        total_voice_hours = info.context.discord_db.exec(voice_query).first() or 0.0

        activity_query = select(func.count(ActivityLog.id))
        if start:
            activity_query = activity_query.where(ActivityLog.started_at >= start)
        if end:
            activity_query = activity_query.where(ActivityLog.started_at <= end)
        total_activities = info.context.discord_db.exec(activity_query).first() or 0

        channel_query = select(
            MessageActivity.channel_id,
            func.count(MessageActivity.message_id).label('count')
        )
        if start:
            channel_query = channel_query.where(MessageActivity.sent_at >= start)
        if end:
            channel_query = channel_query.where(MessageActivity.sent_at <= end)

        most_active_channel_data = info.context.discord_db.exec(
            channel_query.group_by(MessageActivity.channel_id)
            .order_by(func.count(MessageActivity.message_id).desc())
            .limit(1)
        ).first()

        most_active_channel_id = (
            str(most_active_channel_data.channel_id) if most_active_channel_data else None
        )

        common_activity_query = select(
            ActivityLog.activity_name,
            func.count(ActivityLog.id).label('count')
        )
        if start:
            common_activity_query = common_activity_query.where(ActivityLog.started_at >= start)
        if end:
            common_activity_query = common_activity_query.where(ActivityLog.started_at <= end)

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

    @strawberry.field(
        description=(
            "Activity per day, oldest first, for charts. Days without any activity are left out. "
            "Note: days defaults to 30 here, pass days: null to get everything."
        ),
        permission_classes=[IsAuthenticated],
    )
    def daily_stats(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: Days = 30,
        user_id: UserId = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[DailyStatsType]:
        db = info.context.discord_db
        start, end = parse_date_filter(days, start_date, end_date)
        date_trunc = func.date(MessageActivity.sent_at)

        msg_q = select(
            date_trunc.label("d"),
            func.count(MessageActivity.message_id).label("cnt"),
            func.count(func.distinct(MessageActivity.user_id)).label("users"),
        )
        if start:
            msg_q = msg_q.where(MessageActivity.sent_at >= start)
        if end:
            msg_q = msg_q.where(MessageActivity.sent_at <= end)
        if user_id:
            msg_q = msg_q.where(MessageActivity.user_id == int(user_id))
        msg_rows = {
            str(r.d): (r.cnt, r.users)
            for r in db.exec(msg_q.group_by("d"))
        }

        voice_date = func.date(VoiceSession.joined_at)
        voice_q = select(
            voice_date.label("d"),
            func.sum(
                func.extract("epoch", VoiceSession.left_at - VoiceSession.joined_at) / 3600
            ).label("hours"),
        ).where(VoiceSession.left_at.isnot(None))
        if start:
            voice_q = voice_q.where(VoiceSession.joined_at >= start)
        if end:
            voice_q = voice_q.where(VoiceSession.joined_at <= end)
        if user_id:
            voice_q = voice_q.where(VoiceSession.user_id == int(user_id))
        voice_rows = {
            str(r.d): float(r.hours or 0)
            for r in db.exec(voice_q.group_by("d"))
        }

        act_date = func.date(ActivityLog.started_at)
        act_q = select(act_date.label("d"), func.count(ActivityLog.id).label("cnt"))
        if start:
            act_q = act_q.where(ActivityLog.started_at >= start)
        if end:
            act_q = act_q.where(ActivityLog.started_at <= end)
        if user_id:
            act_q = act_q.where(ActivityLog.user_id == int(user_id))
        act_rows = {str(r.d): r.cnt for r in db.exec(act_q.group_by("d"))}

        all_dates = sorted(set(list(msg_rows) + list(voice_rows) + list(act_rows)))
        return [
            DailyStatsType(
                date=d,
                message_count=msg_rows.get(d, (0, 0))[0],
                voice_hours=round(voice_rows.get(d, 0.0), 2),
                activity_count=act_rows.get(d, 0),
                active_users=msg_rows.get(d, (0, 0))[1],
            )
            for d in all_dates
        ]

    @strawberry.field(
        description=(
            "Number of messages per hour of the day. "
            "Always 24 entries, hour 0 to 23 (UTC)."
        ),
        permission_classes=[IsAuthenticated],
    )
    def hourly_message_distribution(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: Days = None,
        user_id: UserId = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[HourlyDistributionType]:
        start, end = parse_date_filter(days, start_date, end_date)
        hour_col = func.extract("hour", MessageActivity.sent_at).label("h")
        q = select(hour_col, func.count(MessageActivity.message_id).label("cnt"))
        if start:
            q = q.where(MessageActivity.sent_at >= start)
        if end:
            q = q.where(MessageActivity.sent_at <= end)
        if user_id:
            q = q.where(MessageActivity.user_id == int(user_id))

        rows = {int(r.h): r.cnt for r in info.context.discord_db.exec(q.group_by("h"))}
        return [HourlyDistributionType(hour=h, count=rows.get(h, 0)) for h in range(24)]

    @strawberry.field(
        description=(
            "Voice channels ranked by total hours spent in them. "
            "name is the channel name (or its ID if unknown), count the number of visits. "
            "Only finished visits count."
        ),
        permission_classes=[IsAuthenticated],
    )
    def top_channels(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: Days = None,
        limit: Limit = 10,
        user_id: UserId = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[TopItemType]:
        start, end = parse_date_filter(days, start_date, end_date)

        hours_sum = func.sum(
            func.extract("epoch", VoiceSession.left_at - VoiceSession.joined_at) / 3600
        )

        q = select(
            VoiceSession.channel_id,
            func.count(VoiceSession.id).label("cnt"),
            hours_sum.label("hours"),
        ).where(VoiceSession.left_at.isnot(None))

        if start:
            q = q.where(VoiceSession.joined_at >= start)
        if end:
            q = q.where(VoiceSession.joined_at <= end)
        if user_id:
            q = q.where(VoiceSession.user_id == int(user_id))

        rows = info.context.discord_db.exec(
            q.group_by(VoiceSession.channel_id)
            .order_by(hours_sum.desc())
            .limit(limit)
        ).all()
        return [
            TopItemType(
                name=info.context.channel_name(r.channel_id) or str(r.channel_id),
                count=r.cnt,
                hours=round(float(r.hours or 0), 2),
            )
            for r in rows
        ]

    @strawberry.field(
        description=(
            "Activities ranked by total hours. "
            "name is the activity name, count how often it was started. "
            "Only finished activities count."
        ),
        permission_classes=[IsAuthenticated],
    )
    def top_activities(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: Days = None,
        limit: Limit = 10,
        user_id: UserId = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[TopItemType]:
        start, end = parse_date_filter(days, start_date, end_date)

        hours_sum = func.sum(
            func.extract("epoch", ActivityLog.ended_at - ActivityLog.started_at) / 3600
        )

        q = select(
            ActivityLog.activity_name,
            func.count(ActivityLog.id).label("cnt"),
            hours_sum.label("hours"),
        ).where(ActivityLog.ended_at.isnot(None))

        if start:
            q = q.where(ActivityLog.started_at >= start)
        if end:
            q = q.where(ActivityLog.started_at <= end)
        if user_id:
            q = q.where(ActivityLog.user_id == int(user_id))

        rows = info.context.discord_db.exec(
            q.group_by(ActivityLog.activity_name)
            .order_by(hours_sum.desc())
            .limit(limit)
        ).all()
        return [
            TopItemType(
                name=r.activity_name,
                count=r.cnt,
                hours=round(float(r.hours or 0), 2),
            )
            for r in rows
        ]

    @strawberry.field(
        description=(
            "Most active users, ranked by score = voice minutes + messages "
            "(one minute in voice counts as much as one message)."
        ),
        permission_classes=[IsAuthenticated],
    )
    def top_users(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: Days = None,
        limit: Limit = 10,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[TopUserType]:
        db = info.context.discord_db
        start, end = parse_date_filter(days, start_date, end_date)

        msg_q = select(
            MessageActivity.user_id,
            func.count(MessageActivity.message_id).label("cnt"),
        )
        if start:
            msg_q = msg_q.where(MessageActivity.sent_at >= start)
        if end:
            msg_q = msg_q.where(MessageActivity.sent_at <= end)
        msg_map = {r.user_id: r.cnt for r in db.exec(msg_q.group_by(MessageActivity.user_id))}

        voice_q = select(
            VoiceSession.user_id,
            func.sum(func.extract("epoch", VoiceSession.left_at - VoiceSession.joined_at) / 3600).label("hours"),
        ).where(VoiceSession.left_at.isnot(None))
        if start:
            voice_q = voice_q.where(VoiceSession.joined_at >= start)
        if end:
            voice_q = voice_q.where(VoiceSession.joined_at <= end)
        voice_map = {
            r.user_id: float(r.hours or 0)
            for r in db.exec(voice_q.group_by(VoiceSession.user_id))
        }

        all_user_ids = set(msg_map.keys()) | set(voice_map.keys())
        scored = []
        for uid in all_user_ids:
            msgs = msg_map.get(uid, 0)
            hours = voice_map.get(uid, 0.0)
            score = hours * 60 + msgs
            scored.append((uid, msgs, hours, score))

        scored.sort(key=lambda x: x[3], reverse=True)
        scored = scored[:limit]

        user_ids = [s[0] for s in scored]
        if not user_ids:
            return []

        names = db.exec(
            select(UserNameHistory)
            .where(UserNameHistory.user_id.in_(user_ids), UserNameHistory.effective_until.is_(None))
        ).all()
        name_map = {n.user_id: n.global_name or n.display_name or n.username for n in names}

        return [
            TopUserType(
                user_id=str(uid),
                name=name_map.get(uid, str(uid)),
                message_count=msgs,
                voice_hours=round(hours, 2),
                score=round(score, 1),
            )
            for uid, msgs, hours, score in scored
        ]

    @strawberry.field(
        description=(
            "For each voice state (muted, deafened, streaming, camera on, ...), "
            "the users who spent the most time in it. limit applies to each state separately."
        ),
        permission_classes=[IsAuthenticated],
    )
    def top_voice_state_users(
        self,
        info: strawberry.Info[GraphQLContext, None],
        days: Days = None,
        limit: Limit = 5,
        start_date: StartDate = None,
        end_date: EndDate = None,
        state_type: Annotated[Optional[VoiceStateTypeEnum], strawberry.argument(
            description="Only this voice state."
        )] = None,
    ) -> List[TopVoiceStateUserType]:
        db = info.context.discord_db
        start, end = parse_date_filter(days, start_date, end_date)

        hours_sum = func.sum(
            func.extract("epoch", VoiceStateLog.ended_at - VoiceStateLog.started_at) / 3600
        )

        q = select(
            VoiceStateLog.state_type,
            VoiceSession.user_id,
            hours_sum.label("hours"),
        ).join(
            VoiceSession, VoiceStateLog.session_id == VoiceSession.id
        ).where(
            VoiceStateLog.ended_at.isnot(None)
        )

        if start:
            q = q.where(VoiceStateLog.started_at >= start)
        if end:
            q = q.where(VoiceStateLog.started_at <= end)
        if state_type:
            q = q.where(VoiceStateLog.state_type == state_type.value)

        q = q.group_by(VoiceStateLog.state_type, VoiceSession.user_id).order_by(
            VoiceStateLog.state_type, hours_sum.desc()
        )

        rows = db.exec(q).all()

        grouped: dict[str, list] = defaultdict(list)
        all_user_ids: set[int] = set()
        for r in rows:
            st_val = r.state_type.value if hasattr(r.state_type, 'value') else str(r.state_type)
            if len(grouped[st_val]) < limit:
                grouped[st_val].append(r)
                all_user_ids.add(r.user_id)

        name_map: dict[int, str] = {}
        if all_user_ids:
            names = db.exec(
                select(UserNameHistory)
                .where(UserNameHistory.user_id.in_(list(all_user_ids)), UserNameHistory.effective_until.is_(None))
            ).all()
            name_map = {n.user_id: n.global_name or n.display_name or n.username for n in names}

        results: List[TopVoiceStateUserType] = []
        for st_val, entries in grouped.items():
            for r in entries:
                results.append(TopVoiceStateUserType(
                    state_type=VoiceStateTypeEnum(st_val),
                    user_id=str(r.user_id),
                    name=name_map.get(r.user_id, str(r.user_id)),
                    hours=round(float(r.hours or 0), 2),
                ))

        return results

    @strawberry.field(
        description=(
            '"Voice dating": pairs of users ranked by how long they were in the same voice channel '
            "at the same time. Only finished sessions count."
        ),
        permission_classes=[IsAuthenticated],
    )
    def voice_connections(
        self,
        info: strawberry.Info[GraphQLContext, None],
        limit: Limit = 20,
        user_id: Annotated[Optional[str], strawberry.argument(
            description="Only pairs that include this Discord user ID."
        )] = None,
        days: Days = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
    ) -> List[VoiceConnectionType]:
        db = info.context.discord_db
        start, end = parse_date_filter(days, start_date, end_date)

        a = aliased(VoiceSession)
        b = aliased(VoiceSession)

        overlap_seconds = func.extract(
            "epoch",
            func.least(a.left_at, b.left_at) - func.greatest(a.joined_at, b.joined_at),
        )
        total_hours = func.sum(overlap_seconds) / 3600

        q = (
            select(
                a.user_id.label("user_a_id"),
                b.user_id.label("user_b_id"),
                total_hours.label("hours"),
                func.count().label("cnt"),
            )
            .where(
                and_(
                    a.channel_id == b.channel_id,
                    a.user_id < b.user_id,
                    a.left_at.isnot(None),
                    b.left_at.isnot(None),
                    a.joined_at < b.left_at,
                    b.joined_at < a.left_at,
                )
            )
        )

        if user_id:
            uid = int(user_id)
            q = q.where(or_(a.user_id == uid, b.user_id == uid))

        if start:
            q = q.where(and_(a.joined_at >= start, b.joined_at >= start))
        if end:
            q = q.where(and_(a.joined_at <= end, b.joined_at <= end))

        q = q.group_by(a.user_id, b.user_id).order_by(total_hours.desc()).limit(limit)

        rows = db.exec(q).all()

        all_user_ids: set[int] = set()
        for r in rows:
            all_user_ids.add(r.user_a_id)
            all_user_ids.add(r.user_b_id)

        name_map: dict[int, str] = {}
        if all_user_ids:
            names = db.exec(
                select(UserNameHistory).where(
                    UserNameHistory.user_id.in_(list(all_user_ids)),
                    UserNameHistory.effective_until.is_(None),
                )
            ).all()
            name_map = {
                n.user_id: n.global_name or n.display_name or n.username
                for n in names
            }

        return [
            VoiceConnectionType(
                user1_id=str(r.user_a_id),
                user1_name=name_map.get(r.user_a_id, str(r.user_a_id)),
                user2_id=str(r.user_b_id),
                user2_name=name_map.get(r.user_b_id, str(r.user_b_id)),
                shared_hours=round(float(r.hours or 0), 2),
                session_count=r.cnt,
            )
            for r in rows
        ]

    @strawberry.field(
        description="All channels and threads the bot has seen, sorted by name.",
        permission_classes=[IsAuthenticated],
    )
    def channels(
        self,
        info: strawberry.Info[GraphQLContext, None],
        include_deleted: Annotated[bool, strawberry.argument(
            description="Also include deleted channels."
        )] = False,
    ) -> List[ChannelType]:
        query = select(Channel).order_by(Channel.name)
        if not include_deleted:
            query = query.where(Channel.deleted_at.is_(None))
        return [ChannelType.from_model(channel) for channel in info.context.discord_db.exec(query).all()]

    @strawberry.field(
        description=(
            "Search users by username, display name or global name (case-insensitive), "
            "newest members first. Like users(search: ...), but sorted by first seen."
        ),
        permission_classes=[IsAuthenticated],
        deprecation_reason="Use users(search: ...) instead.",
    )
    def search_users(
        self,
        info: strawberry.Info[GraphQLContext, None],
        query: Annotated[str, strawberry.argument(
            description="Part of the name, at least 2 characters."
        )],
        limit: Limit = 20
    ) -> List[UserType]:
        if not query or len(query.strip()) < 2:
            return []

        search_term = f"%{query.strip()}%"

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
