from tinydb import TinyDB, Query 
from datatime import datetime 
import os 


class Database:
    def __init__(self, db_path = 'data.json'):
        dirname = os.path.dirname(db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        self.db = TinyDB(db_path)
        self.products = self.db.table("Products ")

    def insert_product(self, product_data):
        product_data['creted_at'] = datetime.now().isoformat()
        return self.products.insert(product_data)

    
    def get_product(self, asin):
        Product = Query()
        return self.products.get(Product.asin == asin)


    def search_products(self, search_critera):
        Product = Query()
        query = None 

        for key, value in search_critera.items():
            if query is None:
                query = (Product[key] == value)
            else:

                query &= (Product[key] == value)