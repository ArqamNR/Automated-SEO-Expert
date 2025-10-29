from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="shopify_home"),  
    path("get-response/", views.get_user_input, name="shopify_get_response"),
    path("fetch-products/", views.fetch_products, name="fetch_products"),
    path("analyze-products/", views.analyze_products, name="analyze_products"),
    path("analyze-single-multiple-products/", views.analyze_single_and_multiple_products, name="analyze_specific_products"),
    path("resolve-product-issues/", views.resolve_product_issues, name="resolve_product_issues"),
    path("resolve-single-product-issues/", views.resolve_single_product_issues, name="resolve_single_product_issues"),
    path("approve-reject-product-suggestions/", views.approve_reject_product_suggestions, name="approve_reject_product_suggestions"),
    path("seo-dashboard-view", views.seo_dashboard_view, name='seo_dashboard_view'),
    path('gsc-queries/', views.get_query_metrics, name='gsc_query_metrics'),
    path('core-web-vitals/', views.get_core_web_vitals, name='core_web_vitals'),
    path('website-issues/', views.get_website_issues, name='website_issues'),
    path('resolve-website-issues/', views.resolve_website_issues, name='resolve_website_issues'),
    path('resolve-single-website-issue/',views.resolve_single_website_issue, name="resolve_single_website_issue"),
    path('write-blogs-and-articles/',views.write_blogs_and_articles_for_a_product, name='write_blogs_and_articles_for_a_product'),
    path('chat-interface/', views.chat_interface, name='chat_interface'),
    path('complete-website-performance/', views.complete_website_performance, name='complete_website_performance'),
]   
