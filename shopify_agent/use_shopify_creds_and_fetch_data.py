import re
import requests
import json
import os
import sys
import django
from dotenv import load_dotenv
load_dotenv()
# --- Ensure Python knows where to find your project ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # one level up
shop_name = os.environ.get('SHOPIFY_SHOP_NAME')
access_token = os.environ.get('SHOPIFY_ACCESS_TOKEN')
# --- Setup Django environment ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
def save_products_to_json(shop_name, access_token):
    
    url = f"https://{shop_name}.myshopify.com/admin/api/2025-01/products.json"

    headers = {
        "X-Shopify-Access-Token":access_token,
        "Content-Type": "application/json"}
    product_ids = []
    response = requests.get(url, headers=headers)
    details_of_all_products = []
    if response.status_code == 200:
        products = response.json().get("products", [])
        for product in products:
            html_content = product['body_html']
            clean_text = re.sub(r'<[^>]*>', '', html_content)
            product['body_html'] = clean_text.strip()
            product['product_url'] = f"https://{shop_name}.myshopify.com/products/{product.get('handle')}"
            details_of_all_products.append(product)
            product_ids.append(product.get('id'))
    

    # --- Configuration (Replace with your actual values) ---
    SHOPIFY_SHOP_URL = shop_name
    ADMIN_API_VERSION = "2025-01"  # Use a recent, stable version
    ACCESS_TOKEN = access_token # Your Admin API Access Token
    # PRODUCT_ID = "9898610327865" # The product's GraphQL ID

    # The expanded GraphQL query to get most relevant fields
    QUERY_ALL_FIELDS = """
    query getProductDetails($id: ID!) {
    product(id: $id) {
        # Core Product Fields
        id
        title
        handle
        description
        descriptionHtml
        productType
        vendor
        status
        tags
        createdAt
        updatedAt
        publishedAt

        
        
        # URL and Publication Info
        onlineStoreUrl
        onlineStorePreviewUrl
        publishedAt
        
        seo {
            title 
            description 
        }
        # SEO Fields (via Metafields)
        metafields(first: 10) {
        edges {
            node {
            key
            value
            namespace
            }
        }
        }
        
        # Images and Media
        images(first: 10) {
        edges {
            node {
            id
            url(transform: {maxWidth: 500, maxHeight: 500})
            altText
            width
            height
            }
        }
        }

        # Product Variants (essential for inventory/pricing)
        variants(first: 10) {
            edges {
                node {
                    id
                    sku
                    price
                    inventoryQuantity
                }
            }
        }
        
        # Options (Size, Color, etc.)
        options {
        id
        name
        values
        }
    }
    }
    """

    def get_all_product_details(product_id):
        """Fetches comprehensive product details using the Shopify GraphQL Admin API."""
        
        url = f"https://{SHOPIFY_SHOP_URL}.myshopify.com/admin/api/{ADMIN_API_VERSION}/graphql.json"
        
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": ACCESS_TOKEN
        }
        
        payload = {
            "query": QUERY_ALL_FIELDS,
            "variables": {
                "id": f"gid://shopify/Product/{product_id}"
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            
            data = response.json()
            
            if 'errors' in data:
                print("GraphQL Errors:", data['errors'])
                return None

            product = data['data']['product']
            if not product:
                print(f"Error: Product with ID {product_id} not found.")
                return None

            # --- Output Summary (for quick viewing) ---
            print("✅ Comprehensive Product Details Retrieved Successfully:")
            print("-" * 50)
            print(f"Product ID: {product.get('id')}")
            print(f"Title: {product.get('title')}")
            print(f"Handle: {product.get('handle')}")
            print(f"Description: {product.get('description')}")
            print(f"Product Type: {product.get('productType')}")
            print(f"Vendor: {product.get('vendor')}")
            print(f"Status: {product.get('status')}")
            print(f"Online URL: {product.get('onlineStoreUrl')}")
            print(f"Tags: {product.get('tags')}")
            print(f"Created At: {product.get('createdAt')}")
            print(f"Updated At: {product.get('updatedAt')}")
            print(f"Published At: {product.get('publishedAt')}")
            print(f"Online Store Preview URL: {product.get('onlineStorePreviewUrl')}")
            print(f"Product SEO: {product.get('seo')}")
            print(f"Images Found: {len(product.get('images', {}).get('edges', []))}")
            print(f"Variants Found: {len(product.get('variants', {}).get('edges', []))}")
            print("-" * 50)
            # print("Raw JSON Data (Full Response):")
            # print(product)
            description_html = product.get('descriptionHtml')
            from urllib.parse import urlparse
            if not description_html:
                print("No description HTML found. (0 internal links)")
                
            from bs4 import BeautifulSoup
            # 2. Parse the HTML to find internal links
            soup = BeautifulSoup(description_html, 'html.parser')
            internal_links = []


            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href'].strip()
                link_text = a_tag.get_text().strip()
                
                is_internal = False
                
                # Check for relative URLs (e.g., /products/t-shirt)
                if href.startswith('/'):
                    is_internal = True
                

                if is_internal:
                    internal_links.append({
                        "href": href,
                        "text": link_text
                    })
            print(internal_links)
            product['internal_links'] = internal_links
            
            return product
            
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            return None
    details_products = []
    for id in product_ids:
        product = get_all_product_details(id)
        details_products.append(product)

    with open(f"shopify_agent/data_of_shopify_products_{shop_name}.json", "w") as file:
            json.dump(details_products, file, indent=4)

# save_products_to_json(shop_name, access_token)
# import sqlite3

# def insert_products_data(file_name, db_path=f'main_db_for_{shop_name}.db'):
#     conn = None 
#     try:
#         conn = sqlite3.connect(db_path)
#         c = conn.cursor()

#         # Table Creation remains the same (id TEXT is correct)
#         c.execute('''
#             CREATE TABLE IF NOT EXISTS products_latest (
#                 id TEXT PRIMARY KEY, title TEXT, handle TEXT, description TEXT, 
#                 descriptionHtml TEXT, product_type TEXT, vendor TEXT, status TEXT, 
#                 tags TEXT, created_at TEXT, updated_at TEXT, published_at TEXT, 
#                 online_store_url TEXT, online_store_preview_url TEXT, 
#                 seo TEXT, metafields TEXT, images TEXT, variants TEXT, options TEXT,
#                 internal_links TEXT, seo_score INTEGER, seo_issues TEXT
#             )
#         ''')
        
#         with open(file_name, 'r', encoding='utf-8') as f:
#             products_data = json.load(f)

#         for record in products_data:
#             # --- Robust Serialization (JSON fields) ---
            
#             # 1. Images, Variants, Metafields: Extract 'edges' list
#             images_data = record.get('images', {}).get('edges', [])
#             images_json = json.dumps(images_data)

#             variants_data = record.get('variants', {}).get('edges', [])
#             variants_json = json.dumps(variants_data)

#             metafields_data = record.get('metafields', {}).get('edges', [])
#             metafields_json = json.dumps(metafields_data)

#             # 2. Options, Tags: Already lists
#             options_json = json.dumps(record.get('options', []))
#             tags_json = json.dumps(record.get('tags', []))

#             # 3. SEO: Convert dict to list of dicts, then serialize
#             seo_data_dict = record.get('seo', {})
#             seo_data_list = [seo_data_dict] 
#             seo_json = json.dumps(seo_data_list)
            
#             # --- Explicit Type Casting (TEXT fields) ---
#             # Cast ALL simple strings to str() to eliminate the mismatch.
#             product_id = str(record.get('id', ""))
#             title = str(record.get('title', ""))
#             handle = str(record.get('handle', ""))
#             description = str(record.get('description', ""))
#             description_html = str(record.get('descriptionHtml', ""))
#             product_type = str(record.get('productType', ""))
#             vendor = str(record.get('vendor', ""))
#             status = str(record.get('status', ""))
#             created_at = str(record.get('createdAt', ""))
#             updated_at = str(record.get('updatedAt', ""))
#             published_at = str(record.get('publishedAt', ""))
#             online_store_url = str(record.get('onlineStoreUrl', ""))
#             online_store_preview_url = str(record.get('onlineStorePreviewUrl', ""))
#             internal_links = str(record.get('internal_links', ""))
            
#             # --- Insertion ---
#             c.execute('''
#                 INSERT OR REPLACE INTO products_latest (
#                     id, title, handle, description, descriptionHtml, product_type, vendor, status, tags, created_at, updated_at,
#                     published_at, online_store_url, online_store_preview_url,
#                     seo, metafields, images, variants, options, internal_links
#                 )
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             ''', (
#                 product_id,
#                 title,
#                 handle,
#                 description,
#                 description_html,
#                 product_type,
#                 vendor,
#                 status,
#                 tags_json,
#                 created_at,
#                 updated_at,
#                 published_at,
#                 online_store_url,
#                 online_store_preview_url,
#                 seo_json,
#                 metafields_json,
#                 images_json,
#                 variants_json,
#                 options_json,
#                 internal_links
#             ))
        
#         conn.commit()
#         print("Product data inserted/updated successfully. ✅")

#     except FileNotFoundError:
#         print(f"Error: The file '{file_name}' was not found. ❌")
#     except sqlite3.Error as e:
#         # This printout is still useful to identify the failing record's ID
#         print(f"\n--- ERROR FOUND ---")
#         print(f"Database error on record ID: {record.get('id')} ⚠️")
#         print(f"Error: {e}")
#         # If the error still occurs, the issue is environmental or a non-standard type in the JSON
#         # that str() cannot fix (e.g., an attempt to insert a Python object not covered by json.dumps)
#     except Exception as e:
#         print(f"An unexpected error occurred: {e} 💥")
#     finally:
#         if conn:
#             conn.close()

# # insert_products_data(f'shopify_agent/data_of_shopify_products_{shop_name}.json', f'main_db_for_{shop_name}.db')

import json
from shopify_manager.models import Product, Page_Query_Metrics, Website_Issues
from django.utils.dateparse import parse_datetime

def insert_products_data(file_name,store_name):
    with open(file_name, 'r', encoding='utf-8') as f:
        products_data = json.load(f)

    for record in products_data:
        # Parse dates safely
        def parse_date(value):
            try:
                return parse_datetime(value)
            except Exception:
                return None

        # Extract all fields
        store_name=store_name,
        product_id = str(record.get('id', ""))
        title = record.get('title')
        handle = record.get('handle')
        description = record.get('description')
        description_html = record.get('descriptionHtml')
        product_type = record.get('productType')
        vendor = record.get('vendor')
        status = record.get('status')
        created_at = parse_date(record.get('createdAt'))
        updated_at = parse_date(record.get('updatedAt'))
        published_at = parse_date(record.get('publishedAt'))
        online_store_url = record.get('onlineStoreUrl')
        online_store_preview_url = record.get('onlineStorePreviewUrl')
        seo = record.get('seo', {})
        metafields = record.get('metafields', {}).get('edges', [])
        images = record.get('images', {}).get('edges', [])
        variants = record.get('variants', {}).get('edges', [])
        options = record.get('options', [])
        internal_links = record.get('internal_links', [])

        # Create or update record in DB
        Product.objects.update_or_create(
            store_name = store_name,
            id=product_id,
            defaults={
                'title': title,
                'handle': handle,
                'description': description,
                'description_html': description_html,
                'product_type': product_type,
                'vendor': vendor,
                'status': status,
                'tags': record.get('tags', []),
                'created_at': created_at,
                'updated_at': updated_at,
                'published_at': published_at,
                'online_store_url': online_store_url,
                'online_store_preview_url': online_store_preview_url,
                'seo': seo,
                'metafields': metafields,
                'images': images,
                'variants': variants,
                'options': options,
                'internal_links': internal_links,
            }
        )
    print("✅ All product data inserted/updated successfully.")

# insert_products_data(f'shopify_agent/data_of_shopify_products_{shop_name}.json')

def insert_pages_query_data(file_name):
    """
    Reads a JSON file and inserts page query metrics into the PageQueryMetric model.
    """
    try:
        # Load JSON data
        with open(file_name, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Prepare list for bulk insert
        metrics_to_create = []

        for record in data:
            page = record.get('page')
            query = record.get('query')
            clicks = record.get('clicks') or 0
            impressions = record.get('impressions') or 0
            ctr = record.get('ctr') or 0.0
            position = record.get('position') or 0.0

            metrics_to_create.append(Page_Query_Metrics(
                page=page,
                query=query,
                clicks=clicks,
                impressions=impressions,
                ctr=ctr,
                position=position,
            ))

        # Bulk insert for speed (faster than individual saves)
        Page_Query_Metrics.objects.bulk_create(metrics_to_create, ignore_conflicts=True)

        print(f"✅ Inserted {len(metrics_to_create)} records into PageQueryMetric successfully.")

    except FileNotFoundError:
        print(f"❌ Error: File '{file_name}' not found.")
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON format in '{file_name}'.")
    except Exception as e:
        print(f"💥 Unexpected error while inserting Page Query Metrics: {e}")
def safe_float(value):
    if not value:
        return None
    try:
        # Remove non-breaking spaces and units like 's' or 'ms'
        clean = str(value).replace('\xa0', '').replace('s', '').strip()
        return float(clean)
    except ValueError:
        return None
# insert_pages_query_data(f'shopify_agent/website_query_metrics.json')
def insert_website_issues_data(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            website_data = json.load(f)

        for record in website_data:
            Website_Issues.objects.update_or_create(
                page=record.get('page'),
                defaults={
                    'indexstatusresult_verdict': record.get('indexstatusresult_verdict'),
                    'coverage_state': record.get('coverage_state'),
                    'robotsTxtState': record.get('robotsTxtState'),
                    'indexingState': record.get('indexingState'),
                    'pageFetchState': record.get('pageFetchState'),
                    'crawledAs': record.get('crawledAs'),
                    'mobileUsabilityResult': record.get('mobileUsabilityResult'),
                    'referringUrls': record.get('referringUrls', []),
                    'lastCrawlTime': record.get('lastCrawlTime'),
                    'googleCanonical': record.get('googleCanonical'),
                    'userCanonical': record.get('userCanonical'),
                    'lcp': safe_float(record.get('lcp')),
                    'cls': safe_float(record.get('cls')),
                    'inp': safe_float(record.get('inp')),
                    'pagespeedscore': float(record.get('pagespeed_score')) if record.get('pagespeed_score') else None,
                    'richResultsResult': record.get('richResultsResult', {}),
                    'issues': record.get('issues', None),
                }
            )

        print("✅ Website Issues data inserted/updated successfully.")

    except FileNotFoundError:
        print(f"❌ Error: The file '{file_name}' was not found.")
    except json.JSONDecodeError:
        print("💥 JSON format error — please check your file content.")
    except Exception as e:
        print(f"💥 Unexpected error occurred: {e}")
# insert_website_issues_data('shopify_agent/data_of_pages_indexing_mobile_issues.json')