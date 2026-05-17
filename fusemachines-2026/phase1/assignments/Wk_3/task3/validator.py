def validator(query: str):
    block = ["DELETE", "DROP", "CREATE", "ALTER", "INSERT", "UPDATE"]
    query_upper = query.strip().upper()

    for keyword in block:
        if keyword in query_upper:
            raise ValueError(f"Blocked query: {keyword} not allowed")
