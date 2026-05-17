import os 
from google import genai


client = genai.Client()


# send prompt 
response = client.models.generate_content(
    model = "gemini-2.5-flash"
    prompt = '''You are a SQL expert. Given this database schema and question, generate a PostgreSQL query.
                Question: List all products
                Intent: Retrieve all products
                Tables: products
                Columns: *
                Filters: None
                Joins: None
               Generate only the SQL query, nothing else.'''
)

print(response.text)