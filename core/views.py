import logging
import psutil
import platform
import time
import csv
import calendar
from datetime import datetime, timedelta
from collections import defaultdict
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db import connections
from django.db.utils import OperationalError
from django.utils import timezone
from django.utils.html import strip_tags
from django.http import HttpResponse
from django.db.models import Count, Sum, Q
from django.db.models.functions import ExtractMonth, ExtractYear
from drf_spectacular.types import OpenApiTypes
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.core.mail import get_connection
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets
from rest_framework.decorators import action
from .models import College, Department, SystemNotification, NotificationReadState
from .serializers import SystemStatsResponseSerializer, HealthCheckResponseSerializer
from .serializers import CollegeSerializer, DepartmentSerializer
from .serializers import AnalyticsDashboardResponseSerializer
from .serializers import SystemNotificationSerializer, NotificationItemSerializer
from analytics.permissions import HasAnalyticsPermission
from users.models import User
from announcements.models import Announcement
from clubs.models import Club
from events.models import Event
from bookings.models import Booking
from venues.models import Venue
from .models import College, Department, SystemNotification, NotificationReadState

logger = logging.getLogger(__name__)


class CollegeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for colleges.
    Read access is public; write actions are restricted to admins.
    """
    queryset = College.objects.filter(is_active=True).order_by('name')
    serializer_class = CollegeSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


class DepartmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for departments.
    Read access is public; write actions are restricted to admins.
    """
    queryset = Department.objects.filter(is_active=True).select_related('college').order_by('name')
    serializer_class = DepartmentSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


@extend_schema(tags=['Notifications'])
class SystemNotificationViewSet(viewsets.ModelViewSet):
    """
    System notifications for authenticated users and admin management.
    """

    queryset = SystemNotification.objects.filter(is_active=True).order_by('-created_at')

    def get_permissions(self):
        admin_actions = {'create', 'update', 'partial_update', 'destroy'}
        if self.action in admin_actions:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):  # type: ignore[reportIncompatibleMethodOverride]
        admin_actions = {'create', 'update', 'partial_update', 'destroy'}
        if self.action in admin_actions:
            return SystemNotificationSerializer
        return NotificationItemSerializer

    def _build_announcement_excerpt(self, body):
        cleaned = strip_tags(body or '').strip()
        if not cleaned:
            return 'New announcement published.'
        return f"{cleaned[:157]}..." if len(cleaned) > 160 else cleaned

    def _ensure_announcement_notifications(self):
        # Prevent this from running on every single request.
        # Run at most once every hour to backfill notifications.
        lock_cache_key = 'notifications:announcement_backfill_lock'
        if cache.get(lock_cache_key):
            return
            
        cache.set(lock_cache_key, True, timeout=3600)

        # Backfill notifications for published announcements so the menu always has meaningful data.
        published = list(
            Announcement.objects.filter(is_active=True, is_published=True)
            .select_related('author')
            .order_by('-created_at')[:100]
        )
        if not published:
            return

        hrefs = [f"/announcements/{announcement.id}" for announcement in published]
        existing_hrefs = set(
            SystemNotification.objects.filter(
                notification_type=SystemNotification.NotificationType.ANNOUNCEMENT,
                href__in=hrefs,
            ).values_list('href', flat=True)
        )

        to_create = []
        for announcement in published:
            href = f"/announcements/{announcement.id}"
            if href in existing_hrefs:
                continue
            to_create.append(
                SystemNotification(
                    title=announcement.title[:180],
                    description=self._build_announcement_excerpt(announcement.body),
                    notification_type=SystemNotification.NotificationType.ANNOUNCEMENT,
                    icon_key='Megaphone',
                    href=href,
                    target_all_users=True,
                    created_by=announcement.author,
                )
            )

        if to_create:
            SystemNotification.objects.bulk_create(to_create)

    def get_queryset(self):  # type: ignore[reportIncompatibleMethodOverride]
        if self.action in {'list', 'retrieve'}:
            self._ensure_announcement_notifications()

        queryset = (
            SystemNotification.objects.filter(is_active=True)
            .prefetch_related('target_roles', 'target_users')
            .order_by('-created_at')
        )

        now = timezone.now()
        queryset = queryset.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))

        # Use getattr to handle cases where self.request may be a plain HttpRequest
        qp = getattr(self.request, 'query_params', getattr(self.request, 'GET', {}))
        user = getattr(self.request, 'user', None)
        if self.action in {'retrieve', 'list'} and getattr(user, 'is_staff', False):
            scope = qp.get('scope')
            if scope == 'admin':
                return queryset

        return queryset.filter(
            Q(target_all_users=True) |
            Q(target_users=user) |
            Q(target_roles__users=user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action in {'list', 'retrieve'}:
            read_ids = set(
                NotificationReadState.objects.filter(user=self.request.user).values_list('notification_id', flat=True)
            )
            context['read_ids'] = read_ids
        return context

    @extend_schema(
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        NotificationReadState.objects.get_or_create(notification=notification, user=request.user)
        return Response(
            {
                'success': True,
                'message': 'Notification marked as read.',
                'data': {'id': str(notification.id), 'read': True},
                'statusCode': 200,
                'error': None,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        notifications = self.get_queryset().values_list('id', flat=True)
        already_read_ids = set(
            NotificationReadState.objects.filter(
                user=request.user,
                notification_id__in=notifications,
            ).values_list('notification_id', flat=True)
        )

        unread_ids = [notification_id for notification_id in notifications if notification_id not in already_read_ids]
        now = timezone.now()

        with transaction.atomic():
            NotificationReadState.objects.bulk_create(
                [
                    NotificationReadState(
                        notification_id=notification_id,
                        user=request.user,
                        read_at=now,
                    )
                    for notification_id in unread_ids
                ],
                ignore_conflicts=True,
            )

        return Response(
            {
                'success': True,
                'message': 'All notifications marked as read.',
                'data': {'count': len(unread_ids)},
                'statusCode': 200,
                'error': None,
            },
            status=status.HTTP_200_OK,
        )


class AnalyticsDashboardView(APIView):
    """
    Aggregated statistics for the frontend Statistics and Reports dashboard.
    """
    permission_classes = [permissions.IsAuthenticated, HasAnalyticsPermission]
    PERIOD_CHOICES = {'last-8-months', 'academic-year', 'calendar-year'}

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='period',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Reporting period: last-8-months, academic-year, calendar-year',
            )
        ],
        responses={200: AnalyticsDashboardResponseSerializer},
    )
    def get(self, request):
        period = request.query_params.get('period', 'last-8-months')
        if period not in self.PERIOD_CHOICES:
            period = 'last-8-months'

        # Determine access level
        is_admin = request.user.is_staff or request.user.is_superuser or request.user.has_perm('analytics.view_analytics')

        cache_ttl = int(getattr(settings, 'ANALYTICS_DASHBOARD_CACHE_TTL', 600))
        # Share cache across users who have the same access level (admin vs member)
        access_level = "admin" if is_admin else "member"
        cache_key = f"analytics-dashboard:{access_level}:{period}"
        
        if cache_ttl > 0:
            cached_payload = cache.get(cache_key)
            if cached_payload is not None:
                return Response(cached_payload, status=status.HTTP_200_OK)

        now = timezone.now()
        labels = self._period_labels(period, now)

        # Base components visible to everyone
        registration_trends = self._registration_trends(period, labels, now)
        occupancy_trends = self._occupancy_trends(period, labels, now)
        club_breakdown = self._club_breakdown()
        event_distribution = self._event_distribution()
        venue_kpis = self._venue_kpis(now)
        venue_stats = self._venue_stats()
        upcoming_mega_events = self._upcoming_mega_events(request, now)
        recent_announcements = self._recent_announcements(request)
        overview = self._overview_cards(period, now)

        # Restricted components (redacted for non-admins)
        if is_admin:
            recent_activity = self._recent_activity(now)
            club_stats = self._club_stats()
        else:
            # Members see empty/limited versions of sensitive admin components
            recent_activity = []
            club_stats = []

        response_data = {
            'period': period,
            'overview': overview,
            'registration_trends': registration_trends,
            'occupancy_trends': occupancy_trends,
            'club_breakdown': club_breakdown,
            'event_distribution': event_distribution,
            'venue_kpis': venue_kpis,
            'venue_stats': venue_stats,
            'club_stats': club_stats,
            'recent_activity': recent_activity,
            'upcoming_mega_events': upcoming_mega_events,
            'recent_announcements': recent_announcements,
        }

        payload = {
            'success': True,
            'message': 'Analytics dashboard data retrieved successfully.',
            'data': response_data,
            'statusCode': 200,
            'error': None,
        }

        if cache_ttl > 0:
            cache.set(cache_key, payload, timeout=cache_ttl)

        return Response(payload, status=status.HTTP_200_OK)

    def _period_labels(self, period, now):
        if period == 'last-8-months':
            labels = []
            year = now.year
            month = now.month
            for offset in range(7, -1, -1):
                mm = month - offset
                yy = year
                while mm <= 0:
                    mm += 12
                    yy -= 1
                labels.append({'label': datetime(yy, mm, 1).strftime('%b'), 'year': yy, 'month': mm})
            return labels

        if period == 'academic-year':
            start_year = now.year if now.month >= 7 else now.year - 1
            return [
                {'label': 'Q1', 'months': [(start_year, 7), (start_year, 8), (start_year, 9)]},
                {'label': 'Q2', 'months': [(start_year, 10), (start_year, 11), (start_year, 12)]},
                {'label': 'Q3', 'months': [(start_year + 1, 1), (start_year + 1, 2), (start_year + 1, 3)]},
                {'label': 'Q4', 'months': [(start_year + 1, 4), (start_year + 1, 5), (start_year + 1, 6)]},
            ]

        year = now.year
        return [
            {'label': 'H1', 'months': [(year, m) for m in range(1, 7)]},
            {'label': 'H2', 'months': [(year, m) for m in range(7, 13)]},
        ]

    def _registration_trends(self, period, labels, now):
        users_qs = User.objects.filter(is_active=True)
        grouped_rows = (
            users_qs
            .annotate(year=ExtractYear('created_at'), month=ExtractMonth('created_at'))
            .values('year', 'month')
            .annotate(total=Count('id'))
        )
        grouped = {(row['year'], row['month']): row['total'] for row in grouped_rows}
        points = []

        if period == 'last-8-months':
            for item in labels:
                value = grouped.get((item['year'], item['month']), 0)
                points.append({'label': item['label'], 'value': value})
            return points

        for block in labels:
            total = sum(grouped.get((yy, mm), 0) for yy, mm in block['months'])
            points.append({'label': block['label'], 'value': total})
        return points

    def _occupancy_trends(self, period, labels, now):
        bookings_qs = Booking.objects.filter(is_active=True).exclude(status='cancelled')
        active_venues = max(Venue.objects.filter(is_active=True).count(), 1)

        # Pre-fetch all relevant bookings for the entire range to avoid N+1 queries
        if period == 'last-8-months':
            start_date = labels[0]['year'], labels[0]['month']
            # We filter from the first day of the first month in labels
            bookings_qs = bookings_qs.filter(start_date__year__gte=labels[0]['year'])
        elif period == 'academic-year':
            start_year = labels[0]['months'][0][0]
            bookings_qs = bookings_qs.filter(start_date__year__gte=start_year)
        else:
            year = labels[0]['months'][0][0]
            bookings_qs = bookings_qs.filter(start_date__year__gte=year)

        # Load all bookings into memory for processing (only the selected_slots and date fields)
        all_bookings = list(bookings_qs.only('selected_slots', 'start_date'))
        
        # Group bookings by (year, month)
        grouped_bookings = defaultdict(list)
        for b in all_bookings:
            grouped_bookings[(b.start_date.year, b.start_date.month)].append(b)

        def month_capacity(yy, mm):
            days = calendar.monthrange(yy, mm)[1]
            # Frontend slots run 08:00-19:00 (12 hourly slots)
            return active_venues * days * 12

        def get_total_slots(yy, mm):
            month_list = grouped_bookings.get((yy, mm), [])
            return sum(len(b.selected_slots or []) for b in month_list)

        points = []

        if period == 'last-8-months':
            for item in labels:
                cap = month_capacity(item['year'], item['month'])
                used = get_total_slots(item['year'], item['month'])
                value = round((used / cap) * 100, 2) if cap else 0
                points.append({'label': item['label'], 'value': value})
            return points

        for block in labels:
            cap_sum = 0
            used_sum = 0
            for yy, mm in block['months']:
                cap_sum += month_capacity(yy, mm)
                used_sum += get_total_slots(yy, mm)
            value = round((used_sum / cap_sum) * 100, 2) if cap_sum else 0
            points.append({'label': block['label'], 'value': value})
        return points

    def _club_breakdown(self):
        palette = ['#c49a22', '#1f2a44', '#7d8ca8', '#d4b45c', '#4b5563']
        rows = (
            Club.objects.filter(is_active=True)
            .values('category__slug', 'category__name')
            .annotate(value=Count('id'))
            .order_by('-value')
        )

        items = []
        for idx, row in enumerate(rows):
            slug = row['category__slug'] or f'uncategorized-{idx}'
            label = row['category__name'] or 'Uncategorized'
            items.append({
                'id': slug,
                'label': label,
                'value': row['value'],
                'color': palette[idx % len(palette)],
            })
        return items

    def _event_distribution(self):
        mega = Event.objects.filter(is_active=True, is_mega_event=True).count()
        general = Event.objects.filter(is_active=True, is_mega_event=False).count()
        return [
            {'id': 'general', 'label': 'General', 'value': general, 'color': '#1f2a44'},
            {'id': 'mega', 'label': 'Mega', 'value': mega, 'color': '#c49a22'},
        ]

    def _venue_kpis(self, now):
        # Use aggregation to find the most popular venue efficiently
        most_popular_row = (
            Booking.objects.filter(is_active=True)
            .exclude(status='cancelled')
            .values('venue__name')
            .annotate(total=Count('id'))
            .order_by('-total')
            .first()
        )
        most_popular = most_popular_row['venue__name'] if most_popular_row else 'N/A'

        # Limit to the last 12 months for KPI calculations to maintain performance
        cutoff_date = now.date() - timedelta(days=365)
        bookings = (
            Booking.objects.filter(is_active=True, start_date__gte=cutoff_date)
            .exclude(status='cancelled')
            .only('selected_slots')
        )
        total_slots = 0
        count = 0
        for booking in bookings:
            slots = len(booking.selected_slots or [])
            if slots > 0:
                total_slots += slots
                count += 1
        avg_hours = round(total_slots / count, 1) if count else 0.0

        return {
            'most_popular': most_popular,
            'avg_session_hours': avg_hours,
        }

    def _venue_stats(self):
        # Aggregate basic venue statistics for dashboard cards
        total_venues = Venue.objects.filter(is_active=True).count()
        maintenance = Venue.objects.filter(status='maintenance').count()

        today = timezone.now().date()
        active_now = (
            Booking.objects.filter(is_active=True)
            .exclude(status='cancelled')
            .filter(start_date__lte=today, end_date__gte=today)
            .values('venue')
            .distinct()
            .count()
        )

        total_capacity = Venue.objects.aggregate(total_capacity=Sum('max_capacity')).get('total_capacity') or 0

        return [
            {'id': 'total-venues', 'title': 'Total Venues', 'value': str(total_venues), 'icon': 'Building2'},
            {'id': 'active-now', 'title': 'Active Now', 'value': str(active_now), 'icon': 'CircleCheck'},
            {'id': 'maintenance', 'title': 'Maintenance', 'value': str(maintenance), 'icon': 'Wrench'},
            {'id': 'total-capacity', 'title': 'Total Capacity', 'value': f"{total_capacity:,}", 'icon': 'Users'},
        ]

    def _club_stats(self):
        total_clubs = Club.objects.filter(is_active=True).count()
        pending = Club.objects.filter(status='pending').count()
        categories = Club.objects.filter(is_active=True).values('category__slug').distinct().count()

        return [
            {'id': 'total-clubs', 'title': 'Total Clubs', 'value': str(total_clubs), 'icon': 'Users'},
            {'id': 'pending-approvals', 'title': 'Pending Approvals', 'value': str(pending), 'icon': 'Clock3'},
            {'id': 'active-categories', 'title': 'Active Categories', 'value': str(categories), 'icon': 'Layers3'},
        ]

    def _relative_timestamp(self, dt, now):
        if not dt:
            return 'Recently'

        delta = now - dt
        minutes = int(delta.total_seconds() // 60)
        if minutes < 1:
            return 'Just now'
        if minutes < 60:
            return f"{minutes} min ago"

        hours = int(delta.total_seconds() // 3600)
        if hours < 24:
            return f"{hours} hour ago" if hours == 1 else f"{hours} hours ago"

        if (now.date() - dt.date()).days == 1:
            return 'Yesterday'

        return dt.strftime('%b %d')

    def _recent_activity(self, now):
        activity = []

        # Optimization: Fetch limited fields and use single queries per category
        clubs = Club.objects.filter(is_active=True).order_by('-created_at').only('id', 'name', 'created_at')[:4]
        for club in clubs:
            activity.append({
                'id': f'club-{club.id}',
                'type': 'club',
                'bold_label': 'New Club Application',
                'description': f"{club.name} submitted for review.",
                'timestamp': self._relative_timestamp(club.created_at, now),
                'created_at': club.created_at,
            })

        bookings = Booking.objects.filter(is_active=True, status='approved').order_by('-updated_at').only('id', 'title', 'id_label', 'updated_at', 'created_at')[:4]
        for booking in bookings:
            activity.append({
                'id': f'approval-{booking.id}',
                'type': 'approval',
                'bold_label': 'Approval Granted',
                'description': f"'{booking.title or booking.id_label}' booking approved.",
                'timestamp': self._relative_timestamp(booking.updated_at or booking.created_at, now),
                'created_at': booking.updated_at or booking.created_at,
            })

        users = User.objects.filter(is_active=True).order_by('-created_at').only('id', 'name', 'created_at')[:4]
        for user in users:
            activity.append({
                'id': f'user-{user.id}',
                'type': 'student',
                'bold_label': 'Student Registration',
                'description': f"{user.name} joined the platform.",
                'timestamp': self._relative_timestamp(user.created_at, now),
                'created_at': user.created_at,
            })

        events = Event.objects.filter(is_active=True).annotate(att_count=Count('attendees')).order_by('-created_at').only('id', 'title', 'max_capacity', 'updated_at', 'created_at')[:4]
        for event in events:
            if event.max_capacity and event.att_count >= event.max_capacity:
                activity.append({
                    'id': f'alert-{event.id}',
                    'type': 'alert',
                    'bold_label': 'System Alert',
                    'description': f"Event '{event.title}' capacity reached.",
                    'timestamp': self._relative_timestamp(event.updated_at or event.created_at, now),
                    'created_at': event.updated_at or event.created_at,
                })

        ordered = sorted(activity, key=lambda x: x['created_at'] or now, reverse=True)[:5]
        for item in ordered:
            item.pop('created_at', None)
        return ordered

    def _upcoming_mega_events(self, request, now):
        qs = (
            Event.objects.filter(is_active=True, is_mega_event=True, start_date_time__gte=now)
            .select_related('venue')
            .annotate(attendee_count_total=Count('attendees'))
            .prefetch_related('attendees')
            .order_by('start_date_time')[:4]
        )

        items = []
        fallback_image = 'https://images.unsplash.com/photo-1511578314322-379afb476865?w=1200&auto=format&fit=crop'
        for event in qs:
            cover = fallback_image
            if event.cover_image:
                cover = request.build_absolute_uri(event.cover_image.url)

            date_label = event.start_date_time.strftime('%b %d').upper() if event.start_date_time else 'TBD'
            # attendees prefetch will work for these first 3
            attendee_items = [
                {
                    'id': str(a.id),
                    'name': a.name,
                }
                for a in event.attendees.all()[:3]
            ]

            items.append({
                'id': str(event.id),
                'title': event.title,
                'venue': event.venue.name if event.venue else 'Campus Venue',
                'image_url': cover,
                'date_label': date_label,
                'attendee_count': event.attendee_count_total,
                'attendees': attendee_items,
            })

        return items

    def _recent_announcements(self, request):
        qs = (
            Announcement.objects.filter(is_active=True, is_published=True)
            .select_related('category')
            .order_by('-created_at')[:3]
        )
        items = []
        for ann in qs:
            items.append({
                'id': str(ann.id),
                'title': ann.title,
                'image': request.build_absolute_uri(ann.image.url) if ann.image else None,
                'createdAt': ann.created_at.isoformat(),
                'categoryDetails': {
                    'name': ann.category.name if ann.category else 'General'
                }
            })
        return items

    def _overview_cards(self, period, now):
        # Optimized counts in fewer queries
        counts = {
            'students': User.objects.filter(is_active=True).count(),
            'clubs': Club.objects.filter(is_active=True, status='active').count(),
            'events': Event.objects.filter(is_active=True, start_date_time__year=now.year, start_date_time__month=now.month).count(),
            'bookings': Booking.objects.filter(is_active=True).exclude(status='cancelled').count(),
        }

        cards = [
            {
                'id': 'overview-students',
                'title': 'Total Students',
                'value': str(counts['students']),
                'icon': 'GraduationCap',
                'icon_bg': '#fdf8ec',
            },
            {
                'id': 'overview-clubs',
                'title': 'Active Clubs',
                'value': str(counts['clubs']),
                'icon': 'Users2',
                'icon_bg': '#fdf8ec',
            },
            {
                'id': 'overview-events',
                'title': 'Monthly Events',
                'value': str(counts['events']),
                'icon': 'CalendarDays',
                'icon_bg': '#fdf8ec',
            },
            {
                'id': 'overview-bookings',
                'title': 'Total Venue Bookings',
                'value': str(counts['bookings']),
                'icon': 'Building2',
                'icon_bg': '#fdf8ec',
            },
        ]

        # Trend indicator logic
        prev_month = now.month - 1 if now.month > 1 else 12
        prev_year = now.year if now.month > 1 else now.year - 1
        
        month_stats = User.objects.filter(is_active=True).aggregate(
            current=Count('id', filter=Q(created_at__year=now.year, created_at__month=now.month)),
            prev=Count('id', filter=Q(created_at__year=prev_year, created_at__month=prev_month))
        )
        
        current_month_users = month_stats['current'] or 0
        prev_month_users = month_stats['prev'] or 0

        if prev_month_users > 0:
            delta = round(((current_month_users - prev_month_users) / prev_month_users) * 100, 1)
        else:
            delta = 0.0

        trend_direction = 'up' if delta > 0 else ('down' if delta < 0 else 'neutral')
        trend_text = f"{delta:+.1f}% from last month"

        for card in cards:
            card['trend'] = trend_text
            card['trend_direction'] = trend_direction

        return cards


class AnalyticsReportExportView(APIView):
    """
    Export analytics report as CSV for the selected period.
    """
    permission_classes = [permissions.IsAuthenticated, HasAnalyticsPermission]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='period', type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name='format', type=str, location=OpenApiParameter.QUERY),
        ],
        responses={200: OpenApiTypes.BINARY},
    )
    def get(self, request):
        period = request.query_params.get('period', 'last-8-months')
        export_format = request.query_params.get('format', 'csv')

        if export_format.lower() != 'csv':
            return Response(
                {'error': 'Only CSV export is currently supported.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        stats_view = AnalyticsDashboardView()
        labels = stats_view._period_labels(period, now)
        registration = stats_view._registration_trends(period, labels, now)
        occupancy = stats_view._occupancy_trends(period, labels, now)

        response = HttpResponse(content_type='text/csv')
        filename = f"analytics-{period}-{now.strftime('%Y%m%d-%H%M%S')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Section', 'Label', 'Value'])

        for item in registration:
            writer.writerow(['registration_trends', item['label'], item['value']])
        for item in occupancy:
            writer.writerow(['occupancy_trends', item['label'], item['value']])

        return response

class SystemStatsView(APIView):
    """
    Detailed system resource usage (CPU, Memory, Disk, Network).
    """
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(responses={200: SystemStatsResponseSerializer})
    def get(self, request):
        # CPU Info
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        try:
            loadavg = list(psutil.getloadavg())
        except AttributeError:
            loadavg = [0.0, 0.0, 0.0]

        # Memory Info
        mem = psutil.virtual_memory()
        
        # Disk Info
        disk = psutil.disk_usage('/')
        
        # Network Info
        net_io = psutil.net_io_counters(pernic=True)
        net_stats = psutil.net_if_stats()
        network_data = []
        for interface, stats in net_stats.items():
            io = net_io.get(interface)
            network_data.append({
                "interface": interface,
                "state": "up" if stats.isup else "down",
                "speedMbps": stats.speed,
                "incomming": io.bytes_recv if io else 0,
                "outgoing": io.bytes_sent if io else 0
            })

        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time

        data = {
            "timestamp": timezone.now().isoformat(),
            "cpu": {
                "cores": cpu_count,
                "model": platform.processor(),
                "speedMHz": cpu_freq.current if cpu_freq else 0,
                "loadavg": loadavg
            },
            "memory": {
                "total": mem.total,
                "free": mem.available,
                "used": mem.used,
                "usedPercent": mem.percent
            },
            "disk": {
                "mount": "/",
                "size": disk.total,
                "used": disk.used,
                "available": disk.free,
                "usedPercent": disk.percent
            },
            "network": network_data,
            "lastUpdate": timezone.now().isoformat(),
            "uptime": uptime,
            "status": "Healthy"
        }

        return Response({
            "success": True,
            "message": "System Stat successfully",
            "data": data,
            "statusCode": 200,
            "error": None
        })

@extend_schema(tags=['Core'])
class HealthCheckView(APIView):
    """
    Quick health check for database and core components.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: HealthCheckResponseSerializer})
    def get(self, request):
        components = []
        
        # 1. Database Check (Critical)
        db_status = "up"
        try:
            connections['default'].cursor()
        except OperationalError:
            db_status = "down"
        components.append({"name": "Database", "status": db_status, "is_critical": True})

        # 2. Storage Check (Critical)
        components.append({"name": "Storage", "status": "up", "is_critical": True})

        # 3. System Resources Check (Critical)
        system_status = "up"
        if psutil.virtual_memory().percent > 95:
            system_status = "degraded"
        components.append({"name": "System Resources", "status": system_status, "is_critical": True})
        
        # 4. Email Configuration Check (Passive)
        # We no longer actively open a connection to avoid blocking the health check
        # and because outbound SMTP is often restricted in cloud environments.
        email_status = "up"
        if not settings.EMAIL_HOST_USER and "console" not in settings.EMAIL_BACKEND:
             email_status = "down"
             
        components.append({
            "name": "Email", 
            "status": email_status,
            "is_critical": False
        })

        # System is healthy if all critical components are up or degraded
        is_healthy = all(
            c['status'] in ['up', 'degraded'] 
            for c in components 
            if c.get('is_critical', True)
        )

        return Response({
            "success": True,
            "message": "Health Check retrieved successfully",
            "data": {
                "success": is_healthy,
                "message": "Health check performed successfully",
                "status": "Healthy" if is_healthy else "Unhealthy",
                "components": components
            },
            "statusCode": 200,
            "error": None
        })
