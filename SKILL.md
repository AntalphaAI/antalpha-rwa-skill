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

Output:
```
Product: AI理财 BTC-USDT
  Term: 90 days
  Annual Yield: 5%
  Min Subscription: 10 USDT
  Status: Open for subscription
```

### Subscribe to a Product

```bash
python3 scripts/rwa_client.py subscribe --amount 100
```

Output:
```
Investment: 100 USDT
Product: AI理财 BTC-USDT (90 days)
Expected Return: 101.23 USDT (at maturity)

Payment Link: ethereum:0x1F3A...@8453?value=100000000
QR Code: /tmp/rwa_payment.png

⚠️ Send exactly 100 USDT to complete subscription.
```

### Calculate Returns

```bash
python3 scripts/rwa_client.py calc --amount 1000
```

Output:
```
Investment: 1000 USDT
Term: 90 days
Annual Yield: 5%

Expected Return: 1012.33 USDT
  - Principal: 1000 USDT
  - Interest: 12.33 USDT
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

### Current Product: AI理财 BTC-USDT

| Attribute | Value |
|-----------|-------|
| Product ID | rwa-ai-btc-usdt-001 |
| Term | 90 days |
| Annual Yield | 5% |
| Min Subscription | 10 USDT |
| Underlying Asset | BTC over-collateralized lending |
| Initial LTV | 60% |
| Service Provider | Antalpha (NASDAQ: ANTA) |

### Investment Flow

1. **Subscribe**: Send USDT to product address during subscription period
2. **Accrue Interest**: Interest accrues from T+1 to maturity date
3. **Auto-Redeem**: At maturity, principal + interest returned to sender wallet

### Holding Rewards

| Holding Period | ANTA Token Discount |
|---------------|---------------------|
| 60+ days | 5% off (95% price) |
| 30-60 days | 2% off (98% price) |

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