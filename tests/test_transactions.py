# tests/test_transactions.py

def test_transaction_list_requires_authentication(client):
    response = client.get("/api/transactions")

    assert response.status_code in (401, 403)


def test_transaction_summary_requires_authentication(client):
    response = client.get("/api/transactions/summary")

    assert response.status_code in (401, 403)