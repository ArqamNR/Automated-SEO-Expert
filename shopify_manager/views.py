from django.shortcuts import render
import sqlite3

import requests
import json
import os
from django.http import HttpResponse
from django.shortcuts import render
from shopify_agent.shopify_store_agent_automted import ShopifyStoreManager
from shopify_agent.shopify_store_agent import ShopifyChat
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import os
from django.db.models import Sum, Avg
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from shopify_agent.send_email import send_email_with_csv_attachment, send_simple_email
from shopify_agent.use_shopify_creds_and_fetch_data import insert_products_data
shopify_store_agent = ShopifyStoreManager()
shopify_chat = ShopifyChat()
message_for_issues_resolved = ''
agent_creation_success = shopify_store_agent.initialize()
chatbot_creation_success = shopify_chat.initialize()
store_name = ''
access_token = ''
from dotenv import load_dotenv
load_dotenv()


def home(request):
    return render(request, 'shopify_manager/index_2.html')
from django.http import JsonResponse
from shopify_manager.models import Product, Page_Query_Metrics, Website_Issues
from django.db.models import Q
import json
from django.core.paginator import Paginator
import ast
from django.forms.models import model_to_dict
@csrf_exempt
def fetch_products(request):
    """
    Handles the POST request for fetching products from Django models.
    """
    SHOPIFY_STORE_NAME = os.environ.get('SHOPIFY_SHOP_NAME')
    SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            print("Raw request body:", request.body) 
            global store_name
            store_name = data.get("storeName", "").strip()
            access_token = data.get("accessToken", "").strip()
            global user_email
            user_email = data.get("email")
            optimized = data.get("optimized")   
            active = data.get("active")         
            analyzed = data.get("analyzed")     
            score_min = data.get("score_min")
            score_max = data.get("score_max")
            seo_score_null = data.get("seo_score_null")
            # 🔹 Read pagination parameters from URL
            page_number = data.get("page")
            page_size = 10
            if not store_name or not access_token or not user_email:
                return JsonResponse({"error": "Store name, email and access token are required."}, status=400)

            # 🛑 CRITICAL VALIDATION STEP 🛑
            if store_name != SHOPIFY_STORE_NAME or access_token != SHOPIFY_ACCESS_TOKEN:
                print(f"Validation failed for store: {store_name}")
                return JsonResponse({"error": "Invalid store credentials."}, status=401)
            print(f"Fetching product data for store: {store_name}")
            # ✅ Check if we already have this store’s products in the Django DB
            existing_products = Product.objects.filter(store_name=store_name)
            
            if existing_products.exists():
                print(f"Products for store '{store_name}' already exist in Django DB.")
            else:
                print(f"No products found for {store_name}. Fetching from Shopify...")

                # 🔹 Fetch data from Shopify API (same logic you already have)
                # save_products_to_json(shop_name=store_name, access_token=access_token)

                # 🔹 Load saved JSON
                with open(f"shopify_agent/data_of_shopify_products_{store_name}.json", "r") as file:
                    products_data = json.load(file)

                # 🔹 Save data to Django DB
                product_objects = []
                for record in products_data:
                    product_objects.append(Product(
                        store_name=store_name,
                        id=str(record.get("id")),
                        title=record.get("title", ""),
                        handle=record.get("handle", ""),
                        description=record.get("description", ""),
                        description_html=record.get("descriptionHtml", ""),
                        product_type=record.get("productType", ""),
                        vendor=record.get("vendor", ""),
                        status=record.get("status", ""),
                        tags=json.dumps(record.get("tags", [])),
                        created_at=record.get("createdAt", ""),
                        updated_at=record.get("updatedAt", ""),
                        published_at=record.get("publishedAt", ""),
                        online_store_url=record.get("onlineStoreUrl", ""),
                        online_store_preview_url=record.get("onlineStorePreviewUrl", ""),
                        seo=json.dumps(record.get("seo", {})),
                        metafields=json.dumps(record.get("metafields", {})),
                        images=json.dumps(record.get("images", {})),
                        variants=json.dumps(record.get("variants", {})),
                        options=json.dumps(record.get("options", [])),
                        internal_links=json.dumps(record.get("internal_links", []))
                    ))

                # ✅ Bulk insert for speed
                Product.objects.bulk_create(product_objects, ignore_conflicts=True)

                print(f"Inserted {len(product_objects)} products for store '{store_name}' ✅")
            # ✅ Fetch products from Django model
            products = Product.objects.all().order_by('id')
            if optimized is True:
                products = products.filter(seo_score__gt=90)
            elif optimized is False:
                products = products.filter(seo_score__lte=90)
            if active is True:
                products = products.filter(status__iexact="active")
            elif active is False:
                products = products.exclude(status__iexact="active")
            if analyzed is True:
                products = products.exclude(seo_score__isnull=True)
            elif analyzed is False:
                products = products.filter(seo_score__isnull=True)
            if score_min is not None and score_max is not None:
                products = products.filter(seo_score__gte=score_min, seo_score__lte=score_max)

            paginator = Paginator(products, page_size)
            page_obj = paginator.get_page(page_number)

            sample_products = []
            specific_products_data = []
            for product in page_obj:
                issues_combined = [] 
                title = product.title
                seoscore = product.seo_score
                status = product.status
                issues_and_proposed_solutions = product.issues_and_proposed_solutions
                if product.seo_issues:
                    print(type(product.seo_issues))
                    issues = ast.literal_eval(product.seo_issues)
                    print(type(issues))   
                    merged = {k: v for d in issues for k, v in d.items()}
                     
                    # Convert SEO issue flags into readable statements (same as before)
                    issues_combined.append(
                        'Meta Title is not set. 0/10' if merged.get('meta_title_set') == 0 else 'Meta Title is explicitly set. 10/10'
                    )
                    issues_combined.append(
                        'Length of Meta Title is not appropriate. 0/10' if merged.get('meta_title_length') == 0 else 'Length of Meta Title is appropriate. 10/10'
                    )
                    issues_combined.append(
                        'Meta Description is missing. 0/10' if merged.get('meta_description_set') == 0 else 'Meta Description is present. 10/10'
                    )
                    issues_combined.append(
                        'Length of Meta Description is not appropriate. 0/10' if merged.get('meta_description_length') == 0 else 'Length of Meta Description is appropriate. 10/10'
                    )
                    issues_combined.append(
                        "There's no internal link included. 0/5" if merged.get('internal_links') == 0 else 'Internal link/s are included. 5/5'
                    )
                    issues_combined.append(
                        'Alt Text is missing. 0/5' if merged.get('alt_text') == 0 else 'Alt Text is present. 5/5'
                    )
                    issues_combined.append(
                        'Description missing/too short. 0/10' if merged.get('content_quality') == 0 else 'Description well-written. 10/10'
                    )
                    issues_combined.append(
                        'Product Type missing/irrelevant. 0/5' if merged.get('product_type_relevant') == 0 else 'Product Type relevant. 5/5'
                    )
                    issues_combined.append(
                        'Tags missing/irrelevant. 0/5' if merged.get('relevant_tags') == 0 else 'Tags relevant. 5/5'
                    )
                    issues_combined.append(
                        'Less than 3 images. 0/5' if merged.get('image_count') == 0 else 'Sufficient images. 5/5'
                    )
                    issues_combined.append(
                        'No metafields added. 0/5' if merged.get('metafields') == 0 else 'Metafields present. 5/5'
                    )
                    issues_combined.append(
                        'Keyword not in title. 0/5' if merged.get('keyword_in_title') == 0 else 'Keyword in title. 5/5'
                    )
                    issues_combined.append(
                        'Product name not in handle. 0/10' if merged.get('product_name_in_handle') == 0 else 'Product name in handle. 10/10'
                    )
                    issues_combined.append(
                        'Product inactive. 0/5' if merged.get('status_active') == 0 else 'Product active. 5/5'
                    )

                sample_products.append({
                    "Product Name": product.title,
                    "SEO Score": product.seo_score,
                    "status": product.status,
                    "issues": issues_combined,
                    "id": product.id,
                    "issues_and_proposed_solutions": product.issues_and_proposed_solutions
                })

            return JsonResponse({
                "products": sample_products,
                "page": page_number,
                "total_pages": paginator.num_pages,
                "filters_used": {
                "optimized": optimized,
                "active": active,
                "analyzed": analyzed,
                "score_min": score_min,
                "score_max": score_max
            },
            })

        except Exception as e:
            print(f"Error fetching products: {e}")
            return JsonResponse({"error": f"An internal error occurred: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)
@csrf_exempt
def analyze_products(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

    try:
        # ✅ Parse incoming payload
        data = json.loads(request.body.decode("utf-8"))
        store_name = data.get("storeName")
        analyze_limit = data.get("limit", 50)  # optional limit on how many products to analyze

        if not store_name:
            return JsonResponse({"error": "store_name is required."}, status=400)

        print(f"Starting SEO analysis for store: {store_name}")

        # ✅ Initialize manager (the AI analysis agent)
        manager = ShopifyStoreManager()
        manager.initialize()

        # ✅ Get products needing analysis (unscored or low score)
        products_to_analyze = Product.objects.filter(
            store_name=store_name
        ).filter(
            Q(seo_score__isnull=True) | Q(seo_score__lt=85)
        )[:analyze_limit]

        if not products_to_analyze:
            return JsonResponse({"message": "No products need analysis."}, status=200)

        analyzed_results = []

        for product in products_to_analyze:
            product_data = model_to_dict(product)

            ip = f"Assign SEO Score, {product_data}"

            print(f"Analyzing product: {product.title}")
            seo_score_and_checks = manager.chat_with_agent(ip)
            seo_score_and_checks = seo_score_and_checks.replace("```json", "").replace("```", "")

            try:
                seo_score_and_checks = ast.literal_eval(seo_score_and_checks)
            except Exception:
                continue  # skip invalid response

            seo_score = seo_score_and_checks.get("seo_score")
            checks = seo_score_and_checks.get("checks")

            merged_checks = {}
            for d in checks or []:
                merged_checks.update(d)

            # ✅ Update product in Django DB
            product.seo_score = seo_score
            product.seo_issues = [merged_checks]
            product.save()

            analyzed_results.append({
                "id": product.id,
                "title": product.title,
                "seo_score": seo_score,
                "output_list_of_checks": merged_checks
            })

        return JsonResponse({
            "message": f"Successfully analyzed {len(analyzed_results)} products for store '{store_name}'.",
            "results": analyzed_results
        }, status=200)

    except Exception as e:
        print(f"Error analyzing products: {e}")
        return JsonResponse({"error": str(e)}, status=500)
@csrf_exempt
def get_user_input(request):
    if request.method == "POST":
        try:

            data = json.loads(request.body.decode("utf-8"))
            user_input = data.get("message", "")

            if chatbot_creation_success:
                bot_response = shopify_chat.chat_with_agent(user_input)
            else:
                bot_response = "Agent not ready."

            total_tokens_used = shopify_chat.store_manager_total_tokens
            input_tokens = shopify_chat.store_manager_input_tokens
            output_tokens = shopify_chat.store_manager_output_tokens
            return JsonResponse({"response": bot_response, 
                                 "tokens": total_tokens_used,
                                 "input_tokens":input_tokens,
                                 "output_tokens":output_tokens})

        except Exception as e:
            print(f"Exception: {e}")
            return JsonResponse({"error": str(e)}, status=400)

    else:
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)
@csrf_exempt
def analyze_single_and_multiple_products(request):
    """
    Handles POST request for analyzing products using the provided credentials.
    Uses Django ORM instead of direct SQLite connection.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            
            store_name = data.get("storeName")
            product_ids = data.get("product_ids", [])

            if not store_name or not product_ids:
                return JsonResponse({"error": "storeName and product_ids are required."}, status=400)

            from shopify_agent.shopify_store_agent_automted import ShopifyStoreManager  # ✅ adjust if needed
            manager = ShopifyStoreManager()
            manager.initialize()

            # ✅ Fetch products directly from Django model
            products = Product.objects.filter(store_name=store_name, id__in=product_ids)

            if not products.exists():
                return JsonResponse({"error": "No matching products found for given IDs."}, status=404)

            analyzed_results = []

            for product in products:
                # Convert ORM object to dict
                product_data = model_to_dict(product)

                if product.seo_score is None or product.seo_score < 85:
                    ip = f"Assign SEO Score, {product_data}"

                    seo_score_and_checks = manager.chat_with_agent(ip)
                    seo_score_and_checks = seo_score_and_checks.replace("```json", "").replace("```", "")

                    try:
                        seo_score_and_checks = ast.literal_eval(seo_score_and_checks)
                    except Exception as e:
                        print(f"Invalid AI response format for product {product.id}: {e}")
                        continue

                    checks = seo_score_and_checks.get("checks", [])
                    merged_checks = {}
                    for d in checks:
                        merged_checks.update(d)

                    output_list_of_checks = [merged_checks]
                    analyzed_results.append({
                        "product_id": product.id,
                        "checks": output_list_of_checks
                    })

                    # ✅ Optionally update the product in DB
                    product.seo_issues = json.dumps(output_list_of_checks)
                    product.seo_score = seo_score_and_checks.get("seo_score", product.seo_score)
                    product.save(update_fields=["seo_issues", "seo_score"])

            return JsonResponse({
                "checks": output_list_of_checks,
                "message": "Successfully analyzed the product(s)."
            })

        except Exception as e:
            print(f"Error analyzing products: {e}")
            return JsonResponse({"error": f"An internal error occurred: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)
@csrf_exempt
def resolve_single_product_issues(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        product_ids = data.get("product_ids", [])
        store_name = data.get("storeName")  # assuming you send it in the payload
        # user_email = data.get("email")  # assuming you send it in the payload
        print(user_email)
        manager = ShopifyStoreManager()
        manager.initialize()
        all_product_issues = []
        resolved_product_data = []
        product_issues_data = []
        print(len(product_ids))
        for id in product_ids:
            print(id)
            product = Product.objects.filter(id=id, store_name=store_name).first()
            if not product:
                continue
 
            if product.seo_score < 95:
                ip = f"Suggest Solutions, {id, store_name}"
                resolving_issues_seo_score = manager.chat_with_agent(ip)
                resolving_issues_seo_score = ast.literal_eval(resolving_issues_seo_score)
                resolving_issues = resolving_issues_seo_score[0]
                seo_score =resolving_issues_seo_score[1]
                print(resolving_issues, type(resolving_issues))
                print(seo_score, type(seo_score))
                issues = resolving_issues
                product = Product.objects.filter(id=id, store_name=store_name).first()
                seo = json.loads(product.seo)
                print(seo)
                meta_title = seo.get("title")
                meta_description = seo.get("description")

                images = product.images
                images = ast.literal_eval(images)
                print(images)
                alt_texts = [i.get("node", {}).get("altText") for i in images.get('edges')]
                description = product.description
                product_type = product.product_type
                tags = product.tags
                print(tags)
                if issues:
                    print(issues)
                    merged = {k: v for d in issues for k, v in d.items()}
                    print(merged)
                    issues_solutions = []
                    print(len(meta_title))
                    print(len(meta_description))
                    if merged.get('meta_title_set') == 10:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":'Meta Title was not set.', "Solution":f"Meta Title is set as {meta_title}."})
                    if merged.get('meta_title_length') == 10:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Length of Meta title was not appropriate.", "Solution":f"Meta Title is set as {meta_title} with length {len(meta_title)}."})
                    if merged.get('meta_description_set') == 10:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Meta Description was missing.", "Solution":f"Meta Description is set as {meta_description}."})
                    if merged.get('meta_description_length') == 10:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Length of Meta Description was not appropriate.", "Solution":f"Meta Description is set as {meta_description} with length {len(meta_description)}."})
                    if merged.get('internal_links') == 5:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Internal links were missing.", "Solution":f"An internal link to the products page is added."})
                    if merged.get('alt_text') == 5:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Alt text was missing for the images.", "Solution":f"Alt texts are added as: {alt_texts}."})                        
                    if merged.get('content_quality') == 10:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Either the description was missing or it was shorter than 300 words", "Solution":f"Description is set as: {description}."})
                    if merged.get('product_type_relevant') == 5:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Either the product type was irrelevant or it was missing", "Solution":f"Product Type is now set as: {product_type}."})
                    if merged.get('relevant_tags') == 5:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Either the tags were missig or irrelavant", "Solution":f"Tags are set as: {tags}."})
                    if merged.get('image_count') == 0:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Either there are no images or less than 3 images.", "Solution":f"Need to add more images."})
                    if merged.get('metafields') == 0:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"There are no metafields for the Product.", "Solution":f"Need to add meta fields for the Product."})
                    product.issues_and_proposed_solutions = product_issues_data
                    product.seo_score = seo_score
                    product.save(update_fields=["issues_and_proposed_solutions"])

                    send_simple_email(
                        user_email,
                        f"Issues resolved for {product.title}. Check Reports section."
                    )
                    all_product_issues.extend(product_issues_data)
                    
                else:
                    all_product_issues.append({
                        "Product": product.title,
                        "ID": product.id,
                        "Message": "Issues already resolved"
                    })
            else:
                all_product_issues.append({
                    "Product": product.title,
                    "ID": product.id,
                    "Message": "Issues already resolved"
                })
            
        return JsonResponse({
            "issues_and_proposed_solutions": all_product_issues,
            "message": f"Processing complete! We’ve notified {user_email}"
        })

    except Exception as e:
        print(f"Error fetching products: {e}")
        return JsonResponse({"error": f"An internal error occurred: {str(e)}"}, status=500)
@csrf_exempt
def resolve_product_issues(request):
    """
    Handles the POST request for analyzing products using the provided credentials.
    Currently returns mock data. REPLACE THIS LOGIC LATER.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
        
        store_name = data.get("storeName")  # assuming you send it in the payload
        # user_email = data.get("email")  # assuming you send it in the payload
        print(user_email)
        product_ids = list(Product.objects.filter(store_name=store_name).values_list('id', flat=True))
        manager = ShopifyStoreManager()
        manager.initialize()
        all_product_issues = []
        resolved_product_data = []
        product_issues_data = []
        not_analyzed_count = 0
        optimized_count = 0
        to_be_resolved_count = 0
        print(len(product_ids))
        for id in product_ids:
            print(id)
            product = Product.objects.filter(id=id, store_name=store_name).first()
            if not product:
                continue
            if product.seo_score is None:
                not_analyzed_count += 1
                all_product_issues.append({
                    "Product": product.title,
                    "ID": product.id,
                    "Message": "Product not analyzed yet."
                })
                continue
 
            if product.seo_score < 95:
                to_be_resolved_count += 1
                ip = f"Suggest Solutions, {id, store_name}"
                resolving_issues_seo_score = manager.chat_with_agent(ip)
                resolving_issues_seo_score = ast.literal_eval(resolving_issues_seo_score)
                resolving_issues = resolving_issues_seo_score[0]
                seo_score =resolving_issues_seo_score[1]
                print(resolving_issues, type(resolving_issues))
                print(seo_score, type(seo_score))
                issues = resolving_issues
                product = Product.objects.filter(id=id, store_name=store_name).first()
                seo = json.loads(product.seo)
                print(seo)
                meta_title = seo.get("title")
                meta_description = seo.get("description")

                images = product.images
                images = ast.literal_eval(images)
                print(images)
                alt_texts = [i.get("node", {}).get("altText") for i in images.get('edges')]
                description = product.description
                product_type = product.product_type
                tags = product.tags
                print(tags)
                if issues:
                    print(issues)
                    merged = {k: v for d in issues for k, v in d.items()}
                    print(merged)
                    issues_solutions = []
                    print(len(meta_title))
                    print(len(meta_description))
                    if merged.get('meta_title_set') == 10:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":'Meta Title was not set.', "Solution":f"Meta Title is set as {meta_title}."})
                    if merged.get('meta_title_length') == 10:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Length of Meta title was not appropriate.", "Solution":f"Meta Title is set as {meta_title} with length {len(meta_title)}."})
                    if merged.get('meta_description_set') == 10:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Meta Description was missing.", "Solution":f"Meta Description is set as {meta_description}."})
                    if merged.get('meta_description_length') == 10:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Length of Meta Description was not appropriate.", "Solution":f"Meta Description is set as {meta_description} with length {len(meta_description)}."})
                    if merged.get('internal_links') == 5:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Internal links were missing.", "Solution":f"An internal link to the products page is added."})
                    if merged.get('alt_text') == 5:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Alt text was missing for the images.", "Solution":f"Alt texts are added as: {alt_texts}."})                        
                    if merged.get('content_quality') == 10:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Either the description was missing or it was shorter than 300 words", "Solution":f"Description is set as: {description}."})
                    if merged.get('product_type_relevant') == 5:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Either the product type was irrelevant or it was missing", "Solution":f"Product Type is now set as: {product_type}."})
                    if merged.get('relevant_tags') == 5:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Either the tags were missig or irrelavant", "Solution":f"Tags are set as: {tags}."})
                    if merged.get('image_count') == 5:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"Either there are no images or less than 3 images.", "Solution":f"Need to add more images."})
                    if merged.get('metafields') == 0:
                        product_issues_data.append({"Product":product.title, "ID":product.id, "Issue":"There are no metafields for the Product.", "Solution":f"Need to add meta fields for the Product."})
                    product.issues_and_proposed_solutions = product_issues_data
                    product.seo_score = seo_score
                    product.save(update_fields=["issues_and_proposed_solutions"])

                    send_simple_email(
                        user_email,
                        f"Issues resolved for {product.title}. Check Reports section."
                    )
                    all_product_issues.extend(product_issues_data)
                    
                else:
                    all_product_issues.append({
                        "Product": product.title,
                        "ID": product.id,
                        "Message": "Issues already resolved"
                    })
            else:
                optimized_count += 1
                all_product_issues.append({
                    "Product": product.title,
                    "ID": product.id,
                    "Message": "Issues already resolved"
                })
        total_products = len(product_ids)

        if optimized_count == total_products:
            message = "All products have already been optimized."
        elif not_analyzed_count == total_products:
            message = "No products have been analyzed yet."
        elif optimized_count + not_analyzed_count == total_products:
            message = "All analyzed products have been optimized."
        elif to_be_resolved_count > 0:
            message = f"Processing complete! We've notified {user_email}."
        else:
            message = "No actionable products found."
        # return JsonResponse({
        #     "issues_and_proposed_solutions": all_product_issues,
        #     "message": f"Processing complete! We’ve notified {user_email}"
        # })
        return JsonResponse({
            "issues_and_proposed_solutions": all_product_issues,
            "summary": {
                "total_products": total_products,
                "optimized": optimized_count,
                "not_analyzed": not_analyzed_count,
                "resolved_now": to_be_resolved_count
            },
            "message": message
        })

    except Exception as e:
        print(f"Error fetching products: {e}")
        return JsonResponse({"error": f"An internal error occurred: {str(e)}"}, status=500)
@csrf_exempt
def approve_reject_product_suggestions(request):
    """
    Handles the POST request for analyzing products using the provided credentials.
    Currently returns mock data. REPLACE THIS LOGIC LATER.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            print(data)
            action = data.get('action')
            product_name = data.get('product_name')

            if action == "approve":
                return JsonResponse({
                    "message": f"You have approved the proposed suggestions for the Product {product_name}. Changes will be published on the Store soon."
                })
            elif action == "reject":
                return JsonResponse({
                    "message": f"You have rejected the proposed suggestions for the Product {product_name}. No changes published."
                })
        except Exception as e:
            print(f"Error fetching products: {e}")
            return JsonResponse({"error": f"An internal error occurred: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)
@csrf_exempt
def write_blogs_and_articles_for_a_product(request):
    import ast
    """
    Handles the POST request for analyzing products using the provided credentials.
    Currently returns mock data. REPLACE THIS LOGIC LATER.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            print(data)
            product_id = data.get("product_id","")
            manager = ShopifyStoreManager()
            manager.initialize()
            ip = f"Find SEO Opportunities for the product: {product_id, store_name}"
            product = Product.objects.get(id=product_id)
            write_blogs_and_articles = manager.chat_with_agent(ip)
    
            if isinstance(write_blogs_and_articles, str):
                try:
                    write_blogs_and_articles = ast.literal_eval(write_blogs_and_articles)
                except (ValueError, SyntaxError):
                    write_blogs_and_articles = []

            if write_blogs_and_articles:
                return JsonResponse({
                    "opportunities": write_blogs_and_articles,
                    "message": f"Suggested blogs and articles for Product ID: {product_id}"
                }, safe=False)
            else:
                return JsonResponse({
                    "opportunities": [],
                    "message": f"Product page doesn't exist for the product {product.title}"
                }, safe=False)
        except Exception as e:
            print(f"Error fetching products: {e}")
            return JsonResponse({"error": f"An internal error occurred: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)
@csrf_exempt
def update_product_on_shopify(request):
    """
    Handles the POST request for analyzing products using the provided credentials.
    Currently returns mock data. REPLACE THIS LOGIC LATER.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            
            
            
            
            return JsonResponse({
                # "products": sample_products,
                "message": f"Successfully updated the product information on Shopify."
            })

        except Exception as e:
            print(f"Error fetching products: {e}")
            return JsonResponse({"error": f"An internal error occurred: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)
@csrf_exempt
def seo_dashboard_view(request):
    """
    Renders the SEO Performance Dashboard.
    
    This view is responsible for serving the HTML file that contains the
    frontend logic for collecting credentials and displaying metrics.
    """
    # The path 'shopify_manager/seo_performance_dashboard.html' assumes Django's 
    # TEMPLATES setting includes the app's 'templates' directory.
    return render(request, 'shopify_manager/gsc_metrics.html', {})

# @login_required
@csrf_exempt
def get_query_metrics(request):
    """
    Handles the GET request to fetch Google Search Console query metrics 
    from the database.

    In a real scenario, this would take the website URL as a parameter 
    to filter the data.
    """
    if request.method == "POST":
        try:
            global website_url
            website_url = request.POST.get('url')
            api_key = request.POST.get('api_key')
            creds_file = request.FILES.get("credentials")
            print(creds_file)
            if not website_url or not api_key or not creds_file:
                return JsonResponse({"error": "Website URL, Google Project API Key and Credentials are required."}, status=400)
            # Fetch only required columns using ORM
            specific_page_performance = Page_Query_Metrics.objects.filter(page=website_url).values(
                'query', 'clicks', 'impressions', 'ctr', 'position'
            )
            print(specific_page_performance)
            # Convert QuerySet to list of dicts
            raw_page_data = list(specific_page_performance)
            return JsonResponse({
                "success": True,
                "metrics": raw_page_data,
                "website_url": website_url,
            })

        except Exception as e:
            print(f"Error fetching query metrics: {e}")
            return JsonResponse({"success": False, "error": f"An internal error occurred: {str(e)}"}, status=500)

    return JsonResponse({"success": False, "error": "Only GET requests are allowed."}, status=405)
@csrf_exempt
def get_core_web_vitals(request):
    if request.method == "POST":
        try:
            
            website_url = request.POST.get('url')
            api_key = request.POST.get('api_key')
            creds_file = request.FILES.get("credentials")
            if not website_url or not api_key or not creds_file:
                return JsonResponse({"error": "Website URL, Google Project API Key and Credentials are required."}, status=400)
            # 1️⃣ Fetch Core Web Vitals for the specific page
            raw_page_data = list(
                Website_Issues.objects.filter(page=website_url)
                .values('lcp', 'cls', 'inp', 'pagespeedscore')
            )
            print(raw_page_data)
            # 2️⃣ Get pages that are indexed (PASS + Submitted and indexed)
            indexed_pages = list(
                Website_Issues.objects.filter(
                    indexstatusresult_verdict="PASS",
                    coverage_state="Submitted and indexed"
                ).values('page')
            )
            print(len(indexed_pages))
            # 3️⃣ Get pages that are NOT indexed
            not_indexed_pages = list(
                Website_Issues.objects.exclude(
                    indexstatusresult_verdict="PASS",
                    coverage_state="Submitted and indexed"
                ).values('page')
            )
            print(len(not_indexed_pages))
            return JsonResponse({
                "success": True,
                "core_web_vitals": raw_page_data,
                "indexed_pages": indexed_pages,
                "not_indexed_pages": not_indexed_pages,
                "website_url": website_url
            })

        except Exception as e:
            print(f"Error fetching query metrics: {e}")
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": False, "error": "Only GET requests are allowed."}, status=405)
@csrf_exempt
def get_website_issues(request):
    if request.method == "POST":
        try:
            
            website_url = request.POST.get('url')
            api_key = request.POST.get('api_key')
            creds_file = request.FILES.get("credentials")
            if not website_url or not api_key or not creds_file:
                return JsonResponse({"error": "Website URL, Google Project API Key and Credentials are required."}, status=400)

            website_issues_data = list(Website_Issues.objects.filter(page=website_url).values(
                'indexstatusresult_verdict', 'coverage_state', 'robotsTxtState', 'indexingState', 'pageFetchState', 'crawledAs','mobileUsabilityResult','referringUrls','lastCrawlTime','googleCanonical','userCanonical','lcp','cls','inp','pagespeedscore','richResultsResult','issues'
            ))
            website_issues_data = website_issues_data[0]
            d = website_issues_data
            lcp = d.get('lcp')
            lcp = float(lcp)
            inp = d.get('inp')
            inp = float(inp)
            cls = float(d.get('cls'))
            print(lcp, cls, inp)
            pagespeed = d.get('pagespeedscore')
            indexingstate = d.get('indexingState')
            mobileusability = d.get('mobileUsabilityResult')
            robotstxtstate = d.get('robotsTxtState')
            coveragestate = d.get('coverage_state')
            indexstatusresult_verdict = d.get('indexstatusresult_verdict')
            richResultsResult = d.get('richResultsResult')
            # richResultsResult = json.loads(richResultsResult)
            richResultsResult_ = richResultsResult.get('detectedItems')
            all_issues = []
            if richResultsResult_ != None:
                for detected_item in richResultsResult_:
                    for item in detected_item.get("items", []):
                        for issue in item.get("issues", []):
                            all_issues.append(issue.get("issueMessage"))
                unique_issues = sorted(list(set(all_issues)))
                print(unique_issues)
            identified_issues = []
            if lcp <= 2.5:
                pass
            if lcp <= 4 and lcp > 2.5:
                print("LCP Needs Improvement.")
                identified_issues.append({'lcp':'Needs Improvement. Should be less than 2.5 s.'})
            if lcp > 4:
                print("LCP is Poor.")
                identified_issues.append({'lcp':'Poor. Should be less than 2.5 s.'})
            if inp <= 0.2:
                pass
            if inp <= 0.5 and inp > 0.2:
                print("INP Needs Improvement.")
                identified_issues.append({'inp':'Needs Improvement. Should be less than 0.2 s.'})
            if inp > 0.5:
                print("INP is Poor.")
                identified_issues.append({'inp':'Poor. Should be less than 0.2 s.'})
            if cls <= 0.1:
                pass
            if cls <= 0.25 and cls > 0.1:
                print("CLS Needs Improvement.")
                identified_issues.append({'cls':'Needs Improvement. Should be less than 0.1'})
            if cls > 0.25:
                print("CLS is Poor.")
                identified_issues.append({'cls':'Poor. Should be less than 0.1'})

            if pagespeed >=90:
                pass
            if pagespeed < 90:
                identified_issues.append({'pagespeedscore':'Needs Improvement. Should be at least 90.'})
            if mobileusability == 'VERDICT_UNSPECIFIED':
                identified_issues.append({'mobileUsabilityResult':'Mobile Usability Verdict is unspecified. Needs to be resolved'})
            if robotstxtstate != 'ALLOWED':
                identified_issues.append({'robotsTxtState':'robots.txt file is not correct.'})
            else:
                pass
            if indexingstate != "INDEXING_ALLOWED":
                identified_issues.append({'indexingState':'Indexing is not allowed.'})
            else:
                pass

            if coveragestate != "Submitted and indexed":
                identified_issues.append({'coverage_state':'Page is not indexed'})
            else:
                pass
            if indexstatusresult_verdict != "PASS":
                identified_issues.append({'indexstatusresult_verdict':'Index status is not pass.'})
            else:
                pass
            if richResultsResult == {}:
                pass
            else:
                identified_issues.append({'richResultsResult':f'Some rich results issues are found as: {unique_issues}'})
            print(len(identified_issues))
            merged_dict = {}
            for d in identified_issues:
                merged_dict.update(d)
            output_list_of_issues = [merged_dict]
            print(output_list_of_issues)
            issues = json.dumps(output_list_of_issues)
            
            Website_Issues.objects.filter(page=website_url).update(issues=issues)
            return JsonResponse({
                "success": True,
                "website_issues":output_list_of_issues,
                "website_url": website_url
            })

        except Exception as e:
            print(f"Error fetching query metrics: {e}")
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": False, "error": "Only GET requests are allowed."}, status=405)
@csrf_exempt
def resolve_website_issues(request):
    if request.method == "GET":
        try:
            import ast
            import sqlite3
            website_url = request.GET.get('url') or request.POST.get('url')
            print(website_url)
            conn = sqlite3.connect(f'main_db_for_0px5tv-ji.db')
            cursor = conn.cursor()
            cursor.execute("SELECT issues FROM website_issues WHERE page = ?",(website_url,))
            issues = cursor.fetchone()[0]

            print(f"Here are the website issues: {issues}")
            ip = f"Provide Solutions for the website issues, {issues}"
            manager = ShopifyStoreManager()
            manager.initialize()        
            resolving_website_issues = manager.chat_with_agent(ip)
            try:
                _issues = ast.literal_eval(resolving_website_issues)
            except Exception:
                _issues = [resolving_website_issues]
            issues_solutions = []
            issues_solutions_to_report = []
            for input_string in _issues:
                issue_start_tag = "Issue: "
                issue_start_index = input_string.find(issue_start_tag) + len(issue_start_tag)
                solution_start_tag = "Solution: "
                solution_start_index = input_string.find(solution_start_tag)
                issue = input_string[issue_start_index:solution_start_index].strip()
                issue_dict = ast.literal_eval(issue)
                key = list(issue_dict.keys())[0]
                value = issue_dict[key]
                
                output_string = f"{key} {value}"
                
                solution_content_start_index = solution_start_index + len(solution_start_tag)
                solution = input_string[solution_content_start_index:].strip()
                issues_solutions.append({'Issue':output_string, 'Solution':solution})
                issues_solutions_to_report.append({"URL":website_url,'Issue':output_string, 'Solution':solution})
            print(issues_solutions)
            # #Send the website and their proposed solutions via email:
            # import pandas as pd
            # df = pd.DataFrame(issues_solutions_to_report)
            # df.to_excel(f'Website Issues and solutions.xlsx')
            # send_email_with_csv_attachment('arqam@northrays.com',f'Website Issues and solutions.xlsx')
            return JsonResponse({
                "success": True,
                "issues_and_solutions":issues_solutions,
                "website_url": website_url
            })
        except Exception as e:
            print(f"Error fetching query metrics: {e}")
            return JsonResponse({"success": False, "error": f"An internal error occurred: {str(e)}"}, status=500)
    return JsonResponse({"success": False, "error": "Only GET requests are allowed."}, status=405)

@csrf_exempt
def resolve_single_website_issue(request):
    if request.method == "POST":
        try:
            import ast
            
            data = json.loads(request.body.decode("utf-8"))
            print(data)
            issues = data.get('issue')
            print(issues)
            parts = issues.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                output_dict = {key: value}
            else:
                output_dict = {}
            issues = [output_dict]
            website_url = data.get('website_url')
            issues = json.dumps(issues)
            print(f"Here are the website issues: {issues}")
            ip = f"Provide Solutions for the website issues, {issues}"
            manager = ShopifyStoreManager()
            manager.initialize()        
            resolving_website_issues = manager.chat_with_agent(ip)
            try:
                _issues = ast.literal_eval(resolving_website_issues)
            except Exception:
                _issues = [resolving_website_issues]
            issues_solutions = []
            issues_solutions_to_report = []
            for input_string in _issues:
                issue_start_tag = "Issue: "
                issue_start_index = input_string.find(issue_start_tag) + len(issue_start_tag)
                solution_start_tag = "Solution: "
                solution_start_index = input_string.find(solution_start_tag)
                issue = input_string[issue_start_index:solution_start_index].strip()
                issue_dict = ast.literal_eval(issue)
                key = list(issue_dict.keys())[0]
                value = issue_dict[key]
                
                output_string = f"{key} {value}"
                
                solution_content_start_index = solution_start_index + len(solution_start_tag)
                solution = input_string[solution_content_start_index:].strip()
                issues_solutions.append({'Issue':output_string, 'Solution':solution})
                issues_solutions_to_report.append({"URL":website_url,'Issue':output_string, 'Solution':solution})
            print(issues_solutions)
            # #Send the website and their proposed solutions via email:
            # import pandas as pd
            # df = pd.DataFrame(issues_solutions_to_report)
            # df.to_excel(f'Website Issues and solutions.xlsx')
            # send_email_with_csv_attachment('arqam@northrays.com',f'Website Issues and solutions.xlsx')
            return JsonResponse({
                "success": True,
                "issues_and_solutions":issues_solutions,
                "website_url": website_url
            })
        except Exception as e:
            print(f"Error fetching query metrics: {e}")
            return JsonResponse({"success": False, "error": f"An internal error occurred: {str(e)}"}, status=500)
    return JsonResponse({"success": False, "error": "Only GET requests are allowed."}, status=405)

@csrf_exempt
def complete_website_performance(request):
    if request.method == "GET":
        try:
            summary = Page_Query_Metrics.objects.aggregate(
            total_clicks=Sum('clicks'),
            total_impressions=Sum('impressions'),
            average_ctr=Avg('ctr'),
            average_position=Avg('position'),
        )
            print(summary)
        except Exception as e:
            print(f"Error fetching query metrics: {e}")
            return JsonResponse({"success": False, "error": str(e)}, status=500)
        return JsonResponse({
                "success": True,
                "summary":summary
            })
    return JsonResponse({"success": False, "error": "Only GET requests are allowed."}, status=405)
def chat_interface(request):
    return render(request, 'shopify_manager/chatbot.html')

















@csrf_exempt
def resolve_product_issues_(request):
    """
    Handles the POST request for analyzing products using the provided credentials.
    Currently returns mock data. REPLACE THIS LOGIC LATER.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
           
            manager = ShopifyStoreManager()
            manager.initialize()
            resolved_product_data = []
            print(store_name)
            conn = sqlite3.connect(f'main_db_for_{store_name}.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products_latest WHERE seo_score < 100")
            products = cursor.fetchall() 
            analyzed_product_data = []
            product_issues_data = []
            columns = [col[0] for col in cursor.description]
            print(len(products))
            for p in products:
                product_dict = dict(zip(columns, p)) if p else None
                
                analyzed_product_data.append(product_dict)
            for product in analyzed_product_data:
                
                if product.get('seo_score') < 95:
                    id = product.get('id')
                    print(id)
                    print(product.get('title'))
                    
                    ip = f"Suggest Solutions, {id, store_name}"
                    
                    resolving_issues = manager.chat_with_agent(ip)
            cursor.execute("SELECT * FROM products_latest WHERE seo_score < 100")
            products = cursor.fetchall()
            for p in products:
                product_dict = dict(zip(columns, p)) if p else None
                resolved_product_data.append(product_dict)
            for product in resolved_product_data:
                issues = product.get('seo_issues')
                print(product.get('title'))
                seo = product.get('seo')
                seo = json.loads(seo)
                meta_title = seo[0].get('title')
                meta_description = seo[0].get('description')
                images = product.get('images')
                images = json.loads(images)
                print(images)
                alt_texts = [i.get('node').get('altText') for i in images]
                description = product.get('description')
                product_type = product.get('product_type')
                tags = product.get('tags')
                
                if issues:
                    issues = json.loads(issues)
                    print(issues)
                    merged = {k: v for d in issues for k, v in d.items()}
                    if merged.get('meta_title_set') == 10:
                        product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":'Meta Title was not set.', "Solution":f"Meta Title is set as {meta_title}."})
                    if merged.get('meta_title_length') == 10:
                        product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Length of Meta title was not appropriate.", "Solution":f"Meta Title is set as {meta_title} with length {len(meta_title)}."})
                    if merged.get('meta_description_set') == 10:
                        product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Meta Description was missing.", "Solution":f"Meta Description is set as {meta_description}."})
                    if merged.get('meta_description_length') == 10:
                        product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Length of Meta Description was not appropriate.", "Solution":f"Meta Description is set as {meta_description} with length {len(meta_description)}."})
                    if merged.get('internal_links') == 5:
                        product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Internal links were missing.", "Solution":f"An internal link to the products page is added."})
                    if merged.get('alt_text') == 5:
                        product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Alt text was missing for the images.", "Solution":f"Alt texts are added as: {alt_texts}."})                        
                    if merged.get('content_quality') == 10:
                        product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Either the description was missing or it was shorter than 300 words", "Solution":f"Description is set as: {description}."})
                    if merged.get('product_type_relevant') == 5:
                        product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Either the product type was irrelevant or it was missing", "Solution":f"Product Type is now set as: {product_type}."})
                    if merged.get('relevant_tags') == 5:
                        product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Either the tags were missig or irrelavant", "Solution":f"Tags are set as: {tags}."})
                    if merged.get('image_count') == 5:
                        product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Either there are no images or less than 3 images.", "Solution":f"Need to add more images."})
                    if merged.get('metafields') == 0:
                        product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"There are no metafields for the Product.", "Solution":f"Need to add meta fields for the Product."})
            print(product_issues_data)
            # Converting the report into an excel file and sending it via email:
            # import pandas as pd
            # df = pd.DataFrame(product_issues_data)
            # df.to_excel(f'Shopify Products Reviewed for store {store_name}.xlsx')
            # send_email_with_csv_attachment('arqam@northrays.com',f'Shopify Products Reviewed for store {store_name}.xlsx')
           
            return JsonResponse({
                # "products": sample_products,
                "message": f"Successfully resolved the issues for the Products."
            })

        except Exception as e:
            print(f"Error fetching products: {e}")
            return JsonResponse({"error": f"An internal error occurred: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)
# @csrf_exempt
# def analyze_single_and_multiple_products_(request):
#     import ast
#     """
#     Handles the POST request for analyzing products using the provided credentials.
#     Currently returns mock data. REPLACE THIS LOGIC LATER.
#     """
#     if request.method == "POST":
#         try:
#             data = json.loads(request.body.decode("utf-8"))
             
#             product_ids = data.get("product_ids")
#             manager = ShopifyStoreManager()
#             manager.initialize()
#             raw_product_data = []
#             print(data)
#             store_name = data.get('storeName')
#             print(store_name)
#             conn = sqlite3.connect(f'main_db_for_{store_name}.db')
#             cursor = conn.cursor()
#             for id in product_ids:
#                 # Assigning SEO Score to all the products:
#                 cursor.execute("SELECT * FROM products_latest WHERE id = ?",(id,))
#                 products = cursor.fetchall() 
#                 columns = [col[0] for col in cursor.description]

#                 for p in products:
#                     product_dict = dict(zip(columns, p)) if p else None
                    
#                     raw_product_data.append(product_dict)
#                 # conn.close()
#                 print(raw_product_data)
#                 for data in raw_product_data:
#                     if data.get('seo_score') == None:
#                         data['store_name'] = store_name
#                         ip = f"Assign SEO Score, {data}"
#                         seo_score_and_checks = manager.chat_with_agent(ip)
#                         seo_score_and_checks = seo_score_and_checks.replace("```json","").replace("```","")
#                         print(seo_score_and_checks, type(seo_score_and_checks))
#                         seo_score_and_checks = ast.literal_eval(seo_score_and_checks)
#                         checks = seo_score_and_checks.get('checks')
#                         merged_checks = {}
#                         for d in checks:
#                             merged_checks.update(d)
#                         output_list_of_checks = [merged_checks]
#                         print(output_list_of_checks)
#                     elif data.get("seo_score") is not None and data.get('seo_score') < 85:
#                         data['store_name'] = store_name
#                         ip = f"Assign SEO Score, {data}"
#                         seo_score_and_checks = manager.chat_with_agent(ip)
#                         print(seo_score_and_checks, type(seo_score_and_checks))
#                         seo_score_and_checks = ast.literal_eval(seo_score_and_checks)
#                         checks = seo_score_and_checks.get('checks')
#                         merged_checks = {}
#                         for d in checks:
#                             merged_checks.update(d)
#                         output_list_of_checks = [merged_checks]
#                         print(output_list_of_checks)
#             return JsonResponse({
#                 "checks": output_list_of_checks,
#                 "message": f"Successfully analyzed the Product/s."
#             })

#         except Exception as e:
#             print(f"Error fetching products: {e}")
#             return JsonResponse({"error": f"An internal error occurred: {str(e)}"}, status=500)

#     return JsonResponse({"error": "Only POST requests are allowed."}, status=405)
# @csrf_exempt
# def analyze_products_(request):
#     import ast
#     """
#     Handles the POST request for analyzing products using the provided credentials.
#     Currently returns mock data. REPLACE THIS LOGIC LATER.
#     """
#     if request.method == "POST":
#         try:
#             data = json.loads(request.body.decode("utf-8"))
            
#             # Placeholder for where you would call your Shopify agent logic:
#             # products = shopify_store_agent.fetch_products(store_name, access_token) 
#             manager = ShopifyStoreManager()
#             manager.initialize()
#             raw_product_data = []
#             print(store_name)
#             conn = sqlite3.connect(f'main_db_for_{store_name}.db')
#             cursor = conn.cursor()
#             # Assigning SEO Score to all the products:
#             cursor.execute("SELECT * FROM products_latest")
#             products = cursor.fetchall() 
#             columns = [col[0] for col in cursor.description]

#             for p in products:
#                 product_dict = dict(zip(columns, p)) if p else None
                
#                 raw_product_data.append(product_dict)
#             conn.close()
#             print(raw_product_data)
#             for data in raw_product_data[6:8]:
#                 if data.get('seo_score') == None:
#                     data['store_name'] = store_name
#                     ip = f"Assign SEO Score, {data}"
#                     seo_score_and_checks = manager.chat_with_agent(ip)
#                     seo_score_and_checks = seo_score_and_checks.replace("```json","").replace("```","")
#                     print(seo_score_and_checks, type(seo_score_and_checks))
#                     seo_score_and_checks = ast.literal_eval(seo_score_and_checks)
#                     checks = seo_score_and_checks.get('checks')
#                     merged_checks = {}
#                     for d in checks:
#                         merged_checks.update(d)
#                     output_list_of_checks = [merged_checks]
#                     print(output_list_of_checks)
#                 elif data.get("seo_score") is not None and data.get('seo_score') < 85:
#                     data['store_name'] = store_name
#                     ip = f"Assign SEO Score, {data}"
#                     seo_score_and_checks = manager.chat_with_agent(ip)
#                     print(seo_score_and_checks, type(seo_score_and_checks))
#                     seo_score_and_checks = ast.literal_eval(seo_score_and_checks)
#                     checks = seo_score_and_checks.get('checks')
#                     merged_checks = {}
#                     for d in checks:
#                         merged_checks.update(d)
#                     output_list_of_checks = [merged_checks]
#                     print(output_list_of_checks)
#             return JsonResponse({
#                 "checks": output_list_of_checks,
#                 "message": f"Successfully analyzed the Products."
#             })

#         except Exception as e:
#             print(f"Error fetching products: {e}")
#             return JsonResponse({"error": f"An internal error occurred: {str(e)}"}, status=500)

#     return JsonResponse({"error": "Only POST requests are allowed."}, status=405)
# @csrf_exempt
# def resolve_single_product_issues_(request):
    """
    Handles the POST request for analyzing products using the provided credentials.
    Currently returns mock data. REPLACE THIS LOGIC LATER.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            print(data)
            
            product_ids = data.get("product_ids",[])
            print(product_ids)
            manager = ShopifyStoreManager()
            manager.initialize()
            resolved_product_data = []
            print(store_name)
            conn = sqlite3.connect(f'main_db_for_{store_name}.db')
            cursor = conn.cursor()
            for id in product_ids:
                cursor.execute("SELECT * FROM products_latest WHERE id = ?",(id,))
                products = cursor.fetchall()            
                analyzed_product_data = []
                product_issues_data = []
                columns = [col[0] for col in cursor.description]

                for p in products:
                    product_dict = dict(zip(columns, p)) if p else None                
                    analyzed_product_data.append(product_dict)        
                for product in analyzed_product_data:                
                    if product.get('seo_score') < 95:
                        id = product.get('id')
                        print(id)
                        print(product.get('title'))
                        
                        ip = f"Suggest Solutions, {id, store_name}"
                        
                        resolving_issues = manager.chat_with_agent(ip)
                        cursor.execute("SELECT * FROM products_latest WHERE id = ?",(id,))
                        products = cursor.fetchall()
                        for p in products:
                            product_dict = dict(zip(columns, p)) if p else None
                            resolved_product_data.append(product_dict)
                        for product in resolved_product_data:
                            issues = product.get('seo_issues')
                            print(product.get('title'))
                            seo = product.get('seo')
                            seo = json.loads(seo)
                            meta_title = seo[0].get('title')
                            meta_description = seo[0].get('description')
                            images = product.get('images')
                            images = json.loads(images)
                            print(images)
                            alt_texts = [i.get('node').get('altText') for i in images]
                            description = product.get('description')
                            product_type = product.get('product_type')
                            tags = product.get('tags')
                            
                            if issues:
                                issues = json.loads(issues)
                                print(issues)
                                merged = {k: v for d in issues for k, v in d.items()}
                                if merged.get('meta_title_set') == 10:
                                    product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":'Meta Title was not set.', "Solution":f"Meta Title is set as {meta_title}."})
                                if merged.get('meta_title_length') == 10:
                                    product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Length of Meta title was not appropriate.", "Solution":f"Meta Title is set as {meta_title} with length {len(meta_title)}."})
                                if merged.get('meta_description_set') == 10:
                                    product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Meta Description was missing.", "Solution":f"Meta Description is set as {meta_description}."})
                                if merged.get('meta_description_length') == 10:
                                    product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Length of Meta Description was not appropriate.", "Solution":f"Meta Description is set as {meta_description} with length {len(meta_description)}."})
                                if merged.get('internal_links') == 5:
                                    product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Internal links were missing.", "Solution":f"An internal link to the products page is added."})
                                if merged.get('alt_text') == 5:
                                    product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Alt text was missing for the images.", "Solution":f"Alt texts are added as: {alt_texts}."})                        
                                if merged.get('content_quality') == 10:
                                    product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Either the description was missing or it was shorter than 300 words", "Solution":f"Description is set as: {description}."})
                                if merged.get('product_type_relevant') == 5:
                                    product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Either the product type was irrelevant or it was missing", "Solution":f"Product Type is now set as: {product_type}."})
                                if merged.get('relevant_tags') == 5:
                                    product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Either the tags were missig or irrelavant", "Solution":f"Tags are set as: {tags}."})
                                if merged.get('image_count') == 5:
                                    product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"Either there are no images or less than 3 images.", "Solution":f"Need to add more images."})
                                if merged.get('metafields') == 0:
                                    product_issues_data.append({"Product":product.get('title'), "ID":product.get('id'), "Issue":"There are no metafields for the Product.", "Solution":f"Need to add meta fields for the Product."})
                        print(product_issues_data)
                        conn = sqlite3.connect(f'main_db_for_{store_name}.db')
                        c = conn.cursor()
                        c.execute('''
                            UPDATE products_latest
                            SET
                                issues_and_proposed_solutions = ?
                            WHERE
                                title = ? 
                            ''', (
                                json.dumps(product_issues_data),
                                product.get('title') 
                        ))
                        
                        conn.commit()
                        msg = f'''The issues in the product and their proposed solutions have been generated.
                        You can head to the Reports section on the dashboard to view the detailed report for the product {product.get('title')}
                        '''
                        print(user_email, msg)
                        send_simple_email(user_email, msg)
                        return JsonResponse({
                    "issues_and_proposed_solutions": product_issues_data,
                    "message": f"Check Reports to see suggestions. You have also been emailed at {user_email}",
                })
                    else:
                        print('Issues already resolved for this product')
                        return JsonResponse({
                    # "products": sample_products,
                    "message": f"Issues are already resolved for this product."
                })
            
                
            # print(product_issues_data)
            # Converting the report into an excel file and sending it via email:
            # import pandas as pd
            # df = pd.DataFrame(product_issues_data)
            # df.to_excel(f'Shopify Products Reviewed for store {store_name}.xlsx')
            # send_email_with_csv_attachment('arqam@northrays.com',f'Shopify Products Reviewed for store {store_name}.xlsx')
            
            

        except Exception as e:
            print(f"Error fetching products: {e}")
            return JsonResponse({"error": f"An internal error occurred: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)