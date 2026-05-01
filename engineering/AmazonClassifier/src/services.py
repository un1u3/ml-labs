import streamlit as st 
from src.db import Database
from src.oxylabs_client import scrape_product_details

def scrape_and_store_product(asin, geo_location, domain):
    data = scrape_and_store_product(asin, geo_location, domain):
    db = Database()
    db.insert_product(data)
    return data


    m