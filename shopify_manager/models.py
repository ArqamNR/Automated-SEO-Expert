from django.db import models
from django.utils import timezone

class Product(models.Model):
    store_name = models.CharField(max_length=255, blank=True, null=True)
    id = models.CharField(primary_key=True, max_length=100)
    title = models.CharField(max_length=255, blank=True, null=True)
    handle = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    description_html = models.TextField(blank=True, null=True)
    product_type = models.CharField(max_length=255, blank=True, null=True)
    vendor = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=100, blank=True, null=True)
    tags = models.JSONField(default=list, blank=True, null=True)
    created_at = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.CharField(max_length=255, blank=True, null=True)
    published_at = models.CharField(max_length=255, blank=True, null=True)
    online_store_url = models.URLField(blank=True, null=True)
    online_store_preview_url = models.URLField(blank=True, null=True)
    seo = models.JSONField(default=dict, blank=True, null=True)
    metafields = models.JSONField(default=list, blank=True, null=True)
    images = models.JSONField(default=list, blank=True, null=True)
    variants = models.JSONField(default=list, blank=True, null=True)
    options = models.JSONField(default=list, blank=True, null=True)
    internal_links = models.JSONField(default=list, blank=True, null=True)
    seo_score = models.IntegerField(blank=True, null=True)
    seo_issues = models.TextField(blank=True, null=True)
    issues_and_proposed_solutions = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.title or 'Untitled'} ({self.id})"
    
class Page_Query_Metrics(models.Model):
    page = models.TextField(blank=True, null=True)
    query = models.TextField(blank=True, null=True)
    clicks = models.IntegerField(blank=True, null=True)
    impressions = models.IntegerField(blank=True, null=True)
    ctr = models.FloatField(blank=True, null=True)
    position = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"{self.page or 'Unknown Page'} - {self.query or 'No Query'}"

class Website_Issues(models.Model):
    page = models.TextField(blank=True, null=True)
    indexstatusresult_verdict = models.TextField(blank=True, null=True)
    coverage_state = models.TextField(blank=True, null=True)
    robotsTxtState = models.TextField(blank=True, null=True)
    indexingState = models.TextField(blank=True, null=True)
    pageFetchState = models.TextField(blank=True, null=True)
    crawledAs = models.TextField(blank=True, null=True)
    mobileUsabilityResult = models.TextField(blank=True, null=True)
    referringUrls = models.JSONField(default=list, blank=True, null=True)
    lastCrawlTime = models.CharField(max_length=255, blank=True, null=True)
    googleCanonical = models.TextField(blank=True, null=True)
    userCanonical = models.TextField(blank=True, null=True)
    lcp = models.FloatField(blank=True, null=True)
    cls = models.FloatField(blank=True, null=True)
    inp = models.FloatField(blank=True, null=True)
    pagespeedscore = models.FloatField(blank=True, null=True)
    richResultsResult = models.JSONField(default=dict, blank=True, null=True)
    issues = models.TextField(blank=True, null=True)  # 🆕 new field you requested
    class Meta:
        db_table = "shopify_manager_website_issues"
        managed = False
    def __str__(self):
        return f"{self.page or 'Unknown Page'}"