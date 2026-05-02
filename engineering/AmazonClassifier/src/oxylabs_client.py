import os
import time

import requests
import streamlit as st
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

OXYLAB_BASE_URL = "https://realtime.oxylabs.io/v1/queries"
DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_READ_TIMEOUT = 120


def get_timeout():
    read_timeout = int(os.getenv("OXYLABS_READ_TIMEOUT", DEFAULT_READ_TIMEOUT))
    return DEFAULT_CONNECT_TIMEOUT, read_timeout


def extract_content(payload):
    if not isinstance(payload, dict):
        return {}

    results = payload.get("results")
    if isinstance(results, list) and results:
        first = results[0]
        if isinstance(first, dict):
            return first.get("content", {}) or {}

    if "content" in payload:
        return payload.get("content", {}) or {}

    return {}


def post_query(payload):
    username = os.getenv("OXYLABS_USERNAME")
    password = os.getenv("OXYLABS_PASSWORD")

    if not username or not password:
        raise RuntimeError("Missing OXYLABS_USERNAME or OXYLABS_PASSWORD in environment")

    response = requests.post(
        OXYLAB_BASE_URL,
        auth=HTTPBasicAuth(username, password),
        json=payload,
        timeout=get_timeout(),
    )
    response.raise_for_status()
    return response.json()


def normalize_product(content):
    category_path = []
    for category in content.get("category_path") or []:
        if isinstance(category, str) and category.strip():
            category_path.append(category.strip())
        elif isinstance(category, dict):
            name = category.get("name") or category.get("title")
            if name:
                category_path.append(str(name).strip())

    return {
        "asin": content.get("asin"),
        "url": content.get("url"),
        "brand": content.get("brand"),
        "price": content.get("price"),
        "stock": content.get("stock"),
        "title": content.get("title"),
        "rating": content.get("rating"),
        "images": content.get("images", []),
        "categories": content.get("category", [])
        or content.get("categories", []),
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
        "domain": domain,
        "parse": True,
    }

    raw = post_query(payload)
    content = extract_content(raw)
    normalized = normalize_product(content)

    if not normalized.get("asin"):
        normalized["asin"] = asin

    normalized["amazon_domain"] = domain
    normalized["geo_location"] = geo_location
    return normalized


def clean_product_name(title):
    title = str(title or "").strip()
    if "-" in title:
        title = title.split("-")[0]
    if "|" in title:
        title = title.split("|")[0]
    return title.strip()


def extract_search_results(content):
    items = []

    if not isinstance(content, dict):
        return items

    if "results" in content:
        results = content["results"]
        if isinstance(results, dict):
            if "organic" in results:
                items.extend(results["organic"])
            if "paid" in results:
                items.extend(results["paid"])
        elif isinstance(results, list):
            items.extend(results)

    elif "products" in content and isinstance(content["products"], list):
        items.extend(content["products"])

    return items


def normalize_search_results(item):
    asin = item.get("asin") or item.get("product_asin")
    title = item.get("title")

    if not (asin or title):
        return None

    return {
        "asin": asin,
        "title": title,
        "category": item.get("category"),
        "price": item.get("price"),
        "rating": item.get("rating"),
    }


def search_competitors(query_title, domain, categories, pages=1, geo_location=""):
    st.write("Searching for competitors")

    search_title = clean_product_name(query_title)
    results = []
    seen_asins = set()

    strategies = ["featured"]

    for sort_by in strategies:
        for page in range(1, max(1, pages) + 1):
            payload = {
                "source": "amazon_search",
                "query": search_title,
                "parse": True,
                "domain": domain,
                "page": page,
                "sort_by": sort_by,
                "geo_location": geo_location,
            }

            if categories and categories[0]:
                payload["refinements"] = {"category": categories[0]}

            try:
                content = extract_content(post_query(payload))
            except requests.Timeout as exc:
                st.warning(f"Search timed out for page {page} ({sort_by}): {exc}")
                continue
            except requests.RequestException as exc:
                st.warning(f"Search request failed for page {page} ({sort_by}): {exc}")
                continue

            items = extract_search_results(content)

            for item in items:
                result = normalize_search_results(item)
                if result and result["asin"] not in seen_asins:
                    seen_asins.add(result["asin"])
                    results.append(result)

    st.write(f"Found {len(results)} competitors")
    return results


def scrape_multiple_products(asins, geo_location, domain):
    st.write("Scraping competitor details")

    products = []
    total = len(asins)
    if total == 0:
        st.write("No competitor ASINs found")
        return products

    progress_text = st.empty()
    progress_bar = st.progress(0)

    for idx, a in enumerate(asins, 1):
        try:
            progress_text.write(f"Processing competitor {idx}/{total}: {a}")
            progress_bar.progress(idx / total)

            product = scrape_product_details(a, geo_location, domain)
            products.append(product)

        except Exception as exc:
            st.warning(f"Skipping {a}: {exc}")

        time.sleep(0.1)

    progress_text.empty()
    progress_bar.empty()

    st.write(f"Successfully scraped {len(products)} out of {total} competitors")
    return products
