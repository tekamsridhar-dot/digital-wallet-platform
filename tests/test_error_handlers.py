from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.error_handlers import register_exception_handlers
from app.core.exceptions import AppException


app = FastAPI()
register_exception_handlers(app)


@app.get("/test-business-error")
def business_error():
    raise AppException(
        status_code=409,
        code="WALLET_FROZEN",
        message="Transactions are not allowed on a frozen wallet.",
    )


@app.get("/test-validation")
def validation_error(amount: int):
    return {"amount": amount}


def test_business_error_format():
    client = TestClient(app)

    response = client.get("/test-business-error")

    assert response.status_code == 409
    assert response.json() == {
        "success": False,
        "error": {
            "code": "WALLET_FROZEN",
            "message": (
                "Transactions are not allowed on a frozen wallet."
            ),
        },
    }


def test_validation_error_format():
    client = TestClient(app)

    response = client.get("/test-validation?amount=invalid")

    assert response.status_code == 422
    body = response.json()

    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in body["error"]


def test_app_exception_response():
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/test-error")
    def test_error():
        raise AppException(
            400,
            "INSUFFICIENT_BALANCE",
            "Insufficient wallet balance.",
        )

    client = TestClient(test_app)
    response = client.get("/test-error")

    assert response.status_code == 400
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "INSUFFICIENT_BALANCE"