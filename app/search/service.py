from app.orders.models import InsightsOrders, SwiggyOrders
from app.search import repository


def format_search_result(order, platform):
    client=order.client
    return {
        "platform": platform,
        "id": order.id,
        "client_id":order.client_id,
        "client_username":client.username if client else None,
        "client_email":client.email if client else None,
        "customer_name": order.customer_name,
        "order_number": order.order_number,
        "product_name":order.product_name,
        "amount": order.amount,
        "status": order.status,
        "order_date": order.order_date,
    }


def search_all_orders(db, query: str,client_id:int |None=None):
    query = query.strip()

    if not query:
        return []

    if query.lower() == "swiggy":
        return [
            format_search_result(order, "Swiggy")
            for order in repository.get_all(db, SwiggyOrders,client_id=client_id)
        ]

    if query.lower() == "insights":
        return [
            format_search_result(order, "Insights")
            for order in repository.get_all(db, InsightsOrders,client_id=client_id)
        ]

    results = [
        format_search_result(order, "Swiggy")
        for order in repository.search(db, SwiggyOrders, query,client_id=client_id)
    ]
    results.extend(
        format_search_result(order, "Insights")
        for order in repository.search(db, InsightsOrders, query,client_id=client_id)
    )

    return results
