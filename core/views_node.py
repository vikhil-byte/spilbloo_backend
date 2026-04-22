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

from .node_auth import IsNodePatientOrTherapist, NodeHeaderTokenAuthentication
from .models import NodeSubscriptionPlan, NodeUserSelectedTherapistPlan

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


class CardsView(NodeBaseAPIView):
    def get(self, request):
        try:
            results = fetch_rows("SELECT * FROM tbl_home_card WHERE is_active = 1")
            processed = [
                {
                    "title": row.get("title"),
                    "description": row.get("description"),
                    "img_url_path": row.get("img_url_path"),
                    "is_active": row.get("is_active") == 1,
                    "position": row.get("position"),
                    "card_type": row.get("card_type"),
                }
                for row in results
            ]
            return Response(node_success("OK", {"cards": processed}, 200), status=200)
        except Exception as exc:
            return Response(node_error(str(exc), 500), status=500)


class FetchJournalsView(NodeBaseAPIView):
    def get(self, request):
        user_id = request.query_params.get("userId")
        try:
            results = fetch_rows("SELECT * FROM tbl_daily_journal WHERE created_by_id = %s", [user_id])
            return Response(node_success("OK", {"journals": results}, 200), status=200)
        except Exception as exc:
            return Response(node_error(str(exc), 500), status=500)


class AddJournalView(NodeBaseAPIView):
    def post(self, request):
        journal = request.data.get("journal")
        question_id = request.data.get("question_id")
        created_by_id = request.data.get("created_by_id")
        entry_date = request.data.get("entry_date")
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO tbl_daily_journal (entry_date, journal, question_id, created_by_id) VALUES (%s, %s, %s, %s)",
                    [entry_date, journal, question_id, created_by_id],
                )
            return Response(node_success("OK", {}, 200), status=200)
        except Exception as exc:
            return Response(node_error(str(exc), 500), status=500)


class EditJournalView(NodeBaseAPIView):
    def post(self, request):
        journal = request.data.get("journal")
        created_by_id = request.data.get("created_by_id")
        entry_date = request.data.get("entry_date")
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE tbl_daily_journal SET journal = %s WHERE created_by_id = %s AND entry_date = %s",
                    [journal, created_by_id, entry_date],
                )
            return Response(node_success("OK", {}, 200), status=200)
        except Exception as exc:
            return Response(node_error(str(exc), 500), status=500)


class DailyQnAView(NodeBaseAPIView):
    def get(self, request):
        try:
            try:
                questions = fetch_rows("SELECT * FROM tbl_daily_checkin_question WHERE is_active = 1")
            except Exception:
                # Keep response contract stable even when table isn't present yet.
                return Response(node_success("OK", {"question_and_answers": []}, 200), status=200)

            answers = []
            for answer_query in (
                "SELECT * FROM tbl_daily_checkin_answer",
                "SELECT * FROM tbl_daily_checkin_Answer",
            ):
                try:
                    answers = fetch_rows(answer_query)
                    break
                except Exception:
                    continue

            question_map = {}
            for q in questions:
                q["answers"] = []
                question_map[q["id"]] = q

            for ans in answers:
                qid = ans.get("question_id")
                if qid in question_map:
                    question_map[qid]["answers"].append(ans)

            qna_response = list(question_map.values())
            return Response(node_success("OK", {"question_and_answers": qna_response}, 200), status=200)
        except Exception as exc:
            return Response(node_error("Error fetching check-in Q&A", 500), status=500)


class AddUserAnswersView(NodeBaseAPIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        qna_map = request.data.get("qna_map", [])
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO tbl_daily_checkin_question_and_answer (created_by_id, qna_map) VALUES (%s, %s::jsonb)",
                    [user_id, json.dumps(qna_map)],
                )
            return Response(node_success("OK", {}, 200), status=200)
        except Exception:
            return Response(node_error("Error adding daily check-in Q&A", 500), status=500)


class DailyUserAnswersView(NodeBaseAPIView):
    def get(self, request):
        user_id = request.query_params.get("userId")
        try:
            results = fetch_rows(
                "SELECT * FROM tbl_daily_checkin_question_and_answer WHERE created_by_id = %s",
                [user_id],
            )
            answers = [[], [], [], [], []]
            for result in results:
                qna_map = result.get("qna_map") or []
                if isinstance(qna_map, str):
                    qna_map = json.loads(qna_map)
                for idx, qna in enumerate(qna_map[:5]):
                    qna["created_on"] = result.get("entry_date")
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
            results = fetch_rows("SELECT * FROM tbl_user_app_review")
            return Response(node_success("OK", {"reviews": results}, 200), status=200)
        except Exception as exc:
            return Response(node_error(str(exc), 500), status=500)


class FetchTherapistsView(NodeBaseAPIView):
    def get(self, request):
        try:
            try:
                results = fetch_rows(
                    "SELECT * FROM tbl_user WHERE role_id = %s and is_available = %s",
                    [5, True],
                )
            except Exception:
                # Fallback for migrated schemas where is_available column doesn't exist yet.
                results = fetch_rows(
                    "SELECT * FROM tbl_user WHERE role_id = %s",
                    [5],
                )
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
                "Sleep dificulties",
                "Sexual abuse",
                "past trauma",
                "Family conflict",
                "Low self esteem",
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
                    # iOS decoders expect a numeric value here.
                    "experience": to_int(row.get("experience"), default=0),
                    "token": row.get("token") or "",
                    # Legacy iOS model reads `device_token`.
                    "device_token": row.get("token") or "",
                    # Some iOS parsing paths still look for this key.
                    "online": online_status,
                    "isOnline": online_status,
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
            therapist_rows = fetch_rows(
                "SELECT id FROM tbl_user WHERE id = %s AND role_id = 5",
                [therapist_id],
            )
            if not therapist_rows:
                return Response({"error": True, "message": "Therapist not found !"}, status=400)

            existing = fetch_rows(
                "SELECT id FROM tbl_user_selected_therapist_plan WHERE user_id = %s",
                [user_id],
            )
            with connection.cursor() as cursor:
                if existing:
                    cursor.execute(
                        """
                        UPDATE tbl_user_selected_therapist_plan
                        SET therapist_id = %s, plan_id = %s, selected_on = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                        """,
                        [therapist_id, plan_id, user_id],
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO tbl_user_selected_therapist_plan (user_id, therapist_id, plan_id, selected_on)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        """,
                        [user_id, therapist_id, plan_id],
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
            title = request.data.get("title")
            tokens = fetch_rows(
                "SELECT device_token FROM tbl_api_access_token WHERE created_by_id = %s",
                [to_id],
            )
            if not tokens:
                return Response(node_error("Error sending push notification", 400), status=400)
            device_token = tokens[0].get("device_token")
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
            rows = fetch_rows(
                "SELECT chats_message FROM tbl_chats_history WHERE user_id = %s ORDER BY created_on",
                [user_id],
            )
            chat_messages = [json.loads(row.get("chats_message") or "[]") for row in rows]
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
            rows = fetch_rows("SELECT chats_message FROM tbl_chats_history WHERE user_id = %s", [user_id])
            with connection.cursor() as cursor:
                if rows:
                    existing = json.loads(rows[0].get("chats_message") or "[]")
                    existing.extend([chat_message, bot_chat])
                    cursor.execute(
                        "UPDATE tbl_chats_history SET chats_message = %s WHERE user_id = %s",
                        [json.dumps(existing), user_id],
                    )
                else:
                    cursor.execute(
                        "INSERT INTO tbl_chats_history (user_id, chats_message) VALUES (%s, %s)",
                        [user_id, json.dumps([chat_message, bot_chat])],
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
