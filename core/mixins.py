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
