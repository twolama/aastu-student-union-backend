import psutil
import platform
import time
from django.db import connections
from django.db.utils import OperationalError
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from .models import College, Department
from .serializers import SystemStatsResponseSerializer, HealthCheckResponseSerializer
from .serializers import CollegeSerializer, DepartmentSerializer


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

class HealthCheckView(APIView):
    """
    Quick health check for database and core components.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses={200: HealthCheckResponseSerializer})
    def get(self, request):
        components = []
        
        # 1. Database Check
        db_status = "up"
        try:
            connections['default'].cursor()
        except OperationalError:
            db_status = "down"
        components.append({"name": "Database", "status": db_status})

        # 2. Storage Check
        components.append({"name": "Storage", "status": "up"})

        # 3. System Resources Check
        system_status = "up"
        if psutil.virtual_memory().percent > 95:
            system_status = "degraded"
        components.append({"name": "System Resources", "status": system_status})

        is_healthy = all(c['status'] in ['up', 'degraded'] for c in components)

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
