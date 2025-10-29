import requests
import os
import json
import re
import sqlite3
from dotenv import load_dotenv
load_dotenv()
def get_shopify_data(shop_name, admin_access_token):
    url = f"https://{shop_name}.myshopify.com/admin/api/2025-01/products.json"
    headers = {
        "X-Shopify-Access-Token": admin_access_token,
        "Content-Type": "application/json"
    }
    folder_name = f"{shop_name}_products"
    response = requests.get(url, headers=headers)
    details_of_all_products = []
    if response.status_code == 200:
        products = response.json().get("products", [])
        for product in products:
            import re
            html_content = product['body_html']
            clean_text = re.sub(r'<[^>]*>', '', html_content)
            product['body_html'] = clean_text.strip()
            product['product_url'] = f"https://{shop_name}.myshopify.com/products/{product.get('handle')}"
            details_of_all_products.append(product)
            print(f"{product['id']} - {product['title']} - {product.get('vendor')} - {product.get('image').get('src')}")
        folder_path = os.path.join(os.getcwd(), folder_name)
        os.makedirs(folder_path, exist_ok=True)
        file_name = f"data_of_shopify_products_{shop_name}.json"
        full_file_path = os.path.join(folder_path, file_name)
        with open(full_file_path, "w") as file:
            json.dump(details_of_all_products, file, indent=4)
        print(f"Data successfully written to: {full_file_path}")
shop_name = os.environ.get('SHOPIFY_SHOP_NAME')
admin_access_token = os.environ.get('SHOPIFY_ACCESS_TOKEN')
# get_shopify_data(shop_name, admin_access_token)

def create_schema(db_path=f'main_db_for_{shop_name}.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create pages table
    c.execute('''
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE,
            robots_txt_state TEXT,
            indexing_state TEXT,
            page_fetch_state TEXT,
            crawled_as TEXT,
            coverage_state TEXT,
            mobileUsabilityResult TEXT,
            indexstatusresult_verdict TEXT,
            referringUrls TEXT,
            userCanonical TEXT,  
            googleCanonical TEXT,
            lastCrawlTime TEXT
        )
    ''')

    # Create performance_metrics table
    c.execute('''
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY,
            page_id INTEGER,
            clicks INTEGER,
            impressions INTEGER,
            ctr REAL,
            position REAL,
            FOREIGN KEY (page_id) REFERENCES pages (id)
        )
    ''')

    # Create rich_result_issues table
    c.execute('''
        CREATE TABLE IF NOT EXISTS rich_result_issues (
            id INTEGER PRIMARY KEY,
            page_id INTEGER,
            rich_result_type TEXT,
            issue_message TEXT,
            severity TEXT,
            FOREIGN KEY (page_id) REFERENCES pages (id)
        )
    ''')
    #Query Performance table
    c.execute('''
            CREATE TABLE IF NOT EXISTS query_performance (
                id INTEGER PRIMARY KEY,
                query TEXT UNIQUE,
                clicks INTEGER,
                impressions INTEGER,
                ctr REAL,
                position REAL
            )
        ''')
    # Create the daily_page_metrics table with a foreign key to the pages table
    c.execute('''
            CREATE TABLE IF NOT EXISTS daily_page_metrics (
                id INTEGER PRIMARY KEY,
                page_id INTEGER,
                date TEXT,
                country TEXT,
                clicks INTEGER,
                impressions INTEGER,
                ctr REAL,
                position REAL,
                FOREIGN KEY (page_id) REFERENCES pages(id)
            )
        ''')
    # Create a 'queries' table to store unique search queries
    c.execute('''
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY,
            query TEXT UNIQUE
        )
    ''')
    # This table links pages and queries, storing their combined performance metrics.
    c.execute('''
            CREATE TABLE IF NOT EXISTS page_query_performance (
                id INTEGER PRIMARY KEY,
                page_id INTEGER,
                query_id INTEGER,
                country TEXT,
                clicks INTEGER,
                impressions INTEGER,
                ctr REAL,
                position REAL,
                FOREIGN KEY (page_id) REFERENCES pages(id),
                FOREIGN KEY (query_id) REFERENCES queries(id)
            )
        ''')
    # Create the new table to link pages and queries with daily metrics
    c.execute('''
            CREATE TABLE IF NOT EXISTS daily_page_query_metrics (
                id INTEGER PRIMARY KEY,
                page_id INTEGER,
                query_id INTEGER,
                date TEXT,
                country TEXT,
                clicks INTEGER,
                impressions INTEGER,
                ctr REAL,
                position REAL,
                FOREIGN KEY (page_id) REFERENCES pages(id),
                FOREIGN KEY (query_id) REFERENCES queries(id)
            )
        ''')
    # Create the core_web_vitals table
    c.execute('''
            CREATE TABLE IF NOT EXISTS core_web_vitals (
                id INTEGER PRIMARY KEY,
                page_id INTEGER,
                lcp REAL,
                cls REAL,
                inp REAL,
                FOREIGN KEY (page_id) REFERENCES pages(id)
            )
        ''')
    # Create the products table if it doesn't exist
    c.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                title TEXT,
                body_html TEXT,
                vendor TEXT,
                product_type TEXT,
                created_at TEXT,
                handle TEXT,
                updated_at TEXT,
                published_at TEXT,
                template_suffix TEXT,
                published_scope TEXT,
                tags TEXT,
                status TEXT,
                admin_graphql_api_id TEXT,
                variants TEXT,
                options TEXT,
                images TEXT,
                product_url TEXT
            )
        ''')
    conn.commit()
    conn.close()

    print("Database schema created successfully.")
# create_schema()

def save_products_data_in_db(file_name, db_path=f"main_db_for_{shop_name}.db"):
    # Load data from the JSON file
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    folder_name = f"{shop_name}_products"
    folder_path = os.path.join(os.getcwd(), folder_name)
    full_file_path = os.path.join(folder_path, file_name)
    with open(full_file_path, 'r') as f:
        products_data = json.load(f)
    # Iterate through the data and insert into the products table
    for record in products_data:
        # Serialize nested lists/dictionaries to JSON strings
        variants_json = json.dumps(record.get('variants'))
        options_json = json.dumps(record.get('options'))
        images_json = json.dumps(record.get('images'))
        c.execute('''
            INSERT OR REPLACE INTO products (
                id, title, body_html, vendor, product_type, created_at, handle,
                updated_at, published_at, template_suffix, published_scope,
                tags, status, admin_graphql_api_id, variants, options, images, product_url
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.get('id'),
            record.get('title'),
            record.get('body_html'),
            record.get('vendor'),
            record.get('product_type'),
            record.get('created_at'),
            record.get('handle'),
            record.get('updated_at'),
            record.get('published_at'),
            record.get('template_suffix'),
            record.get('published_scope'),
            record.get('tags'),
            record.get('status'),
            record.get('admin_graphql_api_id'),
            variants_json,
            options_json,
            images_json,
            record.get('product_url')
        ))
    conn.commit()
    print("Product data inserted/updated successfully.")

# save_products_data_in_db(file_name=f"data_of_shopify_products_{shop_name}.json")