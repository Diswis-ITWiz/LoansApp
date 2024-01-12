from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('new-client', views.newClient, name='new-client'),
    path('loan-item/', views.loanItemClientFinder, name='loan-item'),
    path('loan-item2/<str:pk>', views.loanItemTransaction, name='loan-item-transaction'),
    path('return-item', views.returnItem1, name='return-item1'),
    path('retuern-transaction/<str:pk>', views.returnItem2, name='return-item2'),

    path('admin-dashboard/', views.adminDashboard, name='admin-dashboard'),

    path('item-panel/', views.itemPanel, name='item-panel'),
    path('item-detail/<str:pk>', views.itemDetailView, name='item-details'),
    path('add-item', views.addItem, name='add-item'),
    path('edit-item/<str:pk>', views.editItem, name='edit-item'),
    path('delete-item/<str:pk>', views.deleteItem, name='delete-item'),

    path('client-panel/', views.clientPanel, name='client-panel'),
    path('client-detail/<str:pk>', views.clientDetails, name='client-details'),
    path('edit-client/<str:pk>', views.editClient, name='edit-client'),
    path('lift-client-penalty/<str:pk>', views.liftClientPenalty, name='lift-client-penalty'),

    path('block-date', views.blockOutDate, name='block-date'),
    path('block-time', views.blockOutTime, name='block-time'),
    path('finals-week', views.finalsWeek, name='finals-week'),
]