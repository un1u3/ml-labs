import json 
import time
import requests
import streamlit as st 
from dotenv import load_dotenv 
import os 
from requests.auth import HTTPBasicAuth


load_dotenv()


OXYLAB_BASE_URL = 'https://realtime.oxylabs.io/v1/queries'



def extract_content(payload):
    if not isinstance(payload, dict):
        return {}

    # Case 1: standard Oxylabs shape
    results = payload.get("results")
    if isinstance(results, list) and results:
        first = results[0]
        if isinstance(first, dict):
            return first.get("content", {}) or {}

    # Case 2: content at top level
    if "content" in payload:
        return payload.get("content", {}) or {}

    # Case 3: nothing useful
    return {}
                


def post_query(payload):
    username = os.getenv('OXYLABS_USERNAME')
    password = os.getenv('OXYLABS_PASSWORD')

    response = requests.post(
        OXYLAB_BASE_URL,
        auth=HTTPBasicAuth(username, password),
        json = payload,
        timeout=60
    )   
    response.raise_for_status()
    response_json = response.json()
    return response_json




def normalize_product(content):
    category_path = []
    if content.get("category_path"):
        category_path = [cat.strip() for cat in content["category_path"] if cat]

    return {
        "asin": content.get("asin"),
        "url": content.get("url"),
        "brand": content.get("brand"),
        "price": content.get("price"),
        "stock": content.get("stock"),
        "title": content.get("title"),
        "rating": content.get("rating"),
        "images": content.get("images", []),
        "categories": content.get("category", []) or content.get("categories", []),
        "category_path": category_path,
        "currency": content.get("currency"),
        "buybox": content.get("buybox", []),
        "product_overview": content.get("product_overview", []),
    }



def scrape_product_details(asin, geo_location, domain):
    payload = {
        "source": "amazon_product",
        "query": asin,
        "geo_location": geo_location,
        "domain":domain,
        "parse":True
    }
    raw = post_query(payload)
    content = extract_content(raw)
    normalized = normalize_product(content)
    if not normalized.get("asin"):
        normalized['asin'] = asin
    normalized['amazon_domain'] = domain
    normalized['geo_location'] = geo_location
    return normalized
