import json
import logging
import random
from urllib.parse import quote

from django.db import connection
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import PermissionDenied, NotAuthenticated, AuthenticationFailed

from .node_auth import IsNodePatientOrTherapist, NodeHeaderTokenAuthentication
from .models import (
    NodeSubscriptionPlan, NodeUserSelectedTherapistPlan, HomeCard,
    DailyJournal, DailyCheckinQuestion, DailyCheckinAnswer,
    DailyCheckinQuestionAndAnswer, UserAppReview, ChatsHistory,
    ApiAccessToken
)


User = get_user_model()
logger = logging.getLogger(__name__)


def node_success(message, results, status_code):
    return {"message": message, "error": False, "code": status_code, "results": results}


def node_error(message, status_code):
    allowed_codes = {200, 201, 400, 401, 403, 404, 422, 500}
    status_code = status_code if status_code in allowed_codes else 500
    return {"message": message, "code": status_code, "error": True, "results": []}


def fetch_rows(query, params=None):
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def to_int(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def to_str(value, default=""):
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


class NodeBaseAPIView(APIView):
    authentication_classes = (NodeHeaderTokenAuthentication, JWTAuthentication)
    permission_classes = (IsAuthenticated, IsNodePatientOrTherapist)

    def handle_exception(self, exc):
        if isinstance(exc, (PermissionDenied, NotAuthenticated, AuthenticationFailed)):
            auth_header = self.request.headers.get("Authorization", "")
            user_id_header = self.request.headers.get("user-id", "")
            auth_preview = ""
            if auth_header:
                parts = auth_header.split(" ", 1)
                if len(parts) == 2:
                    auth_preview = f"{parts[0]} {parts[1][:12]}..."
                else:
                    auth_preview = f"{auth_header[:20]}..."
            logger.warning(
                "node auth/permission failed: reason=%s path=%s method=%s user_id=%s role_id=%s auth_backend=%s header_user_id=%s has_auth=%s auth_preview=%s",
                str(exc),
                self.request.path,
                self.request.method,
                getattr(self.request.user, "id", None),
                getattr(self.request.user, "role_id", None),
                self.request.successful_authenticator.__class__.__name__
                if getattr(self.request, "successful_authenticator", None)
                else "none",
                user_id_header,
                bool(auth_header),
                auth_preview,
            )
            if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
                return Response(
                    node_error("Authentication failed or token expired. Please login again.", 401),
                    status=401,
                )
            if isinstance(exc, PermissionDenied):
                return Response(
                    node_error("You do not have permission to access this resource.", 403),
                    status=403,
                )
        return super().handle_exception(exc)


class CardsView(NodeBaseAPIView):
    def get(self, request):
        try:
            results = HomeCard.objects.filter(is_active=1)
            processed = [
                {
                    "title": card.title,
                    "description": card.description,
                    "img_url_path": card.img_url_path,
                    "is_active": card.is_active == 1,
                    "position": card.position,
                    "card_type": card.card_type,
                }
                for card in results
            ]
            if request.user and hasattr(request.user, "get_affirmation_for_the_day"):
                affirmation = request.user.get_affirmation_for_the_day()
            else:
                affirmation = User().get_affirmation_for_the_day()
            return Response(node_success("OK", {"cards": processed, "affirmation": affirmation}, 200), status=200)
        except Exception as exc:
            return Response(node_error(str(exc), 500), status=500)


class FetchJournalsView(NodeBaseAPIView):
    def get(self, request):
        user_id = request.query_params.get("userId")
        try:
            results = list(DailyJournal.objects.filter(created_by_id=user_id).values())
            processed = []
            for r in results:
                # Format entry_date (date object -> YYYY-MM-DDT00:00:00.000Z)
                entry_date_str = ""
                if r.get("entry_date"):
                    entry_date_str = f"{r['entry_date'].strftime('%Y-%m-%d')}T00:00:00.000Z"

                # Format created_on (datetime object -> YYYY-MM-DDTHH:MM:SS.000Z)
                created_on_str = ""
                if r.get("created_on"):
                    created_on_str = r["created_on"].strftime("%Y-%m-%dT%H:%M:%S.000Z")

                processed.append({
                    "id": r.get("id"),
                    "journal": r.get("journal"),
                    "question_id": r.get("question_id"),
                    "entry_date": entry_date_str,
                    "created_by_id": r.get("created_by_id") or r.get("created_by"),
                    "created_on": created_on_str
                })
            return Response(node_success("OK", {"journals": processed}, 200), status=200)
        except Exception as exc:
            return Response(node_error(str(exc), 500), status=500)


class AddJournalView(NodeBaseAPIView):
    def post(self, request):
        journal = request.data.get("journal")
        question_id = request.data.get("question_id")
        created_by_id = request.data.get("created_by_id")
        entry_date = request.data.get("entry_date")
        
        logger.info(
            "AddJournalView.post: journal=%s, question_id=%s, created_by_id=%s, entry_date=%s",
            journal, question_id, created_by_id, entry_date
        )
        
        try:
            kwargs = {
                "journal": journal,
                "question_id": question_id,
                "created_by_id": created_by_id,
            }
            if entry_date:
                if isinstance(entry_date, str) and "T" in entry_date:
                    entry_date = entry_date.split("T")[0]
                kwargs["entry_date"] = entry_date

            DailyJournal.objects.create(**kwargs)
            logger.info("AddJournalView.post success: journal created successfully")
            return Response(node_success("OK", {}, 200), status=200)
        except Exception as exc:
            logger.exception("AddJournalView.post error creating journal entry: %s", str(exc))
            return Response(node_error(str(exc), 500), status=500)


class EditJournalView(NodeBaseAPIView):
    def post(self, request):
        journal = request.data.get("journal")
        created_by_id = request.data.get("created_by_id")
        entry_date = request.data.get("entry_date")
        try:
            DailyJournal.objects.filter(created_by_id=created_by_id, entry_date=entry_date).update(journal=journal)
            return Response(node_success("OK", {}, 200), status=200)
        except Exception as exc:
            return Response(node_error(str(exc), 500), status=500)


class DailyQnAView(NodeBaseAPIView):
    def get(self, request):
        try:
            questions = list(DailyCheckinQuestion.objects.filter(is_active=1).values())
            answers = list(DailyCheckinAnswer.objects.all().values())

            question_map = {}
            for q in questions:
                if q.get("created_on"):
                    q["created_on"] = q["created_on"].strftime("%Y-%m-%d %H:%M:%S")
                else:
                    q["created_on"] = ""
                q["answers"] = []
                question_map[q["id"]] = q

            for ans in answers:
                if ans.get("created_on"):
                    ans["created_on"] = ans["created_on"].strftime("%Y-%m-%d %H:%M:%S")
                else:
                    ans["created_on"] = ""
                qid = ans.get("question_id")
                if qid in question_map:
                    question_map[qid]["answers"].append(ans)

            qna_response = list(question_map.values())
            return Response(node_success("OK", {"question_and_answers": qna_response}, 200), status=200)
        except Exception as exc:
            return Response(node_error("Error fetching check-in Q&A: " + str(exc), 500), status=500)


class AddUserAnswersView(NodeBaseAPIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        qna_map = request.data.get("qna_map", [])
        try:
            DailyCheckinQuestionAndAnswer.objects.create(
                created_by_id=user_id,
                qna_map=qna_map,
            )
            return Response(node_success("OK", {}, 200), status=200)
        except Exception:
            return Response(node_error("Error adding daily check-in Q&A", 500), status=500)


class DailyUserAnswersView(NodeBaseAPIView):
    def get(self, request):
        user_id = request.query_params.get("userId")
        try:
            results = list(DailyCheckinQuestionAndAnswer.objects.filter(created_by_id=user_id).values())
            answers = [[], [], [], [], []]
            title_map = {
                1: "Interest",
                2: "Anxiety",
                3: "Sleep",
                4: "Energy",
                5: "Mood"
            }
            for result in results:
                qna_map = result.get("qna_map") or []
                if isinstance(qna_map, str):
                    qna_map = json.loads(qna_map)
                for idx, qna in enumerate(qna_map[:5]):
                    entry_date = result.get("entry_date")
                    qna["created_on"] = f"{entry_date.strftime('%Y-%m-%d')}T00:00:00.000Z" if entry_date else None
                    if not qna.get("title"):
                        qna["title"] = title_map.get(qna.get("id"), "")
                    answers[idx].append(qna)
            return Response(node_success("OK", {"user_answers": answers}, 200), status=200)
        except Exception:
            return Response(node_error("Error fetching daily check-in user answers", 500), status=500)



class FetchUserSelectedTherapistAndPlanView(NodeBaseAPIView):
    def get(self, request, user_id):
        try:
            rows = list(NodeUserSelectedTherapistPlan.objects.filter(user_id=user_id).values())
            if not rows:
                return Response(node_error("User's therapist and plan not found", 404), status=404)

            therapist_id = rows[0].get("therapist_id")
            plan_id = rows[0].get("plan_id")
            therapist_rows = list(User.objects.filter(id=therapist_id).values())
            plan_rows = list(NodeSubscriptionPlan.objects.filter(id=plan_id).values())
            if not therapist_rows or not plan_rows:
                return Response(node_error("User's therapist and plan not found", 404), status=404)

            therapist = therapist_rows[0]
            online_status = to_str(therapist.get("online"), default="")
            therapist_detail = {
                "id": therapist.get("id"),
                "full_name": therapist.get("full_name") or "",
                "qualification": therapist.get("qualification") or "",
                "contact_no": therapist.get("contact_no") or "",
                "about_me": therapist.get("about_me") or "",
                "profile_file": f"/user/image/{therapist.get('id')}?file={quote(str(therapist.get('profile_file') or ''))}",
                "experience": to_int(therapist.get("experience"), default=0),
                "token": therapist.get("token") or "",
                "device_token": therapist.get("token") or "",
                "online": online_status,
                "isOnline": online_status,
                "language": therapist.get("language") or "",
                "symptoms": [
                    "Anger management",
                    "Specific phobia",
                    "Social anxiety",
                    "Sleep difficulties",
                    "Sexual abuse",
                    "Past trauma",
                    "Family conflict",
                    "Low self-esteem",
                ],
            }
            plan_detail = plan_rows[0]
            return Response(
                node_success(
                    "OK",
                    {"therapist_detail": therapist_detail, "plan_detail": plan_detail},
                    200,
                ),
                status=200,
            )
        except Exception as exc:
            return Response(node_error(str(exc), 500), status=500)


class FetchUserAppReviewView(NodeBaseAPIView):
    def get(self, request):
        try:
            results = list(UserAppReview.objects.all().values())
            return Response(node_success("OK", {"reviews": results}, 200), status=200)
        except Exception as exc:
            return Response(node_error(str(exc), 500), status=500)


class FetchTherapistsView(NodeBaseAPIView):
    def get(self, request):
        try:
            try:
                results = list(User.objects.filter(role_id=5, is_available=True).values())
            except Exception:
                # Fallback for migrated schemas where is_available column doesn't exist yet.
                results = list(User.objects.filter(role_id=5).values())
            logger.info(
                "node.fetch_therapists raw_rows=%s user_id=%s auth=%s",
                len(results),
                getattr(request.user, "id", None),
                request.successful_authenticator.__class__.__name__
                if getattr(request, "successful_authenticator", None)
                else "none",
            )
            symptoms = [
                "Anger management",
                "Specific phobia",
                "Social anxiety",
                "Sleep difficulties",
                "Sexual abuse",
                "Past trauma",
                "Family conflict",
                "Low self-esteem",
            ]
            processed = [
                (
                    lambda online_status: {
                        "id": row.get("id"),
                        "full_name": row.get("full_name") or "",
                        "qualification": row.get("qualification") or "",
                        "contact_no": row.get("contact_no") or "",
                        "about_me": row.get("about_me") or "",
                        "profile_file": f"/user/image/{row.get('id')}?file={quote(str(row.get('profile_file') or ''))}",
                        "experience": to_int(row.get("experience"), default=0),
                        "token": row.get("token") or "",
                        "device_token": row.get("token") or "",
                        "online": online_status,
                        "isOnline": online_status,
                        "language": row.get("language") or "",
                        "symptoms": symptoms,
                    }
                )(to_str(row.get("online"), default=""))
                for row in results
            ]
            null_field_counts = {
                key: sum(1 for row in results if row.get(key) is None)
                for key in ("full_name", "qualification", "contact_no", "about_me", "profile_file", "experience", "token")
            }
            if processed:
                logger.info(
                    "node.fetch_therapists payload_count=%s nulls=%s sample=%s",
                    len(processed),
                    json.dumps(null_field_counts),
                    json.dumps(processed[0]),
                )
            else:
                logger.info(
                    "node.fetch_therapists payload_count=0 nulls=%s",
                    json.dumps(null_field_counts),
                )
            random.shuffle(processed)
            return Response(node_success("OK", {"therapists": processed}, 200), status=200)
        except Exception as exc:
            logger.exception("node.fetch_therapists error: %s", str(exc))
            return Response(node_error(str(exc), 500), status=500)


class SelectTherapistAndPlanView(NodeBaseAPIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        therapist_id = request.data.get("therapist_id")
        plan_id = request.data.get("plan_id")
        try:
            if not User.objects.filter(id=therapist_id, role_id=5).exists():
                return Response({"error": True, "message": "Therapist not found !"}, status=400)

            from django.utils import timezone
            NodeUserSelectedTherapistPlan.objects.update_or_create(
                user_id=user_id,
                defaults={
                    "therapist_id": therapist_id,
                    "plan_id": plan_id,
                    "selected_on": timezone.now(),
                }
            )
            return Response(
                node_success("Therapist and plan selected successfully", {}, 200),
                status=200,
            )
        except Exception as exc:
            return Response({"error": True, "message": str(exc)}, status=400)


class SendPushNotificationView(NodeBaseAPIView):
    def post(self, request):
        try:
            to_id = request.data.get("to_id")
            tokens = ApiAccessToken.objects.filter(created_by_id=to_id)
            if not tokens.exists():
                return Response(node_error("Error sending push notification", 400), status=400)
            device_token = tokens.first().device_token
            # StarterNode returns success envelope with device token in results.
            return Response(
                node_success("Push notification sent successfully", device_token, 200),
                status=200,
            )
        except Exception:
            return Response(node_error("Error sending push notification", 400), status=400)


class FetchChatMessagesView(NodeBaseAPIView):
    def get(self, request, user_id):
        try:
            rows = ChatsHistory.objects.filter(user_id=user_id).order_by("created_on")
            chat_messages = []
            for row in rows:
                msg = row.chats_message
                if isinstance(msg, str):
                    try:
                        msg = json.loads(msg or "[]")
                    except Exception:
                        msg = []
                elif msg is None:
                    msg = []
                chat_messages.append(msg)
            first = chat_messages[0] if chat_messages else []
            return Response(
                node_success("Chat messages retrieved successfully", {"messages": first}, 200),
                status=200,
            )
        except Exception:
            return Response(node_error("Error fetching chat messages", 500), status=500)


class AddChatMessageView(NodeBaseAPIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        chat_message = request.data.get("chats_message") or {}
        user_message = str(chat_message.get("message", "")).lower()
        if user_message == "hi":
            bot_response = "Hey"
        elif user_message == "hello":
            bot_response = "Hi there!"
        else:
            bot_response = "I didn't understand that. Can you please clarify?"

        bot_chat = {"message": bot_response, "is_sent": False}
        try:
            row = ChatsHistory.objects.filter(user_id=user_id).first()
            if row:
                existing = row.chats_message
                if isinstance(existing, str):
                    try:
                        existing = json.loads(existing or "[]")
                    except Exception:
                        existing = []
                elif existing is None:
                    existing = []
                existing.extend([chat_message, bot_chat])
                row.chats_message = json.dumps(existing)
                row.save()
            else:
                ChatsHistory.objects.create(
                    user_id=user_id,
                    chats_message=json.dumps([chat_message, bot_chat])
                )
            return Response(
                node_success(
                    "Messages added successfully",
                    {"user": chat_message, "bot": bot_chat},
                    200,
                ),
                status=200,
            )
        except Exception:
            return Response(node_error("Error adding chat messages", 500), status=500)


class NotImplementedNodeView(NodeBaseAPIView):
    def get(self, request, *args, **kwargs):
        return Response(node_error("Endpoint migration in progress", 404), status=404)

    def post(self, request):
        return Response(node_error("Endpoint migration in progress", 404), status=404)

