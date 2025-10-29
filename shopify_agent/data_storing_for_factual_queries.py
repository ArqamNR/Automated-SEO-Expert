import sqlite3
import json
def create_schema(db_path='search_console.db'):
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
            referringUrls TEXT
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

    conn.commit()
    conn.close()

    print("Database schema created successfully.")
# create_schema()


def insert_page_data(data, db_path='search_console.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    for page_data in data:
        json_string = json.dumps(page_data.get('referringUrls'))
        # Insert into pages table and get the page_id
        try:
            c.execute('''
                INSERT INTO pages (url, robots_txt_state, indexing_state, page_fetch_state, crawled_as, coverage_state, mobileUsabilityResult, indexstatusresult_verdict, referringUrls)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                page_data['url'],
                page_data.get('robotsTxtState'),
                page_data.get('indexingState'),
                page_data.get('pageFetchState'),
                page_data.get('crawledAs'),
                page_data.get('coverage_state'),
                page_data.get('mobileUsabilityResult'),
                page_data.get('indexstatusresult_verdict'),
                json_string
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
with open("shopify_agent/data_of_pages.json", "r") as file:
    data = json.load(file)
# insert_page_data(data)

def run_query(query, params=None):
    """
    Connects to the database, executes a query, and returns the results.
    """
    conn = sqlite3.connect('search_console_a.db')
    cursor = conn.cursor()
    
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
        
    results = cursor.fetchall()
    conn.close()
    return results

""" query = "SELECT url, robots_txt_state, indexing_state FROM pages LIMIT 15"
print("All Pages:")
print(run_query(query)) """

# page_url = "https://theplantsmall.com/products/fresh-peach-of-swat-valley"
# query = """
# SELECT T1.url, T2.clicks, T2.impressions, T2.ctr, T2.position 
# FROM pages AS T1
# JOIN performance_metrics AS T2 ON T1.id = T2.page_id
# WHERE T1.url = ?
# """
# print(f"\nPerformance Metrics for {page_url}:")
# print(run_query(query, (page_url,)))

# issue_type = "Product snippets"
query = """
SELECT title FROM products WHERE vendor != "The Plants Mall";
"""
# print(run_query(query))

import sqlite3
import json

def insert_query_data(file_name, db_path='search_console_a.db'):
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

query = """
CREATE TABLE product_gsc_metrics AS
WITH Aggregated_RRI AS (
    SELECT
        page_id,
        GROUP_CONCAT(
            rich_result_type || ' (' || severity || '): ' || issue_message, 
            ' | '
        ) AS rich_result_issues
    FROM
        rich_result_issues
    GROUP BY
        page_id
)
SELECT
    p.id AS product_id,
    p.title,
    p.body_html,
    p.vendor,
    p.product_type,
    p.created_at,
    p.handle,
    p.updated_at,
    p.published_at,
    p.template_suffix,
    p.tags,
    p.published_scope,
    p.status,
    p.admin_graphql_api_id,
    p.variants,
    p.options,
    p.images,
    p.product_url AS shopify_url,

    
    pg.id AS page_gsc_id,
    pg.url AS gsc_url,
    pg.robots_txt_state,
    pg.indexing_state,
    pg.page_fetch_state,
    pg.crawled_as,
    pg.coverage_state,
    pg.mobileUsabilityResult,
    pg.indexstatusresult_verdict,
    pg.userCanonical,
    pg.googleCanonical,
    pg.lastCrawlTime,
    pg.pagespeed_score, 

    
    cwv.lcp,
    cwv.cls,
    cwv.inp, 

    -- Aggregated RRI summary
    rri.rich_result_issues
    
FROM
    products p
INNER JOIN
    pages pg
    -- Use the robust, case-insensitive LIKE join on the product handle
    ON LOWER(pg.url) LIKE '%' || LOWER(p.handle) || '%'
LEFT JOIN
    core_web_vitals cwv
    ON pg.id = cwv.page_id
LEFT JOIN 
    Aggregated_RRI rri
    ON pg.id = rri.page_id;
"""
print(run_query(query))

file_to_insert = 'shopify_agent/data_of_pages_query.json'
# insert_query_data(file_to_insert)


import json
import sqlite3

def insert_daily_page_data(file_name, db_path='search_console.db'):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

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
                INSERT INTO daily_page_metrics (page_id, date, country, clicks, impressions, ctr, position)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                page_id,
                record.get('date'),
                record.get('country'),
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
# insert_daily_page_data('shopify_agent/data_of_pages_daily.json')

import json
import sqlite3

def insert_daily_query_data(file_name, db_path='search_console.db'):
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
# insert_daily_query_data('shopify_agent/data_of_queries_daily.json')

import json
import sqlite3

def insert_page_query_data(file_name, db_path='search_console.db'):
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

        # Step 1: Create the new 'page_query_performance' table
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
        
        # Load data from the JSON file
        with open(file_name, 'r') as f:
            data = json.load(f)

        # Iterate through the data and insert into the tables
        for record in data:
            url = record.get('url')
            query_text = record.get('query')
            
            # Step 2: Get the ID for the URL from the pages table
            c.execute("SELECT id FROM pages WHERE url = ?", (url,))
            page = c.fetchone()
            if not page:
                c.execute("INSERT INTO pages (url) VALUES (?)", (url,))
                page_id = c.lastrowid
            else:
                page_id = page[0]

            # Step 3: Get the ID for the query from the queries table
            c.execute("SELECT id FROM queries WHERE query = ?", (query_text,))
            query = c.fetchone()
            if not query:
                c.execute("INSERT INTO queries (query) VALUES (?)", (query_text,))
                query_id = c.lastrowid
            else:
                query_id = query[0]

            # Step 4: Insert the performance data into the page_query_performance table
            c.execute('''
                INSERT INTO page_query_performance (page_id, query_id, country, clicks, impressions, ctr, position)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                page_id,
                query_id,
                record.get('country'),
                record.get('clicks'),
                record.get('impressions'),
                record.get('ctr'),
                record.get('position')
            ))
        
        conn.commit()
        print("Page-query data inserted successfully.")

    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

# Example usage:
# insert_page_query_data('shopify_agent/data_of_pages_wrt_queries_daily.json')

import json
import sqlite3

def insert_daily_page_query_data(file_name, db_path='search_console.db'):
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
            url = record.get('page')
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
# insert_daily_page_query_data('shopify_agent/data_of_pages_wrt_queries_daily.json')

import json
import sqlite3

def insert_core_web_vitals(file_name, db_path='search_console.db'):
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
# insert_core_web_vitals('shopify_agent/data_of_pages.json')

import json
import sqlite3

def insert_products_data(file_name, db_path='search_console.db'):
    """
    Creates a 'products' table and inserts product information from a JSON file.
    Nested data (variants, options, images) is serialized to JSON strings.
    """
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()

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
        
        # Load data from the JSON file
        with open(file_name, 'r') as f:
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

    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

# Example usage:
# insert_products_data('shopify_agent/data_of_shopify_products_plants_mall.json')

import sqlite3
import json

def insert_pages_data_into_db(file_name, db_path='search_console.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # --- 1. DEFINE HELPER FOR SCHEMA MIGRATION ---
    def add_column_if_not_exists(cursor, table_name, column_name, data_type):
        try:
            # This attempts to add the column. 
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {data_type}")
            # print(f"Added {column_name} column.")
        except sqlite3.OperationalError as e:
            # If the column already exists, SQLite throws 'duplicate column name'. We ignore it.
            if 'duplicate column name' not in str(e):
                raise
            pass 

    # --- 2. ENSURE TABLE/COLUMNS EXIST ---
    # Create the table if it doesn't exist (with the NEW schema)
    # NOTE: If the table ALREADY exists, this line is SKIPPED, 
    # which is why the ALTER TABLE calls below are essential.
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
            userCanonical TEXT,     -- Included for new tables
            googleCanonical TEXT,   -- Included for new tables
            lastCrawlTime TEXT      -- Included for new tables
        )
    ''')
    
    # Run the ALTER TABLE commands to add the columns for existing tables
    add_column_if_not_exists(c, 'pages', 'userCanonical', 'TEXT')
    add_column_if_not_exists(c, 'pages', 'googleCanonical', 'TEXT')
    add_column_if_not_exists(c, 'pages', 'lastCrawlTime', 'TEXT')
    add_column_if_not_exists(c, 'pages', 'pagespeed_score', 'INTEGER')

    # Load data from the JSON file
    try:
        with open(file_name, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {file_name}")
        conn.close()
        return

    # --- 3. PROCESS AND INSERT DATA ---
    for page_data in data:
        # Handle 'referringUrls' - ensure it's not None before dumping
        referring_urls_data = page_data.get('referringUrls')
        json_string = json.dumps(referring_urls_data) if referring_urls_data is not None else None
        
        # DEBUG: Check the actual values from the JSON before insertion
        # If this prints None, your JSON keys are incorrect, causing the NULL in the DB.
        # print(f"URL: {page_data.get('url')} | userCanonical value from JSON: {page_data.get('userCanonical')}") 

        try:
            # INSERT statement (attempts to add a new row)
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
            # page_id is not strictly needed here but left for context
            page_id = c.lastrowid
            
        except sqlite3.IntegrityError:
            # If the URL already exists (IntegrityError due to UNIQUE constraint), UPDATE the existing row
            c.execute('''
                UPDATE pages 
                SET robots_txt_state=?, indexing_state=?, page_fetch_state=?, crawled_as=?, coverage_state=?, mobileUsabilityResult=?, indexstatusresult_verdict=?, referringUrls=?, userCanonical=?, googleCanonical=?, lastCrawlTime=?, pagespeed_score=?
                WHERE url = ?
            ''', (
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
                page_data.get('pagespeed_score'),
                page_data['url'], # WHERE clause value
                
            ))

    # --- 4. COMMIT AND CLOSE ---
    # Commit all changes after the loop finishes processing all data
    conn.commit()
    conn.close()
    print("Data insertion complete and database connection closed.")
# insert_pages_data_into_db("shopify_agent/data_of_pages.json")