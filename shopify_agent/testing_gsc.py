from googleapiclient.discovery import build
from google.oauth2 import service_account
import json
SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
KEY_FILE = "shopify_agent/credentials.json"
SITE_URL = "sc-domain:theplantsmall.com"
# SITE_URL = "https://sa-electronics-and-home-appliances.myshopify.com/"

def get_search_console_data(page_url):
    creds = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
    webmasters_service = build('searchconsole', 'v1', credentials=creds)

    request_body = {
            "startDate": '2025-06-21',
            "endDate": '2025-09-21',
            "dimensions": ["page"],  # We want data broken down by URL and query
            "dimensionFilterGroups": [{
                "filters": [{
                    "dimension": "page",
                    "operator": "equals",
                    "expression": page_url  # Filter for a specific page URL
                }]
            }]
        }
    sites = webmasters_service.sites().list().execute()
    print(sites)
    response = webmasters_service.searchanalytics().query(siteUrl=SITE_URL, body=request_body).execute()
    print(response.get('rows'))
    return response.get("rows", [])
# get_search_console_data(page_url="https://theplantsmall.com/")
from datetime import datetime
from datetime import timedelta
all_urls = []
pages_data = []
def get_all_indexed_urls(site_url): 
    """Retrieves a list of URLs that have appeared in Google Search results."""
    try:
        credentials = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
        service = build('searchconsole', 'v1', credentials=credentials)

        # Set date range to the last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        # Define the query body to get data by page
        # request_body = {
        #     "startDate": start_date.strftime('%Y-%m-%d'),
        #     "endDate": end_date.strftime('%Y-%m-%d'),
        #     "dimensions": ["page"],
        #     "rowLimit": 25000  # Set a high limit to get more URLs
        # }
        request_body = {
    "startDate": start_date.strftime('%Y-%m-%d'),
    "endDate": end_date.strftime('%Y-%m-%d'),
    "dimensions": ["query","country"], # Add 'country' to the dimensions
    "dimensionFilterGroups": [{
        "filters": [{
            "dimension": "country",
            "operator": "equals",
            "expression": "pak"  # Use the lowercase country code (e.g., 'usa', 'gbr', 'deu')
        }]
    }],
    "rowLimit": 25000
}
        
        # Make the API request
        response = service.searchanalytics().query(
            siteUrl=site_url,
            body=request_body
        ).execute()
        # print(response.keys())
        if 'rows' in response:
            print(f"URLs with search data for {site_url}:")
            print(f"Total rows: {len(response.get('rows'))}")
            for row in response['rows']:
                all_urls.append(row.get('keys')[0])
                # print(f"URL: {row['keys'][0]} | Clicks: {row['clicks']} | Impressions: {row['impressions']} | CTR: {row['ctr']} | Position: {row['position']}")
                pages_data.append({"query":row.get('keys')[0],
                                   "clicks":row.get('clicks'),
                                   "impressions":row.get('impressions'),
                                   "ctr":round(row.get('ctr'), 2),
                                   "position":round(row.get('position'), 2)})
            with open("shopify_agent/data_of_queries_latest.json", "w") as file:
                json.dump(pages_data, file, indent=4)
            # with open("shopify_agent/data_of_all_pages.json", "w") as file:
            #     json.dump(pages_data, file, indent=4)
            return all_urls
        else:
            print("No search data found for this site in the last 30 days.")

    except Exception as e:
        print(f"An error occurred: {e}")

all_urls = get_all_indexed_urls(site_url=SITE_URL)
# print(all_urls)
# print(len(all_urls))

from google.oauth2 import service_account
from googleapiclient.discovery import build


def inspect_url_for_page_experience(site_url, url_to_inspect):
    """
    Inspects a single URL and prints its page experience status.
    """
    try:
        credentials = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
        service = build('searchconsole', 'v1', credentials=credentials)

        request_body = {
            'inspectionUrl': url_to_inspect,
            'siteUrl': site_url,
            'languageCode': 'en-US'
        }
        
        response = service.urlInspection().index().inspect(body=request_body).execute()
        # print(response)
        # print(response['inspectionResult'])
        inspection_result = response['inspectionResult']
        inspection_result_ = inspection_result.get('indexStatusResult')
        # print(inspection_result_.get('lastCrawlTime'),inspection_result_.get('googleCanonical'),inspection_result_.get('userCanonical'),)
        # print(f"URL: {url_to_inspect}")
        print(f"Mobile Usability: {inspection_result['mobileUsabilityResult']}")
        
        with open("shopify_agent/data_of_all_pages.json", "r") as file:
            data = json.load(file)
        for p in data:
            
            if p.get("url") == url_to_inspect:  
                p["indexstatusresult_verdict"] = inspection_result.get('indexStatusResult').get('verdict')
                p["coverage_state"] = inspection_result.get('indexStatusResult').get('coverageState')
                p["robotsTxtState"] = inspection_result.get('indexStatusResult').get('robotsTxtState')
                p["indexingState"] = inspection_result.get('indexStatusResult').get('indexingState')
                p["pageFetchState"] = inspection_result.get('indexStatusResult').get('pageFetchState')
                p["crawledAs"] = inspection_result.get('indexStatusResult').get('crawledAs')
                p["mobileUsabilityResult"] = inspection_result.get('mobileUsabilityResult').get('verdict')
                p["referringUrls"] = inspection_result.get('indexStatusResult').get('referringUrls')
                p["lastCrawlTime"] = inspection_result.get('indexStatusResult').get('lastCrawlTime')
                p["googleCanonical"] = inspection_result.get('indexStatusResult').get('googleCanonical')
                p["userCanonical"] = inspection_result.get('indexStatusResult').get('userCanonical')
                if inspection_result.get('richResultsResult'):
                    p["richResultsResult"] = inspection_result.get('richResultsResult')
                else:
                    p["richResultsResult"] = {}
                break
        with open("shopify_agent/data_of_all_pages.json", "w") as file:
                    json.dump(data, file, indent=4)
    except Exception as e:
        print(f"An error occurred for {url_to_inspect}: {e}")


""" for url in all_urls:
    print(url)
    inspect_url_for_page_experience(SITE_URL, url)
    print("-" * 20) """

import requests
import json

def get_pagespeed_insights(url, api_key):
    """
    Fetches PageSpeed Insights data for a single URL.
    
    Args:
        url (str): The URL to inspect.
        api_key (str): Your Google API key.
    
    Returns:
        dict: A dictionary containing the API response.
    """
    api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&key={api_key}"
    
    try:
        response = requests.get(api_url)
        # print(response)
        response.raise_for_status()  # Raises an exception for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {url}: {e}")
        return None

def process_and_print_cwv(pagespeed_data):
    """Processes the API response and prints Core Web Vitals."""
    if not pagespeed_data or 'loadingExperience' not in pagespeed_data:
        print("No Core Web Vitals field data available for this URL.")
        return

    print(pagespeed_data.get('kind'))
    print(pagespeed_data.get('captchaResult'))
    print(pagespeed_data.get('originLoadingExperience'))
    
    lighthouse_result = pagespeed_data.get('lighthouseResult', {})
    if lighthouse_result:
        print("\n--- Core Web Vitals (Lab Data via Lighthouse) ---")
        
        # Access metrics directly from the audits key
        audits = lighthouse_result.get('audits', {})
        # print(audits)
        lcp_lab = audits.get('largest-contentful-paint', {})
        
        cls_lab = audits.get('cumulative-layout-shift', {})
        
        inp_lab = audits.get('interactive', {}) # Note: INP is related to Time to Interactive (TBT) in Lighthouse
        score = pagespeed_data["lighthouseResult"]["categories"]["performance"]["score"] * 100

        print(f"PageSpeed Score: {score}")
        if 'displayValue' in lcp_lab:
            print(lcp_lab)
            print(f"LCP: {lcp_lab['displayValue']} (from lab test)")
        if 'displayValue' in cls_lab:
            print(cls_lab)
            print(f"CLS: {cls_lab['displayValue']} (from lab test)")
        if 'displayValue' in inp_lab:
            print(inp_lab)
            print(f"TBT: {inp_lab['displayValue']} (from lab test)")
        
        
    return lcp_lab['displayValue'], cls_lab['displayValue'], inp_lab['displayValue'], score
        
    """ cwv_metrics = pagespeed_data['loadingExperience']['metrics']
    
    lcp_data = cwv_metrics.get('LARGEST_CONTENTFUL_PAINT_MS', {})
    cls_data = cwv_metrics.get('CUMULATIVE_LAYOUT_SHIFT_SCORE', {})
    inp_data = cwv_metrics.get('INTERACTION_TO_NEXT_PAINT_MS', {})
    
    print("--- Core Web Vitals (Field Data) ---")
    
    if lcp_data:
        lcp_percentile = lcp_data['percentile']
        lcp_category = lcp_data['category']
        print(f"LCP: {lcp_percentile} ms ({lcp_category})")
    
    if inp_data:
        inp_percentile = inp_data['percentile']
        inp_category = inp_data['category']
        print(f"INP: {inp_percentile} ms ({inp_category})")

    if cls_data:
        cls_percentile = cls_data['percentile']
        cls_category = cls_data['category']
        print(f"CLS: {cls_percentile} ({cls_category})") """
from dotenv import load_dotenv
load_dotenv()
import os
CLOUD_PROJECT_API_KEY = os.environ.get('GOOGLE_CLOUD_PROJECT_API_KEY')
API_KEY = CLOUD_PROJECT_API_KEY
target_url = "https://theplantsmall.com/"
# new_urls = ['https://theplantsmall.com/store/product/25/',"https://theplantsmall.com/store/product/333/","https://www.theplantsmall.com/store/product/168/"]
# for url in all_urls:
#     print(f"Checking: {url}")
#     data = get_pagespeed_insights(url, API_KEY)
#     if data:
#         lcp, cls, inp, score = process_and_print_cwv(data)
#         with open("shopify_agent/data_of_all_pages.json", "r") as file:
#             data_ = json.load(file)
#         for p in data_:
#             if p.get('url') == url:
#                 p["lcp"] = lcp
#                 p["cls"] = cls
#                 p["inp"] = inp
#                 p['pagespeed_score'] = score
            
#         with open("shopify_agent/data_of_all_pages.json", "w") as file:
#             json.dump(data_, file, indent=4)

def get_all_indexed_urls_per_day(site_url):
    """Retrieves a list of URLs that have appeared in Google Search results."""
    try:
        credentials = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
        service = build('searchconsole', 'v1', credentials=credentials)

        # Set date range to the last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        request_body = { 
    "startDate": start_date.strftime('%Y-%m-%d'),
    "endDate": end_date.strftime('%Y-%m-%d'),
    "dimensions": ["date","page", "query", "country"],  # include 'date'
    "dimensionFilterGroups": [{
        "filters": [{
            "dimension": "country",
            "operator": "equals",
            "expression": "pak"  # country code
        }]
    }],
    "rowLimit": 25000
}
        
        # Make the API request
        response = service.searchanalytics().query(
            siteUrl=site_url,
            body=request_body
        ).execute()
        print(response.keys())
        if 'rows' in response:
            print(f"Total rows: {len(response['rows'])}")
            for row in response['rows']:
                date = row['keys'][0]
                page = row['keys'][1]   # first dimension is date
                query = row['keys'][2]    # second is page
                country = row['keys'][3]  # third is country

                pages_data.append({
                    "date": date,
                    "page": page,
                    "query": query,
                    "country": country,
                    "clicks": row['clicks'],
                    "impressions": row['impressions'],
                    "ctr": round(row['ctr'], 2),
                    "position": round(row['position'], 2)
                })
            with open("shopify_agent/data_of_pages_wrt_queries_daily.json", "w") as file:
                json.dump(pages_data, file, indent=4)
            
        else:
            print("No search data found for this site in the last 30 days.")

    except Exception as e:
        print(f"An error occurred: {e}")

# get_all_indexed_urls_per_day(site_url=SITE_URL)
creds = service_account.Credentials.from_service_account_file(KEY_FILE, scopes=SCOPES)
# webmasters_service = build('searchconsole', 'v1', credentials=creds)
# sitemaps = webmasters_service.sitemaps().list(siteUrl=SITE_URL).execute()
# print(sitemaps)


