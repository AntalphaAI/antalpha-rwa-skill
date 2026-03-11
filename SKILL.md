---
name: antalpha-rwa
description: Invest in Antalpha Prime RWA products backed by BTC over-collateralized lending. Query real-time products, generate EIP-681 payment links, and track investments. Zero custody, agent-friendly, no configuration required.
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

- **Query products** - Fetch real-time RWA product offerings
- **Generate payment links** - EIP-681 compliant USDT subscription links
- **Calculate returns** - Estimate investment returns based on current rates
- **Track investments** - Local investment records (optional)

## Quick Start

```bash
# Query products (real-time from server)
python3 scripts/rwa_client.py products

# Generate payment link
python3 scripts/rwa_client.py subscribe --amount 100

# Calculate returns
python3 scripts/rwa_client.py calc --amount 1000
```

## Commands

| Command | Description |
|---------|-------------|
| `products` | Query available products from MCP API |
| `subscribe --amount <usdt>` | Generate EIP-681 payment link |
| `calc --amount <usdt>` | Calculate expected returns |
| `record --tx <hash> --amount <usdt>` | Save investment record |
| `list` | List saved investments |

All commands support `--json` for machine-readable output.

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

Products are fetched in real-time from the MCP API. Use `products` command to see current offerings.

**Underlying Asset:** BTC over-collateralized lending  
**Investment Currency:** USDT  
**Settlement:** Auto-redemption at maturity

## Risk Notice

- **Market Risk:** BTC price volatility affects collateral coverage
- **Liquidity Risk:** Funds locked until maturity
- **Returns Not Guaranteed**

**Only invest what you can afford to lose.**

## Security

- No private keys handled
- Payment links are standard EIP-681
- All transactions verified on-chain

## Requirements

Python 3.8+ with standard library (no additional dependencies).