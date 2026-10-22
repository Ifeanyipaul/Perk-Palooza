
from django.urls import path

from .views import (
    BusinessCategoryListView,
    BusinessListCreateView,
    BusinessDetailView,
    BusinessApprovalView,
    BusinessOwnerAssignmentView,
    MyBusinessesView,

)

urlpatterns = [
    path(
        "categories/",
        BusinessCategoryListView.as_view(),
        name="business-categories"
    ),

    path(
        "",
        BusinessListCreateView.as_view(),
        name="business-list-create"
    ),

    path(
        "<int:pk>/",
        BusinessDetailView.as_view(),
        name="business-detail"
    ),

    path(
        "<int:pk>/approval/",
        BusinessApprovalView.as_view(),
        name="business-approval"
    ),
    path(
        "<int:pk>/assign-owner/",
        BusinessOwnerAssignmentView.as_view(),
        name="business-owner-assignment"
    ),
    path(
        "<int:pk>/assign-owner/",
        BusinessOwnerAssignmentView.as_view(),
        name="business-owner-assignment"
    ),
    path(
        "my/",
        MyBusinessesView.as_view(),
        name="my-businesses"
    ),
]
