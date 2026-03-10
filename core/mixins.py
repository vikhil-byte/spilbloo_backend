from rest_framework.response import Response
from rest_framework import status

class StandardizedResponseMixin:
    """
    Mixin to provide standardized API responses.
    Format: { "status": "success/error", "data": ..., "message": "..." }
    """
    def success_response(self, data=None, message="Success", status_code=status.HTTP_200_OK):
        return Response({
            "status": "success",
            "message": message,
            "data": data
        }, status=status_code)

    def error_response(self, message="An error occurred", data=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({
            "status": "error",
            "message": message,
            "data": data
        }, status=status_code)

    def get_paginated_response(self, data):
        """Standardizes DRF paginated response."""
        return self.success_response(
            data={
                'count': self.paginator.page.paginator.count,
                'next': self.paginator.get_next_link(),
                'previous': self.paginator.get_previous_link(),
                'results': data
            },
            message="Data retrieved successfully"
        )
