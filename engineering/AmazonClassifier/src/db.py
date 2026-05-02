from datetime import datetime
import os

from tinydb import Query, TinyDB


class Database:
    def __init__(self, db_path="data.json"):
        dirname = os.path.dirname(db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        self.db = TinyDB(db_path)
        self.products = self.db.table("products")

    def insert_product(self, product_data):
        record = dict(product_data)
        record["created_at"] = datetime.now().isoformat()
        return self.products.upsert(record, Query().asin == record.get("asin"))

    def get_product(self, asin):
        return self.products.get(Query().asin == asin)

    def search_products(self, search_criteria):
        Product = Query()
        query = None

        for key, value in search_criteria.items():
            if query is None:
                query = Product[key] == value
            else:
                query &= Product[key] == value

        if query is None:
            return self.products.all()

        return self.products.search(query)
