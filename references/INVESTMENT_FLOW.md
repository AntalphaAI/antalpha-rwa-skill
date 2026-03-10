# Investment Flow

## Overview

This document describes the investment flow for Antalpha Prime RWA products.

## Step-by-Step Process

### 1. Query Products

```
User: "What RWA products are available?"
Agent: Calls rwa products
Output: List of products with yields, terms, minimums
```

### 2. Calculate Returns

```
User: "If I invest 1000 USDT, how much will I get?"
Agent: Calls rwa calc --amount 1000
Output: Expected return at maturity
```

### 3. Subscribe

```
User: "Help me invest 100 USDT"
Agent: Calls rwa subscribe --amount 100
Output: Payment link + QR code
```

### 4. Payment

User scans QR code or clicks payment link in their wallet app.

Wallet shows:
- Recipient: Product receiving address
- Amount: 100 USDT
- Network: Base

User confirms transaction.

### 5. Confirmation

```
User: "I sent the payment, TX hash is 0xabc..."
Agent: Calls rwa record --tx 0xabc... --amount 100
Output: Investment recorded
```

### 6. Maturity

At maturity date (e.g., 90 days later):
- Principal + interest automatically returned to sender wallet
- No action required from user

## Investment Record

The skill can track investments locally:

```
~/.antalpha-rwa/investments.json
```

Contents:
```json
[
  {
    "tx_hash": "0xabc...",
    "amount": 100,
    "product_name": "AI理财 BTC-USDT",
    "invested_at": "2026-03-09T15:00:00",
    "maturity_date": "2026-06-07"
  }
]
```

## Notes

- Funds are locked until maturity - no early redemption
- Returns are automatically sent to the original wallet
- Investment confirmed on-chain - no additional registration needed