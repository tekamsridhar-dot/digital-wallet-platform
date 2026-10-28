#                            Digital Wallet Platform

## Project Overview

The **Digital Wallet Platform** is a backend application built using Python and FastAPI that provides wallet management, financial transactions, authentication, authorization, transaction tracking, and security monitoring.

The platform allows users to manage digital wallets, transfer funds between wallets, make simulated deposits, request refunds, and view transaction records. It also includes role-based access control, audit logging, notifications, and transaction risk assessment.

## Features

### 1. Authentication and Authorization
- User registration and login.
- JWT-based authentication.
- Password hashing.
- Role-based access control.
- Roles include Super Admin, Admin, Support Agent, and Customer.

### 2. Wallet Management
- Create and manage wallets.
- View wallet information.
- Track wallet balances.
- Freeze and unfreeze wallets.
- Validate wallet status before financial operations.

### 3. Deposit Management
- Simulated wallet deposits.
- Deposit reference number generation.
- Wallet balance updates.
- Deposit transaction history.
- Audit logging and notifications.

### 4. Fund Transfers
- Transfer funds between wallets.
- Validate sender and receiver wallets.
- Check wallet status and currency compatibility.
- Prevent transfers exceeding the available balance.
- Record transactions and ledger entries.
- Idempotency support to help prevent duplicate transfers.

### 5. Refund Management
- Submit refund requests for eligible transactions.
- Validate refund amounts.
- Prevent requests exceeding the refundable amount.
- Track refund status.
- Record refund requests for auditing.

### 6. Transaction Ledger
- Maintain transaction records.
- Track balances before and after financial operations.
- Store transaction references and descriptions.
- Support financial reconciliation and auditing.

### 7. Notifications
- Notify users about deposits and transfers.
- Notify users about incoming funds.
- Provide notifications for supported financial events.

### 8. Audit Logging
- Record important system and financial activities.
- Track actions performed by users.
- Store entity references and additional details.
- Support accountability and auditing.

### 9. Risk Assessment
- Evaluate transactions using configurable risk rules.
- Detect high-value transactions.
- Identify unusual transaction frequency.
- Monitor frequent outgoing transfers.
- Flag transactions that require review.

### 10. Dashboards
- Administrative dashboard.
- Support dashboard.
- Transaction and risk monitoring, according to configured dashboard functionality.

## Technology Stack

| Technology        | Purpose |
|---|---|
| Python            | Backend programming |
| FastAPI           | REST API development |
| SQLAlchemy        | ORM and database operations |
| PostgreSQL        | Relational database |
| Pydantic          | Request validation and response schemas |
| JWT               | Authentication tokens |
| Alembic           | Database migrations |
| Pytest            | Automated testing |
| Uvicorn           | ASGI application server |
| Git and GitHub    | Version control |

## Project Structure

```text
digital-wallet-platform/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   ├── services/
│   └── core/
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   └── test_error_handlers.py
├── alembic/
│   └── versions/
├── alembic.ini
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

*Note: The structure above is illustrative. Keep the directory names consistent with your actual repository.*

## Installation and Setup

### Prerequisites

Install the following before running the application:

- Python 3.12 or another version supported by your dependencies.
- PostgreSQL.
- Git.

### Step 1: Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd digital-wallet-platform
```

Replace the placeholder with your actual GitHub repository URL.

### Step 2: Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

For Git Bash:

```bash
source .venv/Scripts/activate
```

### Step 3: Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure environment variables

Create a local `.env` file based on `.env.example`.

Configure the required values for your environment, including:

- Database connection URL.
- JWT secret key.
- JWT algorithm.
- Access-token expiration.
- Other settings required by your application.

Never commit real passwords, database credentials, or secret keys to GitHub.

### Step 5: Configure the database

Create a PostgreSQL database for the project and configure the database URL in your environment settings.

Example format:

```env
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/digital_wallet
```

Replace the example credentials and database name with your local configuration.

### Step 6: Apply database migrations

If your project uses Alembic migrations, run:

```bash
alembic upgrade head
```

Ensure your database configuration is correct before running migrations.

### Step 7: Start the application

```bash
uvicorn app.main:app --reload
```

The local API will normally be available at:

```text
http://127.0.0.1:8000
```

## API Documentation

Once the application is running, open the interactive Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

Alternative documentation:

```text
http://127.0.0.1:8000/redoc
```

The available endpoints depend on the routers registered in your application.

## Testing

Run the complete test suite:

```bash
python -m pytest
```

Run tests with concise output:

```bash
python -m pytest -q
```

Run a specific test file:

```bash
python -m pytest -q tests/test_health.py
```

Ensure that the test database and environment variables are configured correctly before running tests.

## Database Design

The database design includes entities for user management, wallets, balances, financial transactions, transfers, deposits, refunds, ledger entries, notifications, audit logs, suspicious transactions, and idempotency records.

Primary keys and foreign keys maintain relationships between the entities. Database constraints and transaction management help protect data integrity.

Refer to the project's database ER diagram for the visual representation of the relationships.

## Security Considerations

- Passwords should be stored using secure password hashing.
- Protected endpoints should require valid authentication.
- Authorization should be enforced at the service or endpoint level.
- Financial operations should use database transactions.
- Idempotency keys should be validated and stored with appropriate uniqueness constraints.
- Sensitive configuration values should be kept outside source control.
- Audit logs should record relevant security and financial events.
- Production deposits should be credited only after confirmation from a trusted payment provider.

## Important Disclaimer

This project is intended for learning, development, and demonstration purposes. Deposits implemented as simulated operations do not represent actual payments.

The application should undergo security testing, financial reconciliation testing, concurrency testing, and operational review before being used with real funds.

## Future Enhancements

- Integration with a real payment gateway.
- Two-factor authentication.
- Transaction limits and configurable fraud rules.
- Refund approval and processing workflows.
- Scheduled transaction reconciliation.
- Improved monitoring and alerting.
- Docker-based deployment and CI/CD automation.
- Expanded automated unit and integration tests.

## Author

**Digital Wallet Platform — Backend Development Project**

Built with Python, FastAPI, SQLAlchemy, and PostgreSQL.
