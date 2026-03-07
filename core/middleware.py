import json
from django.utils.deprecation import MiddlewareMixin
from .models import AuditLog

class AuditTrailMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # We only care about administrative actions (write operations)
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            # We log if the user is authenticated and the request was successful (2xx)
            if hasattr(request, 'user') and request.user.is_authenticated and 200 <= response.status_code < 300:
                try:
                    action_map = {
                        'POST': 'CREATE',
                        'PUT': 'UPDATE',
                        'PATCH': 'UPDATE',
                        'DELETE': 'DELETE'
                    }
                    action_type = action_map.get(request.method, 'OTHER')

                    # Capture path as model/view context
                    path = request.path
                    
                    # Attempt to capture changes from request body
                    changes = None
                    if request.method != 'DELETE':
                        try:
                            # Note: Reading request.body can be risky if not handled properly,
                            # but in most Django setups for APIs, it's already read.
                            if request.content_type == 'application/json' and request.body:
                                changes = json.loads(request.body)
                                # Redact sensitive fields if any
                                if isinstance(changes, dict):
                                    for sensitive in ['password', 'token', 'secret', 'confirm_password', 'otp', 'new_password', 'old_password']:
                                        if sensitive in changes:
                                            changes[sensitive] = '********'
                        except:
                            pass

                    AuditLog.objects.create(
                        action_user=request.user,
                        action_type=action_type,
                        model_name=path,
                        ip_address=self.get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        changes=changes
                    )
                except Exception as e:
                    # In production, use proper logging here
                    pass

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
