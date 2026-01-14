# Backend API Specification

## Base URL
`http://localhost:3000`

## User Endpoints

### Create or Get User Wallet
**Important:** This endpoint has a side effect - it also creates user subwallets.

```
GET /user/{user_telegram_id}/wallet
```
**Response:**
```json
{
  "wallet_dto": {
    "wallet_id": "uuid",
    "evm_address": "0x..."
  }
}
```

### Check Wallet Balance
```
GET /user/{user_telegram_id}/wallet/balance
```
**Response:**
```json
{
  "raw": "1000000000000000000",
  "ui": "1.0"
}
```

## Token Endpoints

### Get Liquidity Pools
**Note:** Works only for mainnet cluster. Testnet pools are not supported.

```
GET /token/{token_ca}/pools
```
**Response:**
```json
{
  "pools": {
    "pairs": [
      {
        "labels": ["v2"],
        ...
      }
    ]
  }
}
```

### Check if Token is Supported
**Important:** 
- For mainnet: checks DexScreener pools and runs swap simulation
- For testnet: always returns `true` if token CA is valid (skips DexScreener check)

```
GET /token/{token_ca}/is-supported
```
**Response:**
```json
{
  "is_supported": true
}
```

## Price Endpoints

### Convert BNB to USD
Uses Pyth/Hermes price oracle for conversion.

```
POST /price/bnb-to-usd
```
**Request Body:**
```json
{
  "amount_wei": "1000000000000000000"
}
```
**Response:**
```json
{
  "amount_usd": 300.50
}
```

## Bot Session Endpoints

### Start Session
**Important:** This method is **idempotent**. If called twice while any session exists, it does nothing and returns `created: false`. Otherwise creates a new session.

```
POST /bot/session/run
```
**Request Body:**
```json
{
  "user_telegram_id": 123456789,
  "pump_amount_wei": "1000000000000000000",
  "swap_amount_wei": "100000000000000000",
  "delay_millis": 1000,
  "token_ca": "0x..."
}
```
**Response:**
```json
{
  "created": true
}
```
- `created: true` - new session was created
- `created: false` - session already exists and is active

### Session Status
**Important:** Used for long-polling. Checks the status of the current active session.

```
POST /bot/session/status
```
**Request Body:**
```json
{
  "user_telegram_id": 123456789
}
```
**Response:**
```json
{
  "status": "Running" | "Paused" | "Success" | "Failed"
}
```

### Pause Session
```
POST /bot/session/pause
```
**Request Body:**
```json
{
  "user_telegram_id": 123456789
}
```
**Response:** `200 OK` (empty body)

### Resume Session
```
POST /bot/session/resume
```
**Request Body:**
```json
{
  "user_telegram_id": 123456789
}
```
**Response:** `200 OK` (empty body)

### Set Delay
Updates delay between swaps in running session.

```
PUT /bot/session/delay
```
**Request Body:**
```json
{
  "user_telegram_id": 123456789,
  "delay_millis": 2000
}
```
**Response:** `200 OK` (empty body)

### Set Swap Amount
Updates swap amount in running session.

```
PUT /bot/session/swap-amount
```
**Request Body:**
```json
{
  "user_telegram_id": 123456789,
  "swap_amount_wei": "200000000000000000"
}
```
**Response:** `200 OK` (empty body)

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "error": "Error description"
}
```

Common HTTP status codes:
- `400 Bad Request` - Invalid input (e.g., invalid address, invalid amount)
- `404 Not Found` - Resource not found (e.g., session not found, user wallet not found)
- `500 Internal Server Error` - Server error
