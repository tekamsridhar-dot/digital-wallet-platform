from fastapi import FastAPI
from app.routers import (auth,wallets,deposits,withdrawals,transfers,refunds,risk,notifications,transactions,
                         dashboard,audit)
from fastapi import FastAPI
from app.core.error_handlers import register_exception_handlers

app=FastAPI(title="Digital Wallet & Transaction Processing Platform",
            description="""Digital Wallet for financial transaction management.
            <br><br><br> Created by: </b> Sridhar Tekam""")

app.include_router(auth.router)
app.include_router(wallets.router)
app.include_router(deposits.router)
app.include_router(withdrawals.router)
app.include_router(transfers.router)
app.include_router(refunds.router)
app.include_router(risk.router)
app.include_router(notifications.router)
app.include_router(transactions.router)
app.include_router(dashboard.router)
app.include_router(audit.router)

@app.get("/health")
def health_check():
    return {"status":"healthy"}


register_exception_handlers(app)