import os

from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SCHEMA = """
- productlines ("productLine", "textDescription", "htmlDescription", "image")
- products ("productCode", "productName", "productLine", "productScale", "productVendor", "productDescription", "quantityInStock", "buyPrice", "MSRP")
- offices ("officeCode", "city", "phone", "addressLine1", "addressLine2", "state", "country", "postalCode", "territory")
- employees ("employeeNumber", "lastName", "firstName", "extension", "email", "officeCode", "reportsTo", "jobTitle")
- customers ("customerNumber", "customerName", "contactLastName", "contactFirstName", "phone", "addressLine1", "addressLine2", "city", "state", "postalCode", "country", "salesRepEmployeeNumber", "creditLimit")
- payments ("customerNumber", "checkNumber", "paymentDate", "amount")
- orders ("orderNumber", "orderDate", "requiredDate", "shippedDate", "status", "comments", "customerNumber")
- orderdetails ("orderNumber", "productCode", "quantityOrdered", "priceEach", "orderLineNumber")
"""

def generate_sql(question: str):
    prompt = f"""You are a SQL expert for a PostgreSQL database with these tables:
{SCHEMA}

Generate a correct PostgreSQL SELECT query only.
Use double quotes around column names because they are mixed-case.
No explanation. No markdown. Only SQL.

Question: {question}
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    return response.text.strip()


def fix_sql(question: str, bad_sql: str, error: str):
    prompt = f"""Fix this PostgreSQL query for the given schema.
                {SCHEMA}

                Use double quotes around column names because they are mixed-case.
                Return only the fixed SELECT query. No explanation. No markdown.

                Question: {question}
                Bad SQL: {bad_sql}
                Error: {error}
                """

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    return response.text.strip()

def translate_to_nlp(question: str, result: list):
    prompt = f"""Given this question and data result, write a 1-2 sentence natural language summary.

                Question: {question}
                Result: {result}

                Write only the summary, nothing else."""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    return response.text.strip()


