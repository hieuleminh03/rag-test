# Sample API Documentation

## Payment Processing API

### Overview
This API handles payment processing for various financial transactions.

### Endpoints

#### POST /api/v1/payment/process
Process a payment transaction.

**Request Body:**
```json
{
  "amount": 100.00,
  "currency": "USD",
  "customer_id": "12345",
  "payment_method": "credit_card"
}
```

**Response:**
```json
{
  "transaction_id": "txn_abc123",
  "status": "success",
  "amount": 100.00,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Error Handling
- 400 Bad Request: Invalid input data
- 401 Unauthorized: Invalid API key
- 500 Internal Server Error: System error

### Business Rules
1. Minimum transaction amount: $1.00
2. Maximum transaction amount: $10,000.00
3. Supported currencies: USD, EUR, GBP
4. Transaction timeout: 30 seconds