import json, requests
from langchain.agents import AgentExecutor, Tool, create_react_agent
from typing import List, Dict, Any
import os, re, ast
import django
import sqlite3
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from shopify_manager.models import Product, Page_Query_Metrics
import sqlite3
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import HumanMessage, AIMessage
from google import genai
from dotenv import load_dotenv
load_dotenv()
SHOPIFY_SHOP_NAME = os.environ.get('SHOPIFY_SHOP_NAME')
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
from shopify_agent.prompts import shopify_store_manager_prompt,seo_agent_prompt,suggestions_agent_prompt
api_key = os.getenv("GOOGLE_API_KEY")
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

class ShopifyStoreManager:
    def __init__(self):
        
        self.get_all_products=None
        self.get_details_of_a_product=None
        self.total_products_tool=None
        self.product_agent=None
        self.seo_analyzer_tool=None
        self.vectorstore = None
        self.vectorstore_diagnosis=None
        self.seo_metrics_checker=None
        self.is_initialized = False
        self.store_manager_total_tokens=0
        self.store_manager_input_tokens=0
        self.store_manager_output_tokens=0
        self.sql_query_tool=None
        self.query_tool=None
        self.rag_chain=None
        self.suggestions_tool=None
        self.diagnosis_agent=None
        self.general_questions_tool=None
        self.get_metrics_tool=None
        self.diagnosis_rag=None
        self.perform_health_checks_tool=None
        self.suggestions_agent=None
        self.seo_tool=None
        self.suggestions_rag=None
        self.product_analysis_tool=None
        self.website_issues_solver_tool=None
        self.writer_tool=None
        self.vectorstore_suggestions=None
        self.shop_name = SHOPIFY_SHOP_NAME
        self.admin_access_token = SHOPIFY_ACCESS_TOKEN
        self.memory_for_shopify_store_manager_agent = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.memory_for_product_agent=ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.memory_for_seo_agent=ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.memory_for_sql_query_agent=ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.memory_for_diagnosis_agent=ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.memory_for_suggestions_agent=ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
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
        self.initialize_products_tool()   
        self.initialize_details_of_a_product_tool()
        self.initialize_total_products_tool()
        self.invoke_seo_agent()
        self.invoke_suggestions_agent()
        self.initialize_seo_tool()
        self.initialize_suggestions_tool()
        # self.initialize_seo_analyzer_tool()
        
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
    
    def create_suggestions_agent(self):
        """
        Creates and initializes the Suggestions Agent for Shopify Store.
        This agent orchestrates the user query handling and efficient tool calling with respect to the user query.
        """
        suggestions_agent_tools = []
        
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
        """Initializes the suggestions agent.""" 
        self.suggestions_agent = Tool(
            name="Suggestions_Agent",
            func=self.suggestions_agent_func,
            description="Understands the user query related to Suggestions of issues for the products and call respective tool from available tools accordingly."
        )
    def suggestions_agent_func(self, query: str) -> str:
        """
        An agent to handle all the queries related to providing Suggestions for the issues arrived in SEO Analysis.
        """
        print(f"\n---Manager calling Suggestions Agent with query: {query}---")
    
            # Invoke the agent with a query that requires a tool call
        response = self.suggestions_agent_executor.invoke({"input": query})
        
        save_memory(serialize_messages(self.suggestions_agent_executor.memory.chat_memory.messages),'suggestions_agent_memory.json')
        return response['output']
    def initialize_suggestions_tool(self):
        self.suggestions_tool = Tool(
            name="Suggestions_Tool",
            func=self.suggestions_tool_func,
            description="Suggests the solutions for the issues in the Product information."
        )
    def suggestions_tool_func(self, query):
        import ast
        query = query.replace("\n", "")
        query = ast.literal_eval(query)
        id_ = query[0]
        store_name = query[1]

        # 🧠 Get product using ORM
        product = Product.objects.filter(id=id_, store_name=store_name).first()

        if not product:
            print("Product not found")
        else:
            issues_in_product = product.seo_issues
            seo_score = product.seo_score
            id = product.id

            # If `seo_issues` is stored as a JSON string, parse it
            if isinstance(issues_in_product, str):
                issues = ast.literal_eval(issues_in_product)
            else:
                issues = issues_in_product or []

            print(issues, type(issues))
            merged = {k: v for d in issues for k, v in d.items()}
            print(merged, type(merged))
        
        if merged.get("meta_title_set") == 0 and merged.get('meta_title_length') == 0:
            client = genai.Client()
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"""
            You are an intelligent and smart agent that is experienced in writing impressive, unique and ranking Meta title for a shopify product. 
            Here is the Product Title of a Shopify Product {product.title} for which you need to provide a single meta title whose number of characters should be strictly between 30 and 60.
            The shop name is The Plants Mall and the shop is associated with growing and selling Cassava, alongside a rich diversity of superfoods, herbs, and medicinal plants like Quinoa, Sesame, Mustard, Barley, Wheat, Aloe Vera, Moringa, Beetroot, Desi Garlic, Basil/Tulsi, Niazbo (Ocimum Basilicum), Aqar Qarha (Anacyclus Pyrethrum) and Ashwagandha (Withania Somnifera), and much more
            Do not provide any options. Just return a single and final Meta title. No need to include bullets or headings or anything else.
        """
        )
            print(response.text, len(response.text))
            meta_title = response.text
            seo_score += 20

            if product:
                seo_data = json.loads(product.seo) or {}  
                seo_data['title'] = meta_title

                # Update issue values
                for issue_dict in issues:
                    if 'meta_title_set' in issue_dict:
                        issue_dict['meta_title_set'] = 10
                    if 'meta_title_length' in issue_dict:
                        issue_dict['meta_title_length'] = 10

                # Assign updated values directly
                product.seo = json.dumps(seo_data)
                product.seo_issues = issues
                product.seo_score = seo_score

                # Save changes to DB
                product.save()
            print("Meta title check passed")
        if merged.get("meta_description_set") == 0 and merged.get('meta_description_length') == 0:
            client = genai.Client()
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"""
            You are an intelligent and smart agent that is experienced in writing impressive, unique and ranking Meta description for a shopify product. 
            Here is the Product Title of a Shopify Product {product.title} for which you need to provide a single meta description. The number of characters for the meta descriptions should always be strictly between 120 and 158 characters.
            The shop name is The Plants Mall and the shop is associated with growing and selling Cassava, alongside a rich diversity of superfoods, herbs, and medicinal plants like Quinoa, Sesame, Mustard, Barley, Wheat, Aloe Vera, Moringa, Beetroot, Desi Garlic, Basil/Tulsi, Niazbo (Ocimum Basilicum), Aqar Qarha (Anacyclus Pyrethrum) and Ashwagandha (Withania Somnifera), and much more
            Do not provide any options. Just return a single and final Meta description. No need to include bullets or headings or anything else.
        """
        )
            print(response.text, len(response.text))
            meta_description = response.text
            seo_score += 20
            seo_data = json.loads(product.seo) or {}  
            seo_data['description'] = meta_description
            # updated_seo_string = json.dumps(seo_data)
            for issue_dict in issues:
                if 'meta_description_set' in issue_dict:
                    issue_dict['meta_description_set'] = 10
                    break
            for issue_dict in issues:
                if 'meta_description_length' in issue_dict:
                    issue_dict['meta_description_length'] = 10
                    break
            print("Meta desc check passed")
            # # Assign updated values directly
            product.seo = json.dumps(seo_data)
            product.seo_issues = issues
            product.seo_score = seo_score

            # Save changes to DB
            product.save()
            
        if merged.get("content_quality") == 0:
            client = genai.Client()
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"""
            You are an intelligent and smart agent that is experienced in writing a well structured Product Description for a shopify product. 
            Here is the Product Title of a Shopify Product {product.title} for which you need to write an impressive and relevant product description for the product.
            The shop name is The Plants Mall and the shop is associated with growing and selling Cassava, alongside a rich diversity of superfoods, herbs, and medicinal plants like Quinoa, Sesame, Mustard, Barley, Wheat, Aloe Vera, Moringa, Beetroot, Desi Garlic, Basil/Tulsi, Niazbo (Ocimum Basilicum), Aqar Qarha (Anacyclus Pyrethrum) and Ashwagandha (Withania Somnifera), and much more.
            The Product Description should be more than 300 words and it should be a proper html description including all relevant HTML tags in it as well. Use H2 and H3 for headings only. Include relevant icons as well.            
            Do not provide any options. Just return the complete product description. No need to include anything else.
        """
        )
            res = (response.text).replace("```html","").replace("```","")
            html_description = res
            print(html_description)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_description, 'html.parser')
            clean_text = soup.get_text(separator='\n', strip=True)
            print(clean_text)
            for issue_dict in issues:
                if 'content_quality' in issue_dict:
                    issue_dict['content_quality'] = 10
                    break
            
            seo_score += 10
            # # Assign updated values directly
            # product.description_html = html_description
            # product.description = clean_text
            # product.seo_score = seo_score
            # product.seo_issues = issues

            # # Save changes to DB
            # product.save()
            print("Content quality check passed")
        if merged.get("internal_links") == 0:
            description = product.description_html
            # description = product_dict.get('descriptionHtml')
            internal_links = '''\n<p>You can always head to the <a href="https://theplantsmall.com/collections/all/" title="Products">Products</a> for exploring more products.</p>'''

            description = description.rstrip()
            updated_description_html = description + internal_links
            print(updated_description_html)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(updated_description_html, 'html.parser')
            clean_text = soup.get_text(separator='\n', strip=True)
            seo_score += 5
            for issue_dict in issues:
                if 'internal_links' in issue_dict:
                    issue_dict['internal_links'] = 5
                    break
            # # Assign updated values directly
            product.description_html = updated_description_html
            product.description = clean_text
            product.seo_score = seo_score
            product.seo_issues = issues

            # Save changes to DB
            product.save()
            print("Internal links check passed")
        if merged.get("alt_text") == 0:
            image_urls = []
            images = product.images
            images = ast.literal_eval(images)
            print(images)
            edges = images.get('edges')   
            print(edges)        
            for node in edges:
                url = node.get('node').get('url')
                image_urls.append(url)
            # current_image_urls = images
            # images = json.loads(current_image_urls)
            client = genai.Client()
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"""
            You are an intelligent and smart agent that is experienced in writing impressive, unique and ranking alt text for the images for a shopify product. 
            Here is the Product Title of a Shopify Product {product.title}. 
            Here are the image urls for which you need to provide alt texts: {image_urls}
            The shop name is The Plants Mall and the shop is associated with growing and selling Cassava, alongside a rich diversity of superfoods, herbs, and medicinal plants like Quinoa, Sesame, Mustard, Barley, Wheat, Aloe Vera, Moringa, Beetroot, Desi Garlic, Basil/Tulsi, Niazbo (Ocimum Basilicum), Aqar Qarha (Anacyclus Pyrethrum) and Ashwagandha (Withania Somnifera), and much more
            Do not provide any options. Just return a single python list of alt texts. No need to include bullets or headings or anything else.
        """
        )
            res = (response.text).replace("\n","").replace("```python","").replace("```","")
            print(res, len(res))
            import ast
            alt_texts = ast.literal_eval(res)

            # Update altText in each node
            for node, alt_text_value in zip(edges, alt_texts):
                node['node']['altText'] = alt_text_value

            updated_images = {"edges": edges}

            # Update issue values and score
            for issue_dict in issues:
                if 'alt_text' in issue_dict:
                    issue_dict['alt_text'] = 5
                    break

            seo_score += 5
            print(json.dumps(updated_images))
            
            # # Assign updated values directly
            product.images = json.dumps(updated_images)
            product.seo_issues = issues
            product.seo_score = seo_score
            # Save changes to DB
            product.save()
            print("Alt texts check passed")
        if merged.get("relevant_tags") == 0:
            client = genai.Client()
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"""
            You are an intelligent and smart agent that is experienced in writing impressive, unique and ranking tags for a shopify product. 
            Here is the Product Title of a Shopify Product {product.title} for which you need to provide three to four relevant tags for the product.
            The shop name is The Plants Mall and the shop is associated with growing and selling Cassava, alongside a rich diversity of superfoods, herbs, and medicinal plants like Quinoa, Sesame, Mustard, Barley, Wheat, Aloe Vera, Moringa, Beetroot, Desi Garlic, Basil/Tulsi, Niazbo (Ocimum Basilicum), Aqar Qarha (Anacyclus Pyrethrum) and Ashwagandha (Withania Somnifera), and much more
            Do not provide any options. Just return a python list of tags. No need to include bullets or headings or anything else.
        """
        )   
            res = (response.text).replace("\n","").replace("```python","").replace("```","")
            print(res, len(res))
            import ast
            tags = ast.literal_eval(res)
            print(type(tags))
            tags = json.dumps(tags)
            for issue_dict in issues:
                if 'relevant_tags' in issue_dict:
                    issue_dict['relevant_tags'] = 5
                    break
            
            seo_score += 5
            
            # # Assign updated values directly
            # product.tags = tags
            # product.seo_score = seo_score
            # product.seo_issues = issues

            # # Save changes to DB
            # product.save()
            print("Relevant tags check passed")
        if merged.get("product_type_relevant") == 0:
            unique_product_types = Product.objects.values_list('product_type', flat=True).distinct()
            print(list(unique_product_types))
            product_types = list(unique_product_types)
            # print(product_types, type(product_types))
            types= []
            for tup in product_types:
                types.append(tup[0])
            print(types)
            client = genai.Client()
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=f"""
            You are an intelligent and smart agent that is experienced in assigning product type to a shopify product. 
            Here is the Product Title of a Shopify Product {product.title} for which you need to select the most relevant product type from the types {types}, for the product.
            The shop name is The Plants Mall and the shop is associated with growing and selling Cassava, alongside a rich diversity of superfoods, herbs, and medicinal plants like Quinoa, Sesame, Mustard, Barley, Wheat, Aloe Vera, Moringa, Beetroot, Desi Garlic, Basil/Tulsi, Niazbo (Ocimum Basilicum), Aqar Qarha (Anacyclus Pyrethrum) and Ashwagandha (Withania Somnifera), and much more
            Do not provide any options. Just return a single product type. No need to include bullets or headings or anything else.
        """
        )
            product_type = response.text
            print(product_type)
            for issue_dict in issues:
                if 'product_type_relevant' in issue_dict:
                    issue_dict['product_type_relevant'] = 5
                    break
            seo_score += 5            
            # # Assign updated values directly
            # product.product_type = product_type
            # product.seo_score = seo_score
            # product.seo_issues = issues

            # # Save changes to DB
            # product.save()
        if merged.get("image_count") == 0:
            for issue_dict in issues:
                if 'image_count' in issue_dict:
                    issue_dict['image_count'] = 0
                    break
            
            product.seo_score = seo_score
            product.seo_issues = issues

            # Save changes to DB
            product.save()
        return issues, seo_score
    def create_seo_agent(self):
        """
        Creates and initializes the SEO Agent for Shopify Store.
        This agent orchestrates the user query handling and efficient tool calling with respect to the user query.
        
        """
        seo_agent_tools = []
        
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
        FAISS_INDEX_PATH = "shopify_agent/faiss_index_suggestions_rag"
        if os.path.exists(FAISS_INDEX_PATH):
            print(f"Loading FAISS index from {FAISS_INDEX_PATH}...")
            self.vectorstore_suggestions = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        else:
            print("Creating new FAISS index...")
            if docs: 
                self.vectorstore_suggestions = FAISS.from_documents(documents=docs, embedding=embeddings)
                self.vectorstore_suggestions.save_local(FAISS_INDEX_PATH)
                print(f"FAISS index saved to {FAISS_INDEX_PATH}")
            else: 
                print("Cannot create FAISS index: no documentS available.")
                self.vectorstore_suggestions = None
    def initialize_suggestions_rag_tool(self):
        """Initializes the RAG tool for Suggestions."""
        self.website_issues_solver_tool = Tool(
            name="Website_issues_solver",
            func=self.rag_func_for_suggestions,
            description="Useful for when you need to resolve a specific issue or improve a particular product or give suggestions for a particular product."
        )
    def rag_func_for_suggestions(self, issues):
        """
        Takes a list of issues and retrieves relevant solutions from the knowledge base using RAG.
        Example input: ['meta title missing', 'slow page speed']
        """
        try:
            # Create retriever from the existing vectorstore
            retriever = self.vectorstore_suggestions.as_retriever(search_type="mmr", search_kwargs={"k": 5}, fetch_k=20, lambda_mult=0.95)

            # Define a retrieval-augmented generation chain
            # from langchain.chains import RetrievalQA
            # self.rag_chain = RetrievalQA.from_chain_type(
            #     llm=self.llm,
            #     retriever=retriever,
            #     chain_type="stuff",
            #     return_source_documents=True
            # )
            from langchain.chains import ConversationalRetrievalChain

            self.rag_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=retriever
            )

            # Handle both single string or list inputs
            # if isinstance(issues, str):
            #     issues = [issues]
            issues = json.loads(issues)
            result = [{k: v} for k, v in issues[0].items()]
            print(result)
            results = []
            for issue in result:
                query = f"Understand the issue precisely and then find a solution or best practice to resolve the following issue: {issue}"
                response = self.rag_chain.invoke({
                            "question": query,
                            "chat_history": []   
                        })
                answer = response.get("answer", "No solution found.")
                results.append(f"Issue: {issue}\nSolution: {answer}\n")

            # return "\n".join(results)
            return results

        except Exception as e:
            return f"Error using RAG tool: {str(e)}"
    def initialize_product_analysis_tool(self):
        self.product_analysis_tool = Tool(
            name="Product_Analysis_Tool",
            func=self.analysis_tool_func,
            description="Analyzes the Product information to find SEO opportunities, potential areas of ranking, untapped potentials."
        )
    def analysis_tool_func(self, query):
        query = query.replace("```","").replace("\n","")
        import ast
        query = ast.literal_eval(query)
        product_id = query[0]
        store_name = query[1]
        print(product_id, store_name)
        product = Product.objects.filter(id=product_id,store_name=store_name).first()
        product_name = product.title
        online_store_url = product.online_store_url
        description = product.description
        seo = product.seo
        description_html = product.description_html
        images = product.images    
        images = json.loads(images)
        print(images)
        alt_texts = [item['node']['altText'] for item in images.get('edges') if item['node'].get('altText')]
        print(alt_texts)
        print(seo)
        seo = json.loads(seo)
        meta_title = seo.get('title')
        meta_description = seo.get('description') 
        raw_page_data = Page_Query_Metrics.objects.filter(page=online_store_url) 
        opportunities_and_proposed_actions = []
        if raw_page_data.exists():
            for q in raw_page_data:               
                impressions = q.impressions
                position = q.position
                ctr = q.ctr
                opportunity_score = impressions * (1 / position) * (1 - ctr)
                print(opportunity_score)
                pos = q.position
                if pos <= 10:
                    q.category = 'Quick Win'
                elif pos <= 30:
                    q.category = "Growth Opportunity"
                else:
                    q.category = "Low Priority"
            
                if q.category == 'Quick Win':
                    print(f"Improve meta title and description. Add keyword {q.query}")
                    proposed_actions = f"Improve meta title and description. Add keyword {q.query}" 
                    client = genai.Client()
                    response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=f"""
                    You are an intelligent and experienced SEO agent that is skilled in improving meta title and meta description for a product.
                    You are provided with a keyword {q.query} which you need to add naturally in the meta title and meta description.
                    The meta title is: {meta_title}
                    The meta description is: {meta_description}
                    You just need to provide a python tuple containing improved meta title and meta description.
                    No need to explain anything.
            """
            )
                    improved_meta_title_and_description = (response.text).replace("python","").replace("\n","").replace("```","")
                    print(improved_meta_title_and_description)
                    improved_meta_title_and_description = ast.literal_eval(improved_meta_title_and_description)
                    new_meta_title = improved_meta_title_and_description[0]
                    new_meta_description = improved_meta_title_and_description[1]
                    print(new_meta_title)
                    print(new_meta_description)
                    opportunities_and_proposed_actions.append({
                        'opportunity':q.category,
                        'proposed_actions':proposed_actions,
                        'product_name':product_name,
                        'new_meta_title':new_meta_title,
                        'new_meta_description':new_meta_description,
                    }) 
                    #Insert the new meta title and meta description in the database table products_latest
            #     elif q.category == 'Growth Opportunity':
            #         print(f"Add keyword {kw.get('query')} naturally in product description and alt text for images.")
            #         proposed_actions = f"Add keyword {kw.get('query')} naturally in product description and alt text for images."
            #         client = genai.Client()
            #         response = client.models.generate_content(
            #         model='gemini-2.0-flash',
            #         contents=f"""
            #         You are an intelligent and experienced SEO agent that is skilled in adding keywords in the product description and alt text of images precisely for a product.
            #         You are provided with a keyword {kw.get('query')} which you need to add naturally in the product description html {description_html} and alt texts {alt_texts}.
            #         You need to return the updated description html and updated alt texts for the images.
            #         No need to explain anything, just return only the tuple containing html and list of alt texts.
            # """
            # )
            #         # alt_texts = (response.text).replace("python","").replace("\n","").replace("```","")
            #         # for image_data, alt_text_value in zip(images, alt_texts):
            #         #     image_data['node']['altText'] = alt_text_value
            #         description_html_and_alt_texts = (response.text).replace("```python","").replace("\n","").replace("```","")
            #         print(description_html_and_alt_texts)
            #         improved_description_and_alt_texts = ast.literal_eval(description_html_and_alt_texts)
            #         description_html_new = improved_description_and_alt_texts[0]
            #         alt_texts_new = improved_description_and_alt_texts[1]
            #         print(description_html_new)
            #         print(alt_texts_new) 
            #         opportunities_and_proposed_actions.append({
            #             'opportunity':cat,
            #             'proposed_actions':proposed_actions,
            #             'product_name':product_name,
            #             'new_description_html':description_html_new,
            #             'new_alt_texts':alt_texts_new,
            #         })
                    #Update the alt texts, descriptionHtml and description in the database table products_latest for the concerned product.

                elif q.category == 'Low Priority':
                    print((f"Write a blog post or article related to the keyword {q.query} and link it back to the product page."))
                    proposed_actions = f"Write a blog post or article related to the keyword {q.query} and link it back to the product page."
                    client = genai.Client()
                    response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=f"""
                    You are an intelligent writer agent that has experience in writing search engine optimized blog posts and articles. You are given a keyword for a Shopify product called "{product_name}".
                    You need to use the keyword: {q.query} and product name: {product_name} to write an optimized article with proper HTML tags.
                    Write a detailed 800-1000 words article and make sure the keyword is included in the article naturally. 
                    Use only H1 or H2 tags in the article. Add animated icons as well in the html file.
                    Return only a valid HTML for the article. Do not add anything else.   
            """
            )
                    article_html = (response.text).replace("html","").replace("\n","")
                    print(article_html)
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(article_html, 'html.parser')
                    clean_text = soup.get_text(separator='\n', strip=True)
                    opportunities_and_proposed_actions.append({
                        'opportunity':q.category,
                        'proposed_actions':proposed_actions,
                        'product_name':product_name,
                        'article_html':article_html,
                        'description':clean_text
                    })
            return opportunities_and_proposed_actions
        else:
            return []

        
    def initialize_seo_tool(self):
        self.seo_tool = Tool(
            name="SEO_Tool",
            func=self.seo_tool_func,
            description="Analyzes the Product information to assign an SEO Score to it."
        )
    def seo_tool_func(self, query):
        print(type(query))
        query = ast.literal_eval(query)
        print(type(query))
        store_name = query.get('store_name')
        print(store_name)
        query.pop('store_name')
        print(query)
        print(store_name)
        seo = query.get('seo')
        seo = json.loads(seo)
        print(seo, type(seo))
        meta_title = seo.get('title')
        meta_description = seo.get('description')
        print(meta_title, meta_description)
        if meta_title != None:
            meta_title_length = len(meta_title)
        if meta_title == None:
            meta_title_length = 0
        if meta_description != None:
            meta_description_length = len(meta_description)
        if meta_description == None:
            meta_description_length = 0
        print(meta_title_length, meta_description_length)
        images = query.get('images')
        images = ast.literal_eval(images)
        
        print(query.get('description_html'))
        if query.get('description_html') != "":
            html_content = query.get('description_html')
        else:
            html_content = ""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        links = soup.find_all('a')
        print(links)
        client = genai.Client()
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=f"""
            You are a smart and efficient SEO agent. Your goal is to understand the Product Information {query} precisely and perform the below mentioned checks accurately. And eventually assigning an SEO score.
            Instructions:
            - You will be forwarded a Shopify Product's information as an input. You need to perform some checks so that you can eventually assign an SEO score to that particular product.
            - The checks that you need to perform are as follows:
            * Check if keyword is present in the title.
                - Provide a score for this factor out of 5.
            * Does the handle contain the product name?
                - Provide a score for this factor out of 10.
            * Meta title {meta_title} should not be None. If meta title is None, just give this factor a score of 0.
                - Provide a score for this factor out of 10.
            * Is the Product type relevant to the product?
                - Provide a score for this factor out of 5.
            * The length of meta title {meta_title_length} should be between 30 and 60. If length of meta title is 0, just give this factor a score of 0.
                - Provide a score for this factor out of 10.
            * Check the quality of the content in descriptionHtml that is the content relevant to the product and is the description over 300 words?
                - Provide a score for this factor out of 10.
            * Meta description {meta_description} should not be None. If meta description is None, just give this factor a score of 0.
                - Provide a score for this factor out of 10.
            * The length of meta description {meta_description_length} should be between 120 and 190 characters. If the length of meta description is 0, just give this factor a score of 0.
                - Provide a score for this factor out of 10.
            * Check at least one internal link (<a href>) should be present in {links} to another product, collection, or page on the store.
                - Provide a score for this factor out of 5.
            * There should be at least three images. If the image count {len(images.get('edges'))} is less than 3, just give this factor a score of 0.
                - Provide a score for this factor out of 5.
            * Check altText for all the images. If altText is an empty string or null, just give this factor a score of 0.
                - Provide a score for this factor out of 5.
            * Are there at least 2 relevant tags?
                - Provide a score for this factor out of 5.
            * Is the status ACTIVE (i.e., visible to search engines)?
                - Provide a score for this factor out of 5.
            * Are at least 1 custom metafield present?
                - Provide a score for this factor out of 5.
        After performing all the checks, add the numbers of checks and compile a Final SEO Score.
        Return the Final SEO Score along with the results of checks performed in a JSON format like the following example: 
        [
        {{
            "checks":[
                {{"keyword_in_title":score}},
                {{"product_name_in_handle":score}},
                {{"meta_title_set":score}},
                {{"product_type_relevant":score}},
                {{"meta_title_length":score}},
                {{"content_quality":score}},
                {{"meta_description_set":score}},
                {{"meta_description_length":score}},
                {{"internal_links":score}},
                {{"image_count":score}},
                {{"alt_text":score}},
                {{"relevant_tags":score}},
                {{"status_active":score}},
                {{"metafields":score}}
            ],
            "seo_score":Final SEO Score,
            "product_name":Product Name
        }}
        ]
        """
        )
        json_output = (response.text).replace('```json',"").replace("```","")
        
        json_output = json.loads(json_output)
        json_output = json_output[0]

        product_name = json_output.get('product_name')
        checks = json_output.get('checks')
        seo_score = 0
        for item in checks:
            for value in item.values():
                if value != 0:
                    seo_score += value
        print(f"SEO Score: {seo_score}")
        print(checks)
        checks = json.dumps(checks)
        conn = sqlite3.connect(f'main_db_for_{store_name}.db')
        c = conn.cursor()
        c.execute('''
            UPDATE products_latest
            SET
                seo_score = ?,
                seo_issues = ?
            WHERE
                title = ? 
            ''', (
                seo_score,
                checks,
                product_name 
        ))
        
        conn.commit()

        return json_output
    def initialize_writer_tool(self):
        self.writer_tool = Tool(
            name="Writer_Tool",
            func=self.writer_tool_func,
            description="Analyzes the Product information and product page keyword performance to suggest blogs and articles that should be published for the product."
        )
    def classify_intent(self, query):
            query_lower = query.lower()
            if any(word in query_lower for word in ["benefit", "use", "how to", "recipe", "vs", "what is", "meaning", "purpose"]):
                return "informational"
            elif any(word in query_lower for word in ["buy", "price", "order", "shop", "discount", "sale"]):
                return "transactional"
            else:
                return "topical"
    def keyword_strength(self,impressions, position):
        
        if impressions > 5 and position < 15:
            return "strong"
        elif impressions > 0 and position < 30:
            return "medium"
        else:
            return "weak"
    def writer_tool_func(self, query):
        query = query.replace("```","").replace("\n","")
        import ast
        query = ast.literal_eval(query)
        product_id = query[0]
        store_name = query[1]
        print(product_id, store_name)
        conn = sqlite3.connect(f'main_db_for_{store_name}.db')
        c = conn.cursor()   
        c.execute('''
    SELECT online_store_url, description, title FROM products_latest WHERE id = ?;          
        ''',
        (product_id,))
        product = c.fetchall()[0]
        online_store_url = product[0]
        description = product[1]
        product_name = product[2]

        c.execute('''
            SELECT * FROM page_query_metrics WHERE page = ?;          
        ''',
        (online_store_url,))
        conn.commit()
        metrics = c.fetchall()
        print(len(metrics))
        columns = [col[0] for col in c.description]
        raw_page_data = []
        for p in metrics:
            product_dict = dict(zip(columns, p)) if p else None
            raw_page_data.append(product_dict)
        print(raw_page_data)
        enriched = []
        for item in raw_page_data:
            item["intent"] = self.classify_intent(item["query"])
            item["strength"] = self.keyword_strength(item["impressions"], item["position"])
            enriched.append(item)
        print(enriched)
        filtered_queries = [
            q for q in enriched 
            if q["intent"] in ["informational"] and q["strength"] in ["strong", "medium"]
        ]
        client = genai.Client()
        response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=f"""
        You are an SEO strategist. You are given keyword data for a Shopify product called "{product_name}".
        Each keyword includes its intent and strength:
        {json.dumps(filtered_queries, indent=2)}
        Based on this, suggest 3 SEO blog article ideas that can drive organic traffic and naturally promote this product.
        Focus on **informational** and **medium/strong** keywords.
        For each blog, provide:
        - "title": catchy SEO-friendly blog title
        - "description": one-sentence summary of what it covers
        - "target_keywords": key phrases from the data

        Return the result as valid JSON.
"""
)
        blog_ideas_for_informational_intent = (response.text).replace("```json","").replace("```","")
        print(blog_ideas_for_informational_intent)
        
        # return blog_ideas_for_informational_intent
    def create_shopify_store_manager_agent(self):
        """
        Creates and initializes the Shopify Store Manager Agent.
        This agent orchestrates the user query handling and efficient tool calling with respect to the user query.
        """
        shopify_store_manager_base_tools = [self.seo_agent, self.seo_tool, self.website_issues_solver_tool, self.suggestions_tool,self.writer_tool, self.product_analysis_tool]
        
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
        self.initialize_suggestions_rag_tool()
        self.initialize_rag_for_Suggestions()
        self.initialize_writer_tool()
        self.initialize_product_analysis_tool()
        if not self.llm or not self.get_all_products:
            print("Initialization failed: LLM or a tool not set up.")
            return False
        
        self.create_shopify_store_manager_agent()
        self.create_seo_agent()
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

""" cursor.execute("SELECT * FROM products_latest")
products = cursor.fetchall() 
columns = [col[0] for col in cursor.description]

for p in products[27:28]:
    product_dict = dict(zip(columns, p)) if p else None
    
    raw_product_data.append(product_dict)
conn.close()
print(raw_product_data)


for data in raw_product_data:
    if data.get('seo_score') == None:
        ip = f"SEO Agent, {data}"
        seo_score_and_issues = manager.chat_with_agent(ip)
        print(seo_score_and_issues)
    elif data.get("seo_score") is not None and data.get('seo_score') < 90:
        ip = f"SEO Agent, {data}"
        seo_score_and_issues = manager.chat_with_agent(ip)
        print(seo_score_and_issues) """


# Getting the updated products with SEO Score less than a certain threshold:
# cursor.execute("SELECT * FROM products_latest WHERE seo_score < 100")
# products = cursor.fetchall() 
# analyzed_product_data = []
# columns = [col[0] for col in cursor.description]
# print(len(products))
# for p in products:
#     product_dict = dict(zip(columns, p)) if p else None
    
#     analyzed_product_data.append(product_dict)
# # conn.close()
# print(len(analyzed_product_data))
# for data in analyzed_product_data[0:1]:
#     if data.get('seo_score') < 96:
#         id = data.get('id')
#         print(id)
#         print(data.get('title'))
#         ip = f"Suggest Solutions, {id}"
        
#         seo_score_and_issues = manager.chat_with_agent(ip)
#         print(seo_score_and_issues)
#Use the updated products data with SEO Score to invoke the Suggestions Agent:
"""
Sample 1 for Product SEO Score distributor:
* Check keyword is present in the title.
    - Provide a score for this factor out of 25.
  * Check the quality of meta description.
    - Provide a score for this factor out of 20
  * Check the URL is clean, keyword included.
    - Provide a score for this factor out of 10
  * Check image alt text for the images is descriptive, relevant and not null.
    - Provide a score for this factor out of 15
  * Check keyword is present in description or not.
    - Provide a score for this factor out of 10
  * Check content is unique, greater than 300 words, user H2/H3.
    - Provide a score for this factor out of 10
  * Check at least 2 relevant internal links to this product page.
    - Provide a score for this factor out of 10.
"""

"""
Sample 2 for Product SEO Score distributor:
* Check keyword is present in the title.
    - Provide a score for this factor out of 10.
  * Check the quality of meta description.
    - Provide a score for this factor out of 10
  * Check the URL is SEO-friendly and hyphenated.
    - Provide a score for this factor out of 10
  * Check image alt text for the images is descriptive, relevant and not null.
    - Provide a score for this factor out of 10
  * Check keyword is present in description or not.
    - Provide a score for this factor out of 10
  * Check CTR, impressions, average position and pagespeed score by calling 'metrics_checker' tool with the product id as an input.
    - Provide a score for CTR out of 15.
    - Provide a score for impressions out of 10.
    - Provide a score for position out of 10.
    - Provide a score for pagespeed score out of 15 keeping in mind that pagespeed score greater than 89 is a good enough score.
"""

"""

Sample 3 for Product SEO distributor:
* Check if keyword is present in the title.
    - Provide a score for this factor out of 5.
* Does the handle contain the main keyword?
    - Provide a score for this factor out of 10.
* Is meta title explicitly set (not null)?
    - Provide a score for this factor out of 15.
* Is the length of meta title between 30 and 60?
    - Provide a score for this factor out of 10.
* Is the description html over 300 words?
    - Provide a score for this factor out of 10.
* Is meta description explicitly set (not null)?
    - Provide a score for this factor out of 10.
* Is meta descriptions length between 120 and 158 characters?
    - Provide a score for this factor out of 10.
* Does the HTML contain at least one internal link to another product, collection, or page on the store?
    - Provide a score for this factor out of 5.
* Are there at least 3 unique images?
    - Provide a score for this factor out of 5.
* Are there at least 2 relevant tags?
    - Provide a score for this factor out of 5.
* Is the status ACTIVE (i.e., visible to search engines)?
    - Provide a score for this factor out of 10.
* Are at least 1 custom metafield present?
    - Provide a score for this factor out of 5.
"""

"""
{{
            "seo_score":final SEO Score,
            "issues":{{
                    "issue_1":"Detail of Issue 1",
                    "issue_2":"Detail of Issue 2",
            }}
        }}
"""