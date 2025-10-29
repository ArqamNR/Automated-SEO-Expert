import json, requests
from langchain.agents import AgentExecutor, Tool, create_react_agent
from typing import List, Dict, Any
import os, re, ast
import django
from langchain_core.documents import Document
import sqlite3
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from google import genai
from dotenv import load_dotenv
load_dotenv()
from shopify_agent.prompts_for_chatbot import shopify_store_manager_prompt,product_agent_prompt,seo_agent_prompt,sql_query_agent_prompt,suggestions_agent_prompt,diagnosis_agent_prompt
api_key = os.getenv("GOOGLE_API_KEY")
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SHOPIFY_SHOP_NAME = os.environ.get('SHOPIFY_SHOP_NAME')
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')
# --- Memory Management Functions ---
def load_memory(file_path):
    """Loads chat history from a JSON file."""
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as f:
        content = f.read().strip()
        if not content:
            return []
        return json.loads(content)

def reset_memory(file_path):
    """Resets (deletes) the memory file."""
    if os.path.exists(file_path):
        os.remove(file_path)

def save_memory(memory_buffer, file_path):
    """Saves chat history to a JSON file."""
    try:
        with open(file_path, "w") as f:
            json.dump(memory_buffer, f)
    except Exception as e:
        print(f'Error occured while saving to memory: {e}')
def reconstruct_memory(memory_data):
    """Reconstructs ConversationBufferMemory from a list of dicts."""
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    messages = []
    for msg_dict in memory_data:
        if msg_dict.get('type') == 'human':
            messages.append(HumanMessage(content=msg_dict['content']))
        elif msg_dict.get('type') == 'ai':
            messages.append(AIMessage(content=msg_dict['content']))
    memory.chat_memory.messages = messages
    return memory

def serialize_messages(messages):
    """Serializes LangChain message objects to dicts for saving."""
    serialized = []
    for msg in messages:
        if hasattr(msg, "model_dump"):
            serialized.append(msg.model_dump())
        elif isinstance(msg, dict):
            serialized.append(msg)
        else:
            raise TypeError(f"Unsupported message type: {type(msg)}")
    return serialized
def serialize_task_body(msg):
    """Serializes LangChain message objects to dicts for saving."""
    serialized = []
    if hasattr(msg, "model_dump"):
        serialized.append(msg.model_dump())
    elif isinstance(msg, dict):
        serialized.append(msg)
    else:
        raise TypeError(f"Unsupported message type: {type(msg)}")
    return serialized

class ShopifyChat:
    def __init__(self):
        # self.gemini_api_key = "AIzaSyA0qysiuVnGXo940Md7M643MfGvOehExEA"
        self.get_all_products=None
        self.get_details_of_a_product=None
        self.total_products_tool=None
        self.product_agent=None
        self.seo_analyzer_tool=None
        self.vectorstore = None
        self.vectorstore_diagnosis=None
        self.is_initialized = False
        self.store_manager_total_tokens=0
        self.store_manager_input_tokens=0
        self.store_manager_output_tokens=0
        self.sql_query_tool=None
        self.query_tool=None
        self.diagnosis_agent=None
        self.general_questions_tool=None
        self.get_metrics_tool=None
        self.diagnosis_rag=None
        self.perform_health_checks_tool=None
        self.suggestions_agent=None
        self.suggestions_rag=None
        self.vectorstore_suggestions=None
        self.shop_name = SHOPIFY_SHOP_NAME
        self.admin_access_token = SHOPIFY_ACCESS_TOKEN
        self.memory_for_shopify_store_manager_agent = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.memory_for_product_agent=ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.memory_for_seo_agent=ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.memory_for_sql_query_agent=ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.memory_for_diagnosis_agent=ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.memory_for_suggestions_agent=ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    def initialize_general_questions_tool(self):
        """Initializes the General Questions tool."""
        self.general_questions_tool = Tool(
            name="general_rag",
            func=self.answer_general_questions,
            description="Useful for when you need to fetch details regarding a specific user query from the Knowledge Base. Try to get the relevant information by understanding the user query."
        )
    def answer_general_questions(self, query: str) -> str:
        """
        A General RAG tool to answer general questions user can ask related to the capabilities of the platform.
        """
        if self.vectorstore:
            try:
                retrieved_docs = self.vectorstore.similarity_search(query,k=7)
                if not retrieved_docs:
                    return "No relevant information found in the knowledge base."
                combined_content = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])
                return combined_content
            except Exception as e:
                return f"Error using RAG tool: {e}"
        else:
            return "General RAG system is not initialized. Cannot fetch information."
    def initialize_llm(self):
        """Initializes the LLM."""
        import os, re, pymupdf, asyncio
        if "GOOGLE_API_KEY" not in os.environ:
            os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", GEMINI_API_KEY)
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain.schema import Document
        """  from langchain_mistralai import ChatMistralAI
        mistral_model = "codestral-latest"
        api_key = ""
        self.llm = ChatMistralAI(model=mistral_model, temperature=0, api_key=api_key) """
        # Step 1: Initialize the LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.3,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            # google_api_key=self.gemini_api_key
        )  
        def extract_pdf_text(path):
            doc = pymupdf.open(path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text

        def extract_qa_pairs(text):
            # Regular expression to match Q: ... A: ...
            pattern = r"Q[:\-–]?\s*(.*?)\nA[:\-–]?\s*(.*?)(?=\nQ[:\-–]?|\Z)"
            matches = re.findall(pattern, text, re.DOTALL)

            docs = []
            for question, answer in matches:
                docs.append({
                    "question": question.strip(),
                    "answer": answer.strip()
                })
            return docs

        def process_pdfs_in_directory(pdf_dir):
            all_docs = []
            for filename in os.listdir(pdf_dir):
                if filename.lower().endswith(".pdf"):
                    pdf_path = os.path.join(pdf_dir, filename)
                    raw_text = extract_pdf_text(pdf_path)
                    clean_text = raw_text.replace("uestion:", "Question:")
                    docs = extract_qa_pairs(clean_text)
                    lc_docs = [
                        Document(
                            page_content=f"Q: {item['question']}\nA: {item['answer']}",
                            metadata={"question": item['question'], "source": filename}
                        )
                        for item in docs
                    ]
                    all_docs.extend(lc_docs)
            return all_docs

        # Step 3: Build docs from PDFs
        docs = process_pdfs_in_directory('shopify_agent/General Questions')
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        
        from langchain_huggingface import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        FAISS_INDEX_PATH = "shopify/shopify_agent/faiss_index_general_rag_shopify"
        if os.path.exists(FAISS_INDEX_PATH):
            print(f"Loading FAISS index from {FAISS_INDEX_PATH}...")
            self.vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        else:
            print("Creating new FAISS index...")
            if docs:
                self.vectorstore = FAISS.from_documents(documents=docs, embedding=embeddings)
                self.vectorstore.save_local(FAISS_INDEX_PATH)
                print(f"FAISS index saved to {FAISS_INDEX_PATH}")
            else:
                print("Cannot create FAISS index: no documentS available.")
                self.vectorstore = None      
        self.initialize_products_tool()   
        self.initialize_details_of_a_product_tool()
        self.initialize_total_products_tool()
        self.invoke_products_agent()
        self.invoke_seo_agent()
        self.initialize_seo_analyzer_tool()
        self.invoke_sql_query_agent()
        self.initialize_query_tool()
        self.initialize_general_questions_tool()
        self.invoke_diagnosis_agent()
        self.initialize_diagnosis_rag_tool()
        self.initialize_health_checks_tool()
        self.invoke_suggestions_agent()
        self.initialize_suggestions_rag_tool()
    def initialize_products_tool(self):
        """Initializes the Products tool."""
        self.get_all_products = Tool(
            name="get_all_products",
            func=self.get_shopify_products,
            description="Useful for when you need to fetch details regarding a specific user query from the Knowledge Base. Try to get the relevant information by understanding the user query."
        )
    def get_shopify_products(self, query: str) -> str:
        """
        A tool to fetch details about the shopify products.
        """
        import requests

        url = f"https://{self.shop_name}.myshopify.com/admin/api/2025-01/products.json"

        headers = {
            "X-Shopify-Access-Token": self.admin_access_token,
            "Content-Type": "application/json"
        }
        product_names=[]
        response = requests.get(url, headers=headers)
        details_of_all_products = []
        if response.status_code == 200:
            products = response.json().get("products", [])
            for product in products:
                import re
                html_content = product['body_html']
                clean_text = re.sub(r'<[^>]*>', '', html_content)
                product['body_html'] = clean_text.strip()
                details_of_all_products.append(product)
                product_names.append(product.get('title'))
                print(f"{product['id']} - {product['title']} - {product.get('vendor')} - {product.get('image').get('src')}")
            with open("shopify/shopify_agent/data_of_shopify_products.json", "w") as file:
                json.dump(details_of_all_products, file, indent=4)
            return product_names
        else:
            print("Error:", response.status_code, response.text)
    def initialize_details_of_a_product_tool(self):
        """Initializes the Products tool."""
        self.get_details_of_a_product = Tool(
            name="get_details_of_a_product",
            func=self.get_product_details,
            description="Useful for when you need to fetch details regarding a specific user query from the Knowledge Base. Try to get the relevant information by understanding the user query."
        )
    def get_product_details(self, query: str) -> str:
        """
        A tool to fetch details about the shopify product.
        """
        query = query.replace("```","").replace("\n","")
        with open("shopify/shopify_agent/data_of_shopify_products.json", "r") as file:
            data = json.load(file)
        for prod in data:
            if prod.get('title') == query:
                return prod
            else:
                
                
                import requests

                url = f"https://{self.shop_name}.myshopify.com/admin/api/2025-01/products.json"

                headers = {
                    "X-Shopify-Access-Token": self.admin_access_token,
                    "Content-Type": "application/json"
                }

                response = requests.get(url, headers=headers)

                if response.status_code == 200:
                    products = response.json().get("products", [])
                    for product in products:
                        if product.get('title') == query:
                            print(f"Getting Details of the Product: {query}")
                            print(f"{product['id']} - {product['title']} - {product.get('vendor')} - {product.get('image').get('src')}")

                        return product
                else:
                    print("Error:", response.status_code, response.text)
    def initialize_total_products_tool(self):
        """Initializes the Total Products tool."""
        self.total_products_tool = Tool(
            name="get_total_products",
            func=self.get_total_products,
            description="Useful for when you need to get the total number of products from the shopify store."
        )
    def get_total_products(self, query: str) -> str:
        """
        A tool to fetch total number of shopify products available on the store.
        """
        query = query.replace("```","").replace("\n","")
        
        # api_version = '2023-10'
        import requests

        url = f"https://{self.shop_name}.myshopify.com/admin/api/2025-01/products.json"

        headers = {
            "X-Shopify-Access-Token": self.admin_access_token,
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers)
        product_names = []
        if response.status_code == 200:
            products = response.json().get("products", [])
            for product in products:
                product_names.append(product.get('title'))
            return len(products), product_names
        else:
            print("Error:", response.status_code, response.text)
    def initialize_seo_analyzer_tool(self):
        """Initializes the SEO Analyzer tool."""
        self.seo_analyzer_tool = Tool(
            name="seo_analyzer",
            func=self.seo_analyzer,
            description="Useful for when you need to analyze a shopify product and provide an SEO score for that specific product."
        )
    def seo_analyzer(self, query: str) -> str:
        """
        A tool to fetch total number of shopify products available on the store.
        """
        query = query.replace("```","").replace("\n","")
        print(f"Query for Analyzer: {query}")
        with open("shopify/shopify_agent/data_of_shopify_products.json", "r") as file:
            data = json.load(file)
        for p in data:
            if p.get('seo_score') and p.get('title') == query:
                print("Product already been optimized.")
                print(f"SEO Score: {p.get('seo_score')}")
                return p.get('seo_score')
            else:
                print("SEO score not assigned. Analyzing the Product Information...")
                import re
                html_content = p['body_html']
                clean_text = re.sub(r'<[^>]*>', '', html_content)
                p['body_html'] = clean_text.strip()
                product_info = p
                from google.genai import types
                config = types.GenerateContentConfig(
                temperature=0.5, 
                )

                client = genai.Client()
                response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    config=config,
                    contents=f"""You are an intelligent SEO expert that has years of experience of doing SEO of Shopify Products.
                    Here is a Shopify Product's information : {product_info}. You need to analyze this product professionaly and you need to provide 
                    an SEO score for this product. Just provide an SEO score out of 100 as your Final Answer, nothing else.
                """
                )
                json_output = response.text
                json_output = json_output.replace("```","").replace("\n","")
                print(f"Seo score: {json_output} and its type: {type(json_output)}")                    
                p['seo_score'] = json_output
                with open("shopify/shopify_agent/data_of_shopify_products.json", "r") as file:
                    data = json.load(file)
                for p in data:
                    if p.get("id") == p.get("id"):  
                        p["seo_score"] = json_output
                        break
                with open("shopify/shopify_agent/data_of_shopify_products.json", "w") as file:
                    json.dump(data, file, indent=4)
                return json_output
        else:
            print("Error:", response.status_code, response.text)
    def initialize_query_tool(self):
        """Initializes the SQL Query tool."""
        self.query_tool = Tool(
            name="query_tool",
            func=self.query_tool_func,
            description="""A tool for executing SQL queries on a relational database. Use this tool to retrieve factual data from the tables.
        schema_description:
        - Table: pages
            Columns: id (INTEGER), url (TEXT), robots_txt_state (TEXT), indexing_state (TEXT), page_fetch_state (TEXT), crawled_as (TEXT), userCanonical (TEXT), googleCanonical (TEXT), lastCrawlTime (TEXT)
        - Table: daily_page_metrics
            Columns: id (INTEGER), page_id (INTEGER), date (TEXT), country (TEXT), clicks (INTEGER), impressions (INTEGER), ctr (REAL), position (REAL)
        - Table: queries
            Columns: id (INTEGER), query (TEXT)
        - Table: core_web_vitals
            Columns: id (INTEGER), page_id (TEXT), lcp (TEXT), cls (TEXT), inp (TEXT)
        - Table: daily_query_metrics
            Columns: id (INTEGER), query_id (INTEGER), date (TEXT), country (TEXT), clicks (INTEGER), impressions (INTEGER), ctr (REAL), position (REAL)
        - Table: daily_page_query_metrics
            Columns: id (INTEGER), page_id (INTEGER), query_id (INTEGER), date (TEXT), country (TEXT), clicks (INTEGER), impressions (INTEGER), ctr (REAL), position (REAL)
        - Table: products
            Columns: id (INTEGER), title (TEXT), body_html (TEXT), vendor (TEXT), product_type (TEXT), created_at (TEXT), handle (TEXT), updated_at (TEXT), published_at (TEXT), template_suffix (TEXT), tags (TEXT), published_scope (TEXT), status (TEXT), admin_graphql_api_id (TEXT), variants (TEXT), options (TEXT), images (TEXT), product_url (TEXT)
        - Table: performance_metrics
            Columns: id (INTEGER), page_id (INTEGER), clicks (INTEGER), impressions (INTEGER), ctr (REAL), position (REAL)
        - Table: rich_result_issues
            Columns: id (INTEGER), page_id (INTEGER), rich_result_type (TEXT), issue_message (TEXT), severity (TEXT)
        - Table: query_performance
            Columns: id (INTEGER), query (TEXT), clicks (INTEGER), impressions (INTEGER), ctr (REAL), position (REAL)"""
        )
    def query_tool_func(self, query: str) -> str:
        
        db_path = r'C:\Follow4follow_agent\search_console_a.db'
        conn = None
        try:
            query = query.replace("```sql","").replace("\n","").replace("```","")
            keywords = [
                'SELECT', 'FROM', 'JOIN', 'ON', 'WHERE', 'ORDER BY', 'GROUP BY',
                'LIMIT', 'DESC', 'ASC'
            ]
            pattern = r'([a-zA-Z0-9])(JOIN|FROM|WHERE|ORDER BY|GROUP BY|LIMIT|DESC|ASC)'
            corrected_query = re.sub(pattern, r'\1 \2', query, flags=re.IGNORECASE)
            corrected_query = re.sub(r'\s+', ' ', corrected_query).strip()
            query = corrected_query
            print(f"Query: {query}")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            print(f"Results: {results}")
            if results:
                # Get column names from the cursor description
                column_names = [description[0] for description in cursor.description]
                # Format the results into a readable string
                formatted_results = [dict(zip(column_names, row)) for row in results]
                return f"Query executed successfully. Results: {formatted_results}"
            else:
                return "Query executed successfully, but no results were found."

        except sqlite3.Error as e:
            return f"Database error: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"
        finally:
            if conn:
                conn.close()

    def create_products_agent(self):
        """
        Creates and initializes the Shopify Products Agent.
        This agent orchestrates the user query handling and efficient tool calling with respect to the user query.
        """
        product_agent_tools = [self.get_all_products,self.get_details_of_a_product, self.total_products_tool]
        
        product_agent_runnable = create_react_agent(self.llm, product_agent_tools, product_agent_prompt)
        self.product_agent_executor = AgentExecutor(
            agent=product_agent_runnable,
            tools=product_agent_tools,
            return_intermediate_steps=True,
            verbose=True,
            handle_parsing_errors=True,
            memory=self.memory_for_product_agent
        )
    def invoke_products_agent(self):
        """Initializes the reporting CRUD agent.""" 
        self.product_agent = Tool(
            name="Product_Agent",
            func=self.product_agent_func,
            description="Understands the user query related to reporting and call respective tool from available tools accordingly."
        )
    def product_agent_func(self, query: str) -> str:
        """
        An agent to handle all the queries related to Reporting (CRUD operations for Reporting).
        """
        print(f"\n---Store Manager calling Product Agent with query: {query}---")
    
            # Invoke the agent with a query that requires a tool call
        response = self.product_agent_executor.invoke({"input": query})
        
        save_memory(serialize_messages(self.product_agent_executor.memory.chat_memory.messages),'product_agent_memory.json')
        return response['output']
    def create_sql_query_agent(self):
        """
        Creates and initializes the SQL Query Agent.
        This agent orchestrates the user query handling and efficient tool calling with respect to the user query.
        """
        sql_query_agent_tools = [self.query_tool]
        
        sql_query_agent_runnable = create_react_agent(self.llm, sql_query_agent_tools, sql_query_agent_prompt)
        self.sql_query_agent_executor = AgentExecutor(
            agent=sql_query_agent_runnable,
            tools=sql_query_agent_tools,
            return_intermediate_steps=True,
            verbose=True,
            handle_parsing_errors=True,
            memory=self.memory_for_sql_query_agent
        )
    def invoke_sql_query_agent(self):
        """Initializes the sql_query_agent.""" 
        self.sql_query_tool = Tool(
            name="SQL_Agent",
            func=self.sql_query_agent_func,
            description="Understands the user query related to pages and queries and call respective tool from available tools accordingly."
        )
    def sql_query_agent_func(self, query: str) -> str:
        """
        An agent to handle all the queries related to sql_query_agent.
        """
        print(f"\n---Store Manager calling SQL Agent with query: {query}---")
    
            # Invoke the agent with a query that requires a tool call
        response = self.sql_query_agent_executor.invoke({"input": query})
        
        save_memory(serialize_messages(self.sql_query_agent_executor.memory.chat_memory.messages),'sql_query_agent_memory.json')
        return response['output']
    def create_seo_agent(self):
        """
        Creates and initializes the SEO Agent for Shopify Store.
        This agent orchestrates the user query handling and efficient tool calling with respect to the user query.
        """
        seo_agent_tools = [self.seo_analyzer_tool]
        
        seo_agent_runnable = create_react_agent(self.llm, seo_agent_tools, seo_agent_prompt)
        self.seo_agent_executor = AgentExecutor(
            agent=seo_agent_runnable,
            tools=seo_agent_tools,
            return_intermediate_steps=True,
            verbose=True,
            handle_parsing_errors=True,
            memory=self.memory_for_seo_agent
        )
    def invoke_seo_agent(self):
        """Initializes the SEO agent.""" 
        self.seo_agent = Tool(
            name="SEO_Agent",
            func=self.seo_agent_func,
            description="Understands the user query related to SEO of products and call respective tool from available tools accordingly."
        )
    def seo_agent_func(self, query: str) -> str:
        """
        An agent to handle all the queries related to SEO of Shopify Products.
        """
        print(f"\n---Manager calling SEO Agent with query: {query}---")
    
            # Invoke the agent with a query that requires a tool call
        response = self.seo_agent_executor.invoke({"input": query})
        
        save_memory(serialize_messages(self.seo_agent_executor.memory.chat_memory.messages),'seo_agent_memory.json')
        return response['output']
    def initialize_rag_for_Diagnosis(self):
        import os, re, pymupdf, asyncio
        if "GOOGLE_API_KEY" not in os.environ:
            os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "AIzaSyDh16PZK4HGXRLchCH1_ZHuRW99tO7vKyE")
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain.schema import Document
        def extract_pdf_text(path):
            doc = pymupdf.open(path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text

        def extract_health_checks(text):
            """
            Extracts health check blocks in the format:
            Health Check: NAME
            Issues to look for: ...
            Impact: ...
            """
            # Regex matches one block starting with Health Check
            pattern = r"(Health Check[:\-–]?\s*.*?(?=Health Check[:\-–]?|\Z))"
            matches = re.findall(pattern, text, re.DOTALL)

            docs = []
            for match in matches:
                docs.append({
                    "content": match.strip()
                })
            
            return docs

        def process_pdfs_in_directory(pdf_dir):
            all_docs = []
            for filename in os.listdir(pdf_dir):
                if filename.lower().endswith(".pdf"):
                    pdf_path = os.path.join(pdf_dir, filename)
                    raw_text = extract_pdf_text(pdf_path)
                    blocks = extract_health_checks(raw_text)

                    lc_docs = [
                        Document(
                            page_content=item['content'],
                            metadata={"source": filename}
                        )
                        for item in blocks
                    ]
                    
                    all_docs.extend(lc_docs)
            return all_docs

        # Example usage
        docs = process_pdfs_in_directory('Health Checks')
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        
        from langchain_huggingface import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        FAISS_INDEX_PATH = "shopify/shopify_agent/faiss_index_diagnosis_rag"
        if os.path.exists(FAISS_INDEX_PATH):
            print(f"Loading FAISS index from {FAISS_INDEX_PATH}...")
            self.vectorstore_diagnosis = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        else:
            print("Creating new FAISS index...")
            if docs: 
                self.vectorstore_diagnosis = FAISS.from_documents(documents=docs, embedding=embeddings)
                self.vectorstore_diagnosis.save_local(FAISS_INDEX_PATH)
                # self.vectorstore_diagnosis = self.vectorstore_diagnosis.as_retriever()
                print(f"FAISS index saved to {FAISS_INDEX_PATH}")
            else: 
                print("Cannot create FAISS index: no documentS available.")
                self.vectorstore_diagnosis = None
    def initialize_diagnosis_rag_tool(self):
        """Initializes the RAG tool for diagnosis."""
        self.diagnosis_rag = Tool(
            name="Diagnosis_RAG",
            func=self.rag_func_for_diagnosis,
            description="Useful for when you need to fetch details regarding a specific issue in the Product or page Performance."
        )
    def rag_func_for_diagnosis(self, query):
        try:
            retrieved_docs = self.vectorstore_diagnosis.similarity_search(query,k=11)
            # retrieved_docs = self.vectorstore_diagnosis.invoke(query)
            if not retrieved_docs:
                return "No relevant information found in the knowledge base."
            combined_content = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])
            return combined_content
        except Exception as e:
            return f"Error using RAG tool: {e}"
    def initialize_rag_for_Suggestions(self):
        import os, re, pymupdf, asyncio
        if "GOOGLE_API_KEY" not in os.environ:
            os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "AIzaSyDh16PZK4HGXRLchCH1_ZHuRW99tO7vKyE")
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain.schema import Document
        def extract_pdf_text(path):
            doc = pymupdf.open(path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text

        def extract_suggestions(text):
            """
            Extracts Suggestion blocks in the format:
            Suggestion: Suggestion title
            Solution: ...
            """
            # Regex matches one block starting with Health Check
            pattern = r"(Suggestion[:\-–]?\s*.*?(?=Suggestion[:\-–]?|\Z))"
            matches = re.findall(pattern, text, re.DOTALL)

            docs = []
            for match in matches:
                docs.append({
                    "content": match.strip()
                })
            
            return docs

        def process_pdfs_in_directory(pdf_dir):
            all_docs = []
            for filename in os.listdir(pdf_dir):
                if filename.lower().endswith(".pdf"):
                    pdf_path = os.path.join(pdf_dir, filename)
                    raw_text = extract_pdf_text(pdf_path)
                    blocks = extract_suggestions(raw_text)

                    lc_docs = [
                        Document(
                            page_content=item['content'],
                            metadata={"source": filename}
                        )
                        for item in blocks
                    ]
                    
                    all_docs.extend(lc_docs)
            return all_docs

        # Example usage
        docs = process_pdfs_in_directory('Suggestions')
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        
        from langchain_huggingface import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        FAISS_INDEX_PATH = "shopify/shopify_agent/faiss_index_suggestions_rag"
        if os.path.exists(FAISS_INDEX_PATH):
            print(f"Loading FAISS index from {FAISS_INDEX_PATH}...")
            self.vectorstore_suggestions = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        else:
            print("Creating new FAISS index...")
            if docs: 
                self.vectorstore_suggestions = FAISS.from_documents(documents=docs, embedding=embeddings)
                self.vectorstore_suggestions.save_local(FAISS_INDEX_PATH)
                # self.vectorstore_diagnosis = self.vectorstore_diagnosis.as_retriever()
                print(f"FAISS index saved to {FAISS_INDEX_PATH}")
            else: 
                print("Cannot create FAISS index: no documentS available.")
                self.vectorstore_suggestions = None
    def initialize_suggestions_rag_tool(self):
        """Initializes the RAG tool for Suggestions."""
        self.suggestions_rag = Tool(
            name="Suggestions_RAG",
            func=self.rag_func_for_suggestions,
            description="Useful for when you need to resolve a specific issue or improve a particular product or give suggestions for a particular product."
        )
    def rag_func_for_suggestions(self, query):
        try:
            # retrieved_docs = self.vectorstore_suggestions.similarity_search(query,k=3)
            retrieved_docs = self.vectorstore_suggestions.max_marginal_relevance_search(
        query,
        k=2,         
        fetch_k=20,  
        lambda_mult=0.95 
    )
            
            if not retrieved_docs:
                return "No relevant information found in the knowledge for Suggestions."
            combined_content = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])
            return combined_content
        except Exception as e:
            return f"Error using RAG tool: {e}"
    def initialize_health_checks_tool(self):
        """Initializes the SQL Query tool."""
        self.perform_health_checks_tool = Tool(
            name="health_checks",
            func=self.checks_tool,
            description="""A tool for executing SQL queries on a relational database. Use this tool to retrieve factual data from the tables.
        schema_description:
        - Table: pages
            Columns: id (INTEGER), url (TEXT), robots_txt_state (TEXT), indexing_state (TEXT), page_fetch_state (TEXT), crawled_as (TEXT), userCanonical (TEXT), googleCanonical (TEXT), lastCrawlTime (TEXT), pagespeed_score (INTEGER)
        - Table: daily_page_metrics
            Columns: id (INTEGER), page_id (INTEGER), date (TEXT), country (TEXT), clicks (INTEGER), impressions (INTEGER), ctr (REAL), position (REAL)
        - Table: queries
            Columns: id (INTEGER), query (TEXT)
        - Table: core_web_vitals
            Columns: id (INTEGER), page_id (TEXT), lcp (TEXT), cls (TEXT), inp (TEXT)
        - Table: daily_query_metrics
            Columns: id (INTEGER), query_id (INTEGER), date (TEXT), country (TEXT), clicks (INTEGER), impressions (INTEGER), ctr (REAL), position (REAL)
        - Table: daily_page_query_metrics
            Columns: id (INTEGER), page_id (INTEGER), query_id (INTEGER), date (TEXT), country (TEXT), clicks (INTEGER), impressions (INTEGER), ctr (REAL), position (REAL)
        - Table: products
            Columns: id (INTEGER), title (TEXT), body_html (TEXT), vendor (TEXT), product_type (TEXT), created_at (TEXT), handle (TEXT), updated_at (TEXT), published_at (TEXT), template_suffix (TEXT), tags (TEXT), published_scope (TEXT), status (TEXT), admin_graphql_api_id (TEXT), variants (TEXT), options (TEXT), images (TEXT), product_url (TEXT)
        - Table: performance_metrics
            Columns: id (INTEGER), page_id (INTEGER), clicks (INTEGER), impressions (INTEGER), ctr (REAL), position (REAL)
        - Table: rich_result_issues
            Columns: id (INTEGER), page_id (INTEGER), rich_result_type (TEXT), issue_message (TEXT), severity (TEXT)
        - Table: query_performance
            Columns: id (INTEGER), query (TEXT), clicks (INTEGER), impressions (INTEGER), ctr (REAL), position (REAL)"""
        )
    def checks_tool(self, query: str) -> str:
        
        db_path = r'C:\Follow4follow_agent\search_console_test.db'
        conn = None
        try:
            query = query.replace("```sql","").replace("\n","").replace("```","")
            keywords = [
                'SELECT', 'FROM', 'JOIN', 'ON', 'WHERE', 'ORDER BY', 'GROUP BY',
                'LIMIT', 'DESC', 'ASC'
            ]
            pattern = r'([a-zA-Z0-9])(JOIN|FROM|WHERE|ORDER BY|GROUP BY|LIMIT|DESC|ASC)'
            corrected_query = re.sub(pattern, r'\1 \2', query, flags=re.IGNORECASE)
            corrected_query = re.sub(r'\s+', ' ', corrected_query).strip()
            query = corrected_query
            print(f"Query: {query}")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            print(f"Results: {results}")
            if results:
                # Get column names from the cursor description
                column_names = [description[0] for description in cursor.description]
                # Format the results into a readable string
                formatted_results = [dict(zip(column_names, row)) for row in results]
                return f"Query executed successfully. Results: {formatted_results}"
            else:
                return "Query executed successfully, but no results were found."

        except sqlite3.Error as e:
            return f"Database error: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"
        finally:
            if conn:
                conn.close() 
    def create_diagnosis_agent(self):
        """
        Creates and initializes the Diagnosis Agent for Shopify Products and Google Search Console performance metrics.
        This agent orchestrates the user query handling and efficient tool calling with respect to the user query.
        """
        diagnosis_agent_tools = [self.perform_health_checks_tool, self.diagnosis_rag]
        
        diagnosis_agent_runnable = create_react_agent(self.llm, diagnosis_agent_tools, diagnosis_agent_prompt)
        self.diagnosis_agent_executor = AgentExecutor(
            agent=diagnosis_agent_runnable,
            tools=diagnosis_agent_tools,
            return_intermediate_steps=True,
            verbose=True,
            handle_parsing_errors=True,
            memory=self.memory_for_diagnosis_agent
        )
    def invoke_diagnosis_agent(self):
        """Initializes the Diagnosis agent.""" 
        self.diagnosis_agent = Tool(
            name="Diagnosis_Agent",
            func=self.diagnosis_agent_func,
            description="Understands the user query related to issues for shopify store products and website and call respective tool from available tools accordingly."
        )
    def diagnosis_agent_func(self, query: str) -> str:
        """
        An agent to diagnose the issues related to SEO of Shopify Products.
        """
        print(f"\n---Manager calling Diagnosis Agent with query: {query}---")
    
            # Invoke the agent with a query that requires a tool call
        response = self.diagnosis_agent_executor.invoke({"input": query})
        
        save_memory(serialize_messages(self.diagnosis_agent_executor.memory.chat_memory.messages),'diagnosis_agent_memory.json')
        return response['output']
    def create_suggestions_agent(self):
        """
        Creates and initializes the Suggestions Agent for Shopify Products and Google Search Console performance metrics.
        This agent orchestrates the user query handling and efficient tool calling with respect to the user query.
        """
        suggestions_agent_tools = [self.suggestions_rag]
        
        suggestions_agent_runnable = create_react_agent(self.llm, suggestions_agent_tools, suggestions_agent_prompt)
        self.suggestions_agent_executor = AgentExecutor(
            agent=suggestions_agent_runnable,
            tools=suggestions_agent_tools,
            return_intermediate_steps=True,
            verbose=True,
            handle_parsing_errors=True,
            memory=self.memory_for_suggestions_agent
        )
    def invoke_suggestions_agent(self):
        """Initializes the Suggestions agent.""" 
        self.suggestions_agent = Tool(
            name="Suggestions_Agent",
            func=self.suggestions_agent_func,
            description="Understands the user query related to improving products, providing suggestions, resolving issues for shopify store products and website and call respective tool from available tools accordingly."
        )
    def suggestions_agent_func(self, query: str) -> str:
        """
        An agent to improve the products, resolve the issues related to SEO of Shopify Products and providing suggestions for the Products and Store as well.
        """
        print(f"\n---Manager calling Suggestions Agent with query: {query}---")
    
            # Invoke the agent with a query that requires a tool call
        response = self.suggestions_agent_executor.invoke({"input": query})
        
        save_memory(serialize_messages(self.suggestions_agent_executor.memory.chat_memory.messages),'suggestions_agent_memory.json')
        return response['output']
    def create_shopify_store_manager_agent(self):
        """
        Creates and initializes the Shopify Store Manager Agent.
        This agent orchestrates the user query handling and efficient tool calling with respect to the user query.
        """
        shopify_store_manager_base_tools = [self.product_agent, self.seo_agent,self.sql_query_tool,self.general_questions_tool,self.diagnosis_agent, self.suggestions_agent]
        
        shopify_store_manager_agent_runnable = create_react_agent(self.llm, shopify_store_manager_base_tools, shopify_store_manager_prompt)
        self.shopify_store_manager_agent_executor = AgentExecutor(
            agent=shopify_store_manager_agent_runnable,
            tools=shopify_store_manager_base_tools,
            return_intermediate_steps=True,
            verbose=True,
            handle_parsing_errors=True,
            memory=self.memory_for_shopify_store_manager_agent
        )
    def initialize(self):
        """Initializes all components: LLM and  all agents."""
        
        self.initialize_llm()
        self.initialize_rag_for_Diagnosis()
        self.initialize_rag_for_Suggestions()
        if not self.llm or not self.get_all_products:
            print("Initialization failed: LLM or a tool not set up.")
            return False
        
        self.create_shopify_store_manager_agent()
        self.create_products_agent()
        self.create_seo_agent()
        self.create_sql_query_agent()
        self.create_diagnosis_agent()
        self.create_suggestions_agent()
        self.is_initialized = True
        return True

    def chat_with_agent(self, user_input: str) -> Dict[str, Any]:
        """
        Takes the user query and forwards it to respective tool as it is.
        """
        print(f"-----Query for Shopify Store Manager Agent: {user_input}-----")
        from langchain.callbacks import get_openai_callback
        with get_openai_callback() as cb:
            
            response = self.shopify_store_manager_agent_executor.invoke({"input": user_input})
            self.store_manager_total_tokens = cb.total_tokens
            self.store_manager_input_tokens = cb.prompt_tokens
            self.store_manager_output_tokens = cb.completion_tokens
            
            print("\n--- Callback Token Usage for Shopify Store Manager Agent---")
            print(f"Total Tokens: {cb.total_tokens}")
            print(f"Prompt Tokens: {cb.prompt_tokens}")
            print(f"Completion Tokens: {cb.completion_tokens}")
            print(f"Total Cost (USD): ${cb.total_cost}")
    
        
        save_memory(serialize_messages(self.shopify_store_manager_agent_executor.memory.chat_memory.messages), 'shopify_store_manager_memory.json')
        response = response['output']
        response = response.replace("```markdown","").replace("```","")
        return response
    


