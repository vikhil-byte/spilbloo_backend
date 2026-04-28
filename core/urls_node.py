from django.urls import path

from .views_node import (
    AddJournalView,
    AddChatMessageView,
    AddUserAnswersView,
    CardsView,
    DailyQnAView,
    DailyUserAnswersView,
    EditJournalView,
    FetchChatMessagesView,
    FetchJournalsView,
    FetchTherapistsView,
    FetchUserAppReviewView,
    FetchUserSelectedTherapistAndPlanView,
    NotImplementedNodeView,
    SelectTherapistAndPlanView,
    SendPushNotificationView,
)

urlpatterns = [
    path("cards", CardsView.as_view(), name="node_cards"),
    path("fetch-Journals", FetchJournalsView.as_view(), name="node_fetch_journals"),
    # iOS legacy uses lowercase endpoint.
    path("fetch-journals", FetchJournalsView.as_view(), name="node_fetch_journals_legacy"),
    path("add-journal", AddJournalView.as_view(), name="node_add_journal"),
    path("edit-journal", EditJournalView.as_view(), name="node_edit_journal"),
    path("daily-qna", DailyQnAView.as_view(), name="node_daily_qna"),
    path("daily-user-answers", DailyUserAnswersView.as_view(), name="node_daily_user_answers"),
    path("add-user-answers", AddUserAnswersView.as_view(), name="node_add_user_answers"),
    path(
        "fetch-user-selected-therapist-plan/<int:user_id>",
        FetchUserSelectedTherapistAndPlanView.as_view(),
        name="node_fetch_user_selected_therapist_and_plan",
    ),
    path("fetch-user-app-review", FetchUserAppReviewView.as_view(), name="node_fetch_user_app_review"),
    path("fetch-therapists", FetchTherapistsView.as_view(), name="node_fetch_therapists"),
    path("select-therapist-and-plan", SelectTherapistAndPlanView.as_view(), name="node_select_therapist_and_plan"),
    path("send-push-notification", SendPushNotificationView.as_view(), name="node_send_push_notification"),
    path("fetch-chat-messages/<int:user_id>", FetchChatMessagesView.as_view(), name="node_fetch_chat_messages"),
    path("add-chat-message", AddChatMessageView.as_view(), name="node_add_chat_message"),
]
