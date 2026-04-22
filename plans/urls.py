from django.urls import path
from .views import (
    PlanListView, CompanyUserPlanListView, MyPlansView, CreateSubscriptionView,
    AuthenticateSubscriptionView, AuthenticateOneTimeSubView, CancelCompanyView,
    CancelView, BuyVideoPlanView, CheckBuyVideoPlanView, VideoPlanListView,
    ApplyCouponView, ApplyVideoCouponView, UpdateSubscriptionView,
    FreeSubscriptionView, OneTimeSubscriptionView, CurrencyListView
)

urlpatterns = [
    path('list/', PlanListView.as_view(), name='plan_list'),
    path('company-user-plan-list/', CompanyUserPlanListView.as_view(), name='company_user_plan_list'),
    path('my-plans/', MyPlansView.as_view(), name='my_plans'),
    path('company-user-subscription/', AuthenticateSubscriptionView.as_view(), name='company_user_subscription'), # Dummy mapping
    path('create-subscription/', CreateSubscriptionView.as_view(), name='create_subscription'),
    path('authenticate-subscription/', AuthenticateSubscriptionView.as_view(), name='authenticate_subscription'),
    path('authenticate-one-time-sub/', AuthenticateOneTimeSubView.as_view(), name='authenticate_one_time_sub'),
    path('cancel-company/', CancelCompanyView.as_view(), name='cancel_company'),
    path('cancel/', CancelView.as_view(), name='cancel'),
    path('buy-video-plan/', BuyVideoPlanView.as_view(), name='buy_video_plan'),
    # iOS legacy compatibility alias.
    path('buy/', OneTimeSubscriptionView.as_view(), name='buy_legacy'),
    path('check-buy-video-plan/', CheckBuyVideoPlanView.as_view(), name='check_buy_video_plan'),
    path('video-plan/', VideoPlanListView.as_view(), name='video_plan_list'),
    # iOS legacy compatibility alias.
    path('currency/', CurrencyListView.as_view(), name='currency_list'),
    path('apply-coupon/', ApplyCouponView.as_view(), name='apply_coupon'),
    path('apply-video-coupon/', ApplyVideoCouponView.as_view(), name='apply_video_coupon'),
    path('update-subscription/', UpdateSubscriptionView.as_view(), name='update_subscription'),
    path('free-subscription/', FreeSubscriptionView.as_view(), name='free_subscription'),
    path('one-time-subscription/', OneTimeSubscriptionView.as_view(), name='one_time_subscription'),
]
