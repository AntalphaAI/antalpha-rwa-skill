---
name: antalpha-rwa
description: DeFi investment skill for AI agents. Invest in Web3 RWA products with BTC-backed over-collateralized lending on Ethereum. Query real-time DeFi yields, generate EIP-681 payment links for on-chain subscriptions, and track crypto investments. Agent-friendly crypto wealth management with zero custody. Supports Ethereum chain with USDT stablecoin.
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

# Query orders by wallet address
python3 scripts/rwa_client.py orders --address 0x...

# Generate payment link
python3 scripts/rwa_client.py subscribe --amount 100

# Calculate returns
python3 scripts/rwa_client.py calc --amount 1000
```

## Commands

| Command | Description |
|---------|-------------|
| `products` | Query available products from MCP API |
| `orders --address <wallet>` | Query orders by wallet address |
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

## FAQ

### What is "AI AntAlpha"?

AI Antalpha is an "AI Agent Balance Management" product we launched, providing AI-powered digital financial services. Users can query product information through the AI Agent interface, enabling automated allocation of idle crypto assets, letting the agent "earn for you."

### How are product returns calculated?

Returns are calculated using simple interest with the formula: **Investment Principal × Expected Annual Yield / 365 × Actual Holding Days**.

- If subscribed before the product start date, the actual holding days are calculated from the product start date to the product end date.
- If subscribed on or after the product start date, the actual holding days are calculated from the actual subscription date (T+0) to the product end date.

Interest starts accruing on the day of successful subscription with no additional verification period, maximizing capital efficiency.

**Note:** Investments below the minimum amount will not generate interest.

### What is the underlying asset? How is fund safety ensured?

The underlying asset is BTC over-collateralized institutional lending. All borrowing institutions have undergone Antalpha's evaluation and due diligence.

The initial LTV (Loan-to-Value) of the lending assets is only 60%, providing ample buffer for BTC price volatility. Reasonable margin call and liquidation lines are established, with 24/7 monitoring of LTV changes to maximize fund safety.

### Are there third-party audit reports or other information disclosures?

You can query collateral status in real-time through the collateral management address disclosed in the product information.

### Why must I use a "self-custody wallet"? Can I transfer directly from an exchange?

**No.** When the product repays principal and interest, the system returns funds to the original transfer address. Since exchange deposit addresses are typically dynamic or belong to the exchange's main account, if you transfer directly from an exchange, the return payment will go to the exchange's account, and you may not be able to retrieve the funds.

### How do I confirm a successful subscription after transferring to the Ethereum receiving address?

You can consult the AI Agent customer service for the latest order status, or query the MCP server.

### How do I redeem when the product matures?

Upon product maturity, principal and interest will be automatically returned to your investment wallet (original path) on T+1, without any user action required. Current products do not support early redemption. Once subscription is completed, funds are locked until the maturity date.

## Requirements

Python 3.8+ with standard library (no additional dependencies).
