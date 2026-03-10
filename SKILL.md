---
name: antalpha-rwa
description: Invest in Antalpha Prime RWA (Real World Asset) products. Query BTC-backed investment opportunities with fixed yields and generate subscription payment links. Zero custody, agent-friendly, no configuration required. Use when user wants to invest in institutional-grade digital asset products.
metadata:
  openclaw:
    requires:
      env: []
    persistence:
      path: ~/.antalpha-rwa/
      files:
        - investments.json: Local investment records (optional)
    security_notes:
      - This skill generates payment links only - never handles private keys
      - Investment involves risk - returns are not guaranteed
      - Funds are locked until maturity - no early redemption
---

# Antalpha Prime RWA Investment Skill

> **Zero custody. Agent-friendly. No configuration.**

## What This Does

- **Query RWA products** - Discover BTC-backed investment opportunities
- **Generate payment links** - EIP-681 compliant subscription links
- **Calculate returns** - Estimate investment returns
- **Track investments** - Local investment records (optional)

## Quick Start

### Query Available Products

```bash
python3 scripts/rwa_client.py products
```

Output (example - actual values from server):
```
Product: AI理财 BTC-USDT
  Term: [from server]
  Annual Yield: [from server]
  Min Subscription: 10 USDT
  Status: Open for subscription
```

### Subscribe to a Product

```bash
python3 scripts/rwa_client.py subscribe --amount 100
```

Output (example):
```
Investment: 100 USDT
Product: AI理财 BTC-USDT
Expected Return: [calculated from server rates]

Payment Link: ethereum:0x1F3A...@8453?value=100000000
QR Code: /tmp/rwa_payment.png

⚠️ Send exactly 100 USDT to complete subscription.
```

### Calculate Returns

```bash
python3 scripts/rwa_client.py calc --amount 1000
```

Output (example - uses server rates):
```
Investment: 1000 USDT
Product: AI理财 BTC-USDT
Term: [from server]
Annual Yield: [from server]

Expected Return: [calculated]
  - Principal: 1000 USDT
  - Interest: [calculated]
```

## Commands

### `products` - Query Product List

```bash
python3 scripts/rwa_client.py products [--json]
```

Returns available RWA investment products with:
- Product name and ID
- Term (days)
- Expected annual yield
- Minimum subscription amount
- Subscription status

### `subscribe` - Generate Payment Link

```bash
python3 scripts/rwa_client.py subscribe --amount <usdt> [--qr <path>]
```

Options:
- `--amount`: Investment amount in USDT (required)
- `--qr`: Generate QR code and save to path
- `--json`: Output as JSON

### `calc` - Calculate Returns

```bash
python3 scripts/rwa_client.py calc --amount <usdt>
```

### `record` - Save Investment Record

```bash
python3 scripts/rwa_client.py record --tx <hash> --amount <usdt>
```

Saves investment to local file for tracking.

### `list` - List Investment Records

```bash
python3 scripts/rwa_client.py list
```

Shows all recorded investments.

## How It Works

```
┌─────────────┐     MCP API      ┌─────────────────┐
│   Agent     │ ───────────────► │ Antalpha Prime  │
│             │  Query Products  │   RWA Platform  │
└─────────────┘                  └─────────────────┘
       │
       │ Generate Payment Link
       ▼
┌─────────────┐                  ┌─────────────────┐
│    User     │ ──── USDT ─────► │  Product Pool   │
│   Wallet    │                  │                 │
└─────────────┘                  └─────────────────┘
```

1. Agent queries products via MCP API
2. User chooses investment amount
3. Agent generates EIP-681 payment link
4. User sends USDT to product address
5. Investment confirmed on-chain

## Product Details

### Available Products

Products are queried in real-time from the MCP API. Use `python3 scripts/rwa_client.py products` to see current offerings.

**Typical Product Features:**
- BTC over-collateralized lending
- Fixed-term investment periods
- Competitive fixed yields
- Minimum subscription: 10 USDT
- Auto-redemption at maturity

> ⚠️ Product parameters (term, yield, status) are dynamic and fetched from the server at query time.

### Investment Flow

1. **Subscribe**: Send USDT to product address during subscription period
2. **Accrue Interest**: Interest accrues from T+1 to maturity date
3. **Auto-Redeem**: At maturity, principal + interest returned to sender wallet

> 💡 For current rewards, rates, and promotions, query the MCP API directly.

## Risk Notice

- **Market Risk**: BTC price volatility affects collateral coverage
- **Liquidity Risk**: Funds locked until maturity, no early redemption
- **Returns Not Guaranteed**: Expected yield is an estimate

**Only invest what you can afford to lose.**

## Security

- ✅ No private keys handled
- ✅ No user funds held
- ✅ Payment links are standard EIP-681
- ✅ All transactions verified on-chain

## Installation

No additional dependencies required. Python 3.8+ with standard library.

For QR code generation (optional):
```bash
# QR code is generated via npx (auto-downloads)
# No installation needed
```

---

**Maintainer**: Web3 Investor Team  
**License**: MIT