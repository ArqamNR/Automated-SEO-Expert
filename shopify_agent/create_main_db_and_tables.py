import sqlite3
import json
def create_schema(db_path=f'main_db_for_the_plants_mall.db'):
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
            lastCrawlTime TEXT,
            pagespeed_score INTEGER
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
            CREATE TABLE IF NOT EXISTS daily_query_metrics (
                id INTEGER PRIMARY KEY,
                query_id INTEGER,
                date TEXT,
                country TEXT,
                clicks INTEGER,
                impressions INTEGER,
                ctr REAL,
                position REAL,
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

def insert_page_data(data, db_path='main_db_for_the_plants_mall.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    for page_data in data:
        json_string = json.dumps(page_data.get('referringUrls'))
        # Insert into pages table and get the page_id
        try:
            c.execute('''
                INSERT INTO pages (url, robots_txt_state, indexing_state, page_fetch_state, crawled_as, coverage_state, mobileUsabilityResult, indexstatusresult_verdict, referringUrls, userCanonical, googleCanonical, lastCrawlTime, pagespeed_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                page_data['url'],
                page_data.get('robotsTxtState'),
                page_data.get('indexingState'),
                page_data.get('pageFetchState'),
                page_data.get('crawledAs'),
                page_data.get('coverage_state'),
                page_data.get('mobileUsabilityResult'),
                page_data.get('indexstatusresult_verdict'),
                json_string,
                page_data.get('userCanonical'),
                page_data.get('googleCanonical'),
                page_data.get('lastCrawlTime'),
                page_data.get('pagespeed_score')
            ))
            page_id = c.lastrowid
        except sqlite3.IntegrityError:
            # If the URL already exists, get its page_id
            c.execute('SELECT id FROM pages WHERE url = ?', (page_data['url'],))
            page_id = c.fetchone()[0]
        # Insert into performance_metrics table
        c.execute('''
            INSERT INTO performance_metrics (page_id, clicks, impressions, ctr, position)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            page_id,
            page_data.get('clicks'),
            page_data.get('impressions'),
            page_data.get('ctr'),
            page_data.get('position')
        ))

        # Insert into rich_result_issues table if issues exist
        if page_data['richResultsResult'] != {} and page_data['richResultsResult']['verdict'] == 'PASS':
            for item in page_data['richResultsResult']['detectedItems']:
                for issue in item['items']:
                    for specific_issue in issue['issues']:
                        c.execute('''
                            INSERT INTO rich_result_issues (page_id, rich_result_type, issue_message, severity)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            page_id,
                            item['richResultType'],
                            specific_issue.get('issueMessage'),
                            specific_issue.get('severity')
                        ))
    
    conn.commit()
    conn.close()
    print("Data insertion complete.")
with open("shopify_agent/data_of_all_pages.json", "r") as file:
    data = json.load(file)
# insert_page_data(data)

def insert_query_data(file_name, db_path='main_db_for_the_plants_mall.db'):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Create the new table for query data
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

        # Load data from the JSON file
        with open(file_name, 'r') as f:
            query_data = json.load(f)

        # Iterate through the data and insert into the new table
        for record in query_data:
            c.execute('''
                INSERT OR IGNORE INTO query_performance (query, clicks, impressions, ctr, position)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                record.get('query'),
                record.get('clicks'),
                record.get('impressions'),
                record.get('ctr'),
                record.get('position')
            ))
        
        conn.commit()
        print("Query data inserted successfully.")

    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()
file_to_insert = 'shopify_agent/data_of_queries_latest.json'
# insert_query_data(file_to_insert)

def insert_daily_page_data(file_name, db_path='main_db_for_the_plants_mall.db'):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Create the daily_page_metrics table with a foreign key to the pages table
        c.execute('''
            CREATE TABLE IF NOT EXISTS daily_page_metrics (
                id INTEGER PRIMARY KEY,
                page_id INTEGER,
                date TEXT,
                clicks INTEGER,
                impressions INTEGER,
                ctr REAL,
                position REAL,
                FOREIGN KEY (page_id) REFERENCES pages(id)
            )
        ''')
        
        # Load data from the JSON file
        with open(file_name, 'r') as f:
            daily_data = json.load(f)

        # Iterate through the data and insert into the tables
        for record in daily_data:
            url = record.get('url')
            
            # Step 1: Check if the page URL already exists and get its ID
            c.execute("SELECT id FROM pages WHERE url = ?", (url,))
            page = c.fetchone()
            
            page_id = None
            if page:
                page_id = page[0]
            else:
                # If the URL does not exist, insert it into the pages table
                c.execute("INSERT INTO pages (url) VALUES (?)", (url,))
                page_id = c.lastrowid # Get the ID of the new row

            # Step 2: Insert the daily data into the new table using the page_id
            c.execute('''
                INSERT INTO daily_page_metrics (page_id, date, clicks, impressions, ctr, position)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                page_id,
                record.get('date'),
                record.get('clicks'),
                record.get('impressions'),
                record.get('ctr'),
                record.get('position')
            ))
        
        conn.commit()
        print("Daily page data inserted successfully.")

    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

# Example usage:
# insert_daily_page_data('shopify_agent/data_of_pages_daily_latest.json')
def insert_daily_query_data(file_name, db_path='main_db_for_the_plants_mall.db'):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Create a 'queries' table to store unique search queries
        c.execute('''
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY,
                query TEXT UNIQUE
            )
        ''')

        # Create the 'daily_query_metrics' table with a foreign key to the 'queries' table
        c.execute('''
            CREATE TABLE IF NOT EXISTS daily_query_metrics (
                id INTEGER PRIMARY KEY,
                query_id INTEGER,
                date TEXT,
                country TEXT,
                clicks INTEGER,
                impressions INTEGER,
                ctr REAL,
                position REAL,
                FOREIGN KEY (query_id) REFERENCES queries(id)
            )
        ''')
        
        # Load data from the JSON file
        with open(file_name, 'r') as f:
            daily_data = json.load(f)

        # Iterate through the data and insert into the tables
        for record in daily_data:
            query_text = record.get('query')
            
            # Step 1: Check if the query string already exists and get its ID
            c.execute("SELECT id FROM queries WHERE query = ?", (query_text,))
            query_record = c.fetchone()
            
            query_id = None
            if query_record:
                query_id = query_record[0]
            else:
                # If the query does not exist, insert it into the 'queries' table
                c.execute("INSERT OR IGNORE INTO queries (query) VALUES (?)", (query_text,))
                query_id = c.lastrowid # Get the ID of the new row

            # Step 2: Insert the daily data into the new table using the query_id
            c.execute('''
                INSERT INTO daily_query_metrics (query_id, date, country, clicks, impressions, ctr, position)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                query_id,
                record.get('date'),
                record.get('country'),
                record.get('clicks'),
                record.get('impressions'),
                record.get('ctr'),
                record.get('position')
            ))
        
        conn.commit()
        print("Daily query data inserted successfully.")

    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

# Example usage:
# insert_daily_query_data('shopify_agent/data_of_queries_daily_latest.json')

def insert_daily_page_query_data(file_name, db_path='main_db_for_the_plants_mall.db'):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

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
        
        # Load data from the JSON file
        with open(file_name, 'r') as f:
            daily_data = json.load(f)

        # Iterate through the data and insert into the tables
        for record in daily_data:
            url = record.get('url')
            query_text = record.get('query')
            
            # Step 1: Check if the page URL exists and get its ID
            c.execute("SELECT id FROM pages WHERE url = ?", (url,))
            page_record = c.fetchone()
            
            page_id = None
            if page_record:
                page_id = page_record[0]
            else:
                # If the URL does not exist, insert it into the pages table
                c.execute("INSERT INTO pages (url) VALUES (?)", (url,))
                page_id = c.lastrowid # Get the ID of the new row

            # Step 2: Check if the query string exists and get its ID
            c.execute("SELECT id FROM queries WHERE query = ?", (query_text,))
            query_record = c.fetchone()
            
            query_id = None
            if query_record:
                query_id = query_record[0]
            else:
                # If the query does not exist, insert it into the queries table
                c.execute("INSERT OR IGNORE INTO queries (query) VALUES (?)", (query_text,))
                query_id = c.lastrowid # Get the ID of the new row

            # Step 3: Insert the daily data into the new table using the page_id and query_id
            c.execute('''
                INSERT INTO daily_page_query_metrics (page_id, query_id, date, country, clicks, impressions, ctr, position)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                page_id,
                query_id,
                record.get('date'),
                record.get('country'),
                record.get('clicks'),
                record.get('impressions'),
                record.get('ctr'),
                record.get('position')
            ))
        
        conn.commit()
        print("Daily page-query data inserted successfully.")

    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

# Example usage:
# insert_daily_page_query_data('shopify_agent/data_of_pages_queries_daily.json')
def insert_core_web_vitals(file_name, db_path='main_db_for_the_plants_mall.db'):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

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

        # Load data from the JSON file
        with open(file_name, 'r') as f:
            vitals_data = json.load(f)

        # Iterate through the data and insert into the tables
        for record in vitals_data:
            url = record.get('url')
            
            # Step 1: Check if the page URL already exists and get its ID
            c.execute("SELECT id FROM pages WHERE url = ?", (url,))
            page = c.fetchone()
            
            page_id = None
            if page:
                page_id = page[0]
            else:
                # If the URL does not exist, insert it into the pages table
                c.execute("INSERT INTO pages (url) VALUES (?)", (url,))
                page_id = c.lastrowid # Get the ID of the new row

            # Clean and convert string values to float for the database
            lcp = record.get('lcp', '0').replace('\u00a0', '')
            cls = record.get('cls', '0').replace('\u00a0', '')
            inp = record.get('inp', '0').replace('\u00a0', '')

            # Step 2: Insert the Core Web Vitals data into the new table using the page_id
            c.execute('''
                INSERT INTO core_web_vitals (page_id, lcp, cls, inp)
                VALUES (?, ?, ?, ?)
            ''', (
                page_id,
                lcp,
                cls,
                inp
            ))
        
        conn.commit()
        print("Core Web Vitals data inserted successfully.")

    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

# Example usage:
# insert_core_web_vitals('shopify_agent/data_of_all_pages.json')

def insert_products_data(file_name, db_path='main_db_for_the_plants_mall.db'):
    """
    Creates a 'products' table and inserts product information from a JSON file.
    Nested data (variants, options, images) is serialized to JSON strings.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Create the products table if it doesn't exist
        c.execute('''
            CREATE TABLE IF NOT EXISTS products_latest (
                id TEXT PRIMARY KEY,
                title TEXT,
                handle TEXT,
                description TEXT,
                descriptionHtml TEXT,
                product_type TEXT,
                vendor TEXT,
                status TEXT,
                tags TEXT,
                created_at TEXT,
                updated_at TEXT,
                published_at TEXT,
                online_store_url TEXT,
                online_store_preview_url TEXT,
                seo TEXT,
                metafields TEXT,
                images TEXT,
                variants TEXT,
                options TEXT
            )
        ''')
        
        # Load data from the JSON file
        with open(file_name, 'r') as f:
            products_data = json.load(f)

        # Iterate through the data and insert into the products table
        for record in products_data:
            # Serialize nested lists/dictionaries to JSON strings
            variants_json = json.dumps(record.get('variants'))
            options_json = json.dumps(record.get('options'))
            images_json = json.dumps(record.get('images'))
            seo_json = json.dumps(record.get('seo'))
            metafields_json = json.dumps(record.get('metafields'))
            tags_data = record.get('tags')
            tags_json = json.dumps(tags_data) if isinstance(tags_data, list) else json.dumps([])
            
            c.execute('''
                INSERT OR REPLACE INTO products_latest (
                    id, title, handle, description, descriptionHtml, product_type, vendor, status, tags, created_at, updated_at,
                    published_at, online_store_url, online_store_preview_url,
                    seo, metafields, images, variants, options
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.get('id'),
                record.get('title'),
                record.get('handle'),
                record.get('description'),
                record.get('descriptionHtml'),
                record.get('productType'),
                record.get('vendor'),
                record.get('status'),
                tags_json,
                record.get('createdAt'),
                record.get('updatedAt'),
                record.get('publishedAt'),
                record.get('onlineStoreUrl'),
                record.get('onlineStorePreviewUrl'),
                seo_json,
                metafields_json,
                images_json,
                variants_json,
                options_json
            ))
        
        conn.commit()
        print("Product data inserted/updated successfully.")

    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

# Example usage:
# insert_products_data('shopify_agent/data_of_shopify_products_complete.json', 'search_console_test.db')

def create_table_for_product_history(db_path=f'search_console_a.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Create pages table
    c.execute('''
        CREATE TABLE IF NOT EXISTS product_history (
            history_id INTEGER PRIMARY KEY,
            product_id TEXT UNIQUE,
            fetch_date TEXT,
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


def create_table_for_products_electronics(db_path=f'search_console_a.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS products_electronics (
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
# create_table_for_products_electronics()
from datetime import date
# create_table_for_product_history()
def insert_products_history(file_name, db_path='search_console_test.db'):
    """
    Creates a 'products' table and inserts product information from a JSON file.
    Nested data (variants, options, images) is serialized to JSON strings.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Create the product history table if it doesn't exist
        c.execute('''
        CREATE TABLE IF NOT EXISTS product_history (
            history_id INTEGER PRIMARY KEY,
            product_id TEXT,
            fetch_date TEXT,
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
        
        # Load data from the JSON file
        with open(file_name, 'r') as f:
            products_data = json.load(f)
        fetch_date = date.today().strftime('%Y-%m-%d')
        # Iterate through the data and insert into the products table
        for record in products_data:
            # Serialize nested lists/dictionaries to JSON strings
            variants_json = json.dumps(record.get('variants'))
            options_json = json.dumps(record.get('options'))
            images_json = json.dumps(record.get('images'))
            
            c.execute('''
                INSERT INTO product_history (
                    product_id, fetch_date, title, body_html, vendor, product_type, created_at, handle,
                    updated_at, published_at, template_suffix, published_scope,
                    tags, status, admin_graphql_api_id, variants, options, images, product_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.get('id'),
                fetch_date,
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

    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()
# insert_products_history(r'C:\Users\NorthRays\Desktop\shopify_agent\data_of_shopify_products_plants_mall.json')

# insert_products_data('shopify_agent/data_of_shopify_products_electronics.json','search_console_a.db')

def insert_products_data(file_name, db_path='main_db_for_the_plants_mall.db'):
    conn = None 
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Table Creation remains the same (id TEXT is correct)
        c.execute('''
            CREATE TABLE IF NOT EXISTS products_latest (
                id TEXT PRIMARY KEY, title TEXT, handle TEXT, description TEXT, 
                descriptionHtml TEXT, product_type TEXT, vendor TEXT, status TEXT, 
                tags TEXT, created_at TEXT, updated_at TEXT, published_at TEXT, 
                online_store_url TEXT, online_store_preview_url TEXT, 
                seo TEXT, metafields TEXT, images TEXT, variants TEXT, options TEXT,
                internal_links TEXT, seo_score INTEGER, seo_issues TEXT
            )
        ''')
        
        with open(file_name, 'r', encoding='utf-8') as f:
            products_data = json.load(f)

        for record in products_data:
            # --- Robust Serialization (JSON fields) ---
            
            # 1. Images, Variants, Metafields: Extract 'edges' list
            images_data = record.get('images', {}).get('edges', [])
            images_json = json.dumps(images_data)

            variants_data = record.get('variants', {}).get('edges', [])
            variants_json = json.dumps(variants_data)

            metafields_data = record.get('metafields', {}).get('edges', [])
            metafields_json = json.dumps(metafields_data)

            # 2. Options, Tags: Already lists
            options_json = json.dumps(record.get('options', []))
            tags_json = json.dumps(record.get('tags', []))

            # 3. SEO: Convert dict to list of dicts, then serialize
            seo_data_dict = record.get('seo', {})
            seo_data_list = [seo_data_dict] 
            seo_json = json.dumps(seo_data_list)
            
            # --- Explicit Type Casting (TEXT fields) ---
            # Cast ALL simple strings to str() to eliminate the mismatch.
            product_id = str(record.get('id', ""))
            title = str(record.get('title', ""))
            handle = str(record.get('handle', ""))
            description = str(record.get('description', ""))
            description_html = str(record.get('descriptionHtml', ""))
            product_type = str(record.get('productType', ""))
            vendor = str(record.get('vendor', ""))
            status = str(record.get('status', ""))
            created_at = str(record.get('createdAt', ""))
            updated_at = str(record.get('updatedAt', ""))
            published_at = str(record.get('publishedAt', ""))
            online_store_url = str(record.get('onlineStoreUrl', ""))
            online_store_preview_url = str(record.get('onlineStorePreviewUrl', ""))
            internal_links = str(record.get('internal_links', ""))
            
            # --- Insertion ---
            c.execute('''
                INSERT OR REPLACE INTO products_latest (
                    id, title, handle, description, descriptionHtml, product_type, vendor, status, tags, created_at, updated_at,
                    published_at, online_store_url, online_store_preview_url,
                    seo, metafields, images, variants, options, internal_links
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product_id,
                title,
                handle,
                description,
                description_html,
                product_type,
                vendor,
                status,
                tags_json,
                created_at,
                updated_at,
                published_at,
                online_store_url,
                online_store_preview_url,
                seo_json,
                metafields_json,
                images_json,
                variants_json,
                options_json,
                internal_links
            ))
        
        conn.commit()
        print("Product data inserted/updated successfully. ✅")

    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found. ❌")
    except sqlite3.Error as e:
        # This printout is still useful to identify the failing record's ID
        print(f"\n--- ERROR FOUND ---")
        print(f"Database error on record ID: {record.get('id')} ⚠️")
        print(f"Error: {e}")
        # If the error still occurs, the issue is environmental or a non-standard type in the JSON
        # that str() cannot fix (e.g., an attempt to insert a Python object not covered by json.dumps)
    except Exception as e:
        print(f"An unexpected error occurred: {e} 💥")
    finally:
        if conn:
            conn.close()

# insert_products_data('shopify_agent/data_of_shopify_products_complete.json', 'main_db_for_the_plants_mall.db')
