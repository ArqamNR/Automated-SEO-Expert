from tabulate import tabulate
import requests
import os
import json
import re

def download_image(url: str, save_path: str) -> None:
    """Download an image from a given URL and save it locally."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
                
        print(f"Image downloaded successfully: {save_path}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to download image: {e}")
        raise


url = f"https://{shop_name_electronics}.myshopify.com/admin/api/2025-01/products.json"
headers = {
    "X-Shopify-Access-Token": admin_access_token_electronics,
    "Content-Type": "application/json"
}
# url_collections = f"https://{shop_name}.myshopify.com/admin/api/2025-01/custom_collections.json"
# response = requests.get(url, headers=headers)
# # print(response)
# if response.status_code == 200:
#     products = response.json().get("products", [])
#     images_folder = "shopify_agent"
#     # print(products[0])
#     os.makedirs(images_folder, exist_ok=True)

#     # Collect rows for tabulation
#     table_rows = []

#     for product in products[0:5]:
#         print(product.get('image'))
#         image_path = f"{product.get('title')}.png"
        
#         # Download image if not already present
#         if not os.path.exists(os.path.join(images_folder, image_path)):
#             if product.get('image'):
#                 download_image(product['image']['src'], os.path.join(images_folder, image_path))
#         else:
#             print(f"Image {image_path} is already in the images folder.")

#         # Clean HTML description
#         html_content = product.get('body_html', '')
#         clean_text = re.sub(r'<[^>]*>', '', html_content)
#         product['body_html'] = clean_text.strip()
#         image = product.get('image', {}).get('src', '')


# else:
#     print("Error:", response.status_code, response.text)


url = f"https://{shop_name}.myshopify.com/admin/api/2025-01/products.json"

headers = {
    "X-Shopify-Access-Token": admin_access_token,
    "Content-Type": "application/json"
}
import re
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
        # print(product.get('images'))
        # print(f"{product['id']} - {product['title']} - {product.get('vendor')} - {product.get('image').get('src')}")
    # with open("shopify_agent/data_of_shopify_products_electronics.json", "w") as file:
    #     json.dump(details_of_all_products, file, indent=4)
# for id in product_ids[0:2]:
#     url = f"https://{shop_name}.myshopify.com/admin/api/2025-01/products/{id}/metafields.json"
#     response = requests.get(url, headers=headers)
#     print(response.json())

import requests
import json

# --- Configuration (Replace with your actual values) ---
SHOPIFY_SHOP_URL = shop_name
ADMIN_API_VERSION = "2025-01"  # Use a recent, stable version
ACCESS_TOKEN = admin_access_token # Your Admin API Access Token
PRODUCT_ID = "9898610327865" # The product's GraphQL ID

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
# for id in product_ids:
#     product = get_all_product_details(id)
#     details_products.append(product)

# with open("shopify_agent/data_of_shopify_products_complete.json", "w") as file:
#         json.dump(details_products, file, indent=4)