#!/usr/bin/env python3
"""
Antalpha Prime RWA Investment Client

Query RWA investment products and generate subscription payment links.

Usage:
    python3 rwa_client.py products
    python3 rwa_client.py subscribe --amount 100
    python3 rwa_client.py calc --amount 1000
    python3 rwa_client.py record --tx <hash> --amount <usdt>
    python3 rwa_client.py list
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR.parent / "references" / "mcp.json"
DATA_DIR = Path.home() / ".antalpha-rwa"
INVESTMENTS_FILE = DATA_DIR / "investments.json"

# USDC contract address on Base
USDC_CONTRACT = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"

# Default values (overridden by config file if exists)
DEFAULT_MCP_URL = "https://mcp.prime.antalpha.com/mcp"
DEFAULT_CHAIN_ID = 8453  # Base
DEFAULT_TIMEOUT = 30


def load_config() -> Dict[str, Any]:
    """
    Load configuration from references/mcp.json.
    Returns default values if file doesn't exist.
    """
    config = {
        "mcp_url": DEFAULT_MCP_URL,
        "default_chain_id": DEFAULT_CHAIN_ID,
        "default_network": "base",
        "timeout_seconds": DEFAULT_TIMEOUT
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load config file: {e}")
    
    return config


# Load configuration at module level
_CONFIG = load_config()
MCP_URL = _CONFIG["mcp_url"]
DEFAULT_CHAIN_ID = _CONFIG["default_chain_id"]

# ============================================================================
# MCP Client
# ============================================================================

def call_mcp_tool(tool_name: str, arguments: dict = None) -> Dict[str, Any]:
    """
    Call Antalpha Prime MCP API.
    
    Args:
        tool_name: Name of the MCP tool to call
        arguments: Tool arguments (optional)
    
    Returns:
        Parsed JSON response
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {}
        },
        "id": 1
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "antalpha-rwa-client/1.0"
    }
    
    request = Request(
        MCP_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    
    try:
        with urlopen(request, timeout=30) as response:
            content = response.read().decode('utf-8')
            
            # Parse SSE format: "event: message\ndata: {...}"
            lines = content.strip().split('\n')
            for line in lines:
                if line.startswith('data: '):
                    data_str = line[6:]  # Remove "data: " prefix
                    result = json.loads(data_str)
                    
                    if 'error' in result:
                        raise Exception(f"MCP Error: {result['error']}")
                    
                    return result.get('result', {})
            
            raise Exception("No data in SSE response")
            
    except HTTPError as e:
        raise Exception(f"HTTP Error {e.code}: {e.reason}")
    except URLError as e:
        raise Exception(f"URL Error: {e.reason}")
    except json.JSONDecodeError as e:
        raise Exception(f"JSON Decode Error: {e}")


def get_products() -> List[Dict[str, Any]]:
    """Get list of RWA investment products."""
    result = call_mcp_tool("list_products")
    
    # Extract products from structuredContent
    content = result.get('content', [])
    structured = result.get('structuredContent', {})
    
    if structured and 'products' in structured:
        return structured['products']
    
    # Fallback: parse from text content
    for item in content:
        if item.get('type') == 'text':
            try:
                return json.loads(item['text'])
            except json.JSONDecodeError:
                pass
    
    return []


def get_active_product() -> Optional[Dict[str, Any]]:
    """Get the currently active product (first product in list)."""
    products = get_products()
    if products:
        return products[0]
    return None

# ============================================================================
# Payment Link Generation
# ============================================================================

def generate_payment_link(
    receiving_address: str,
    amount_usdt: float,
    chain_id: int = DEFAULT_CHAIN_ID
) -> Dict[str, Any]:
    """
    Generate EIP-681 payment link for USDT subscription.
    
    Args:
        receiving_address: Product receiving address
        amount_usdt: Amount in USDT
        chain_id: Chain ID (default: Base = 8453)
    
    Returns:
        Dict with payment link and details
    """
    # USDT has 6 decimals on Base
    amount_raw = int(amount_usdt * 1_000_000)
    
    # EIP-681 format for ERC-20 token transfer (USDC on Base)
    # Format: ethereum:<token_contract>@<chain_id>/transfer?address=<recipient>&uint256=<amount>
    eip681_link = f"ethereum:{USDC_CONTRACT}@{chain_id}/transfer?address={receiving_address}&uint256={amount_raw}"
    
    # MetaMask deep link for ERC-20 transfer
    metamask_link = f"https://metamask.app.link/send/{USDC_CONTRACT}@{chain_id}/transfer?address={receiving_address}&uint256={amount_raw}"
    
    return {
        "eip681": eip681_link,
        "metamask": metamask_link,
        "receiving_address": receiving_address,
        "usdc_contract": USDC_CONTRACT,
        "amount_usdt": amount_usdt,
        "amount_raw": amount_raw,
        "chain_id": chain_id
    }


def generate_qr_code(link: str, output_path: str) -> bool:
    """Generate QR code using npx qrcode."""
    try:
        result = subprocess.run(
            ["npx", "qrcode", "-t", "png", "-o", output_path, link],
            capture_output=True,
            timeout=30
        )
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception:
        return False

# ============================================================================
# Investment Calculations
# ============================================================================

def calculate_returns(
    amount: float,
    annual_yield: float,
    term_days: int
) -> Dict[str, float]:
    """
    Calculate expected investment returns.
    
    Args:
        amount: Investment amount in USDT
        annual_yield: Annual yield (e.g., 0.05 for 5%)
        term_days: Investment term in days
    
    Returns:
        Dict with principal, interest, and total
    """
    interest = amount * annual_yield * (term_days / 365)
    total = amount + interest
    
    return {
        "principal": amount,
        "interest": round(interest, 2),
        "total": round(total, 2),
        "annual_yield": annual_yield,
        "term_days": term_days
    }

# ============================================================================
# Investment Records
# ============================================================================

def ensure_data_dir():
    """Ensure data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_investments() -> List[Dict[str, Any]]:
    """Load investment records from local file."""
    ensure_data_dir()
    if INVESTMENTS_FILE.exists():
        with open(INVESTMENTS_FILE, 'r') as f:
            return json.load(f)
    return []


def save_investments(investments: List[Dict[str, Any]]):
    """Save investment records to local file."""
    ensure_data_dir()
    with open(INVESTMENTS_FILE, 'w') as f:
        json.dump(investments, f, indent=2)


def record_investment(tx_hash: str, amount: float, product_id: str = None) -> Dict[str, Any]:
    """
    Record an investment.
    
    Args:
        tx_hash: Transaction hash
        amount: Investment amount in USDT
        product_id: Product ID (optional)
    
    Returns:
        Recorded investment record
    """
    product = get_active_product()
    
    record = {
        "tx_hash": tx_hash,
        "amount": amount,
        "product_id": product_id or (product.get('id') if product else None),
        "product_name": product.get('name') if product else None,
        "invested_at": datetime.now().isoformat(),
        "term_days": product.get('productTerm') if product else None,
        "expected_yield": product.get('expectedYieldAnnual') if product else None,
        "maturity_date": product.get('maturityDate') if product else None
    }
    
    investments = load_investments()
    investments.append(record)
    save_investments(investments)
    
    return record

# ============================================================================
# CLI Commands
# ============================================================================

def cmd_products(args):
    """Handle 'products' command."""
    try:
        products = get_products()
        
        if args.json:
            print(json.dumps(products, indent=2))
            return 0
        
        if not products:
            print("No products available.")
            return 0
        
        print("\n" + "=" * 60)
        print("RWA Investment Products")
        print("=" * 60 + "\n")
        
        for i, p in enumerate(products, 1):
            yield_pct = p.get('expectedYieldAnnual', 0) * 100
            term = p.get('productTerm', 'N/A')
            min_sub = p.get('minSubscriptionUsdt', 'N/A')
            status = "Open" if p.get('startDate') else "Pending"
            
            print(f"{i}. {p.get('name', 'Unknown')}")
            print(f"   ID: {p.get('id', 'N/A')}")
            print(f"   Term: {term} days")
            print(f"   Annual Yield: {yield_pct:.2f}%")
            print(f"   Min Subscription: {min_sub} USDT")
            print(f"   Status: {status}")
            print(f"   Receiving Address: {p.get('receivingAddress', 'N/A')}")
            print()
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_subscribe(args):
    """Handle 'subscribe' command."""
    if args.amount < 10:
        print("Error: Minimum subscription is 10 USDT")
        return 1
    
    try:
        product = get_active_product()
        
        if not product:
            print("Error: No active product available")
            return 1
        
        min_sub = product.get('minSubscriptionUsdt', 10)
        if args.amount < min_sub:
            print(f"Error: Minimum subscription is {min_sub} USDT")
            return 1
        
        receiving_address = product.get('receivingAddress')
        if not receiving_address:
            print("Error: Product has no receiving address")
            return 1
        
        # Generate payment link
        payment = generate_payment_link(receiving_address, args.amount)
        
        # Calculate returns
        returns = calculate_returns(
            args.amount,
            product.get('expectedYieldAnnual', 0.05),
            product.get('productTerm', 90)
        )
        
        # Generate QR if requested
        qr_path = None
        if args.qr:
            if generate_qr_code(payment['metamask'], args.qr):
                qr_path = args.qr
        
        if args.json:
            output = {
                "success": True,
                "product": {
                    "id": product.get('id'),
                    "name": product.get('name'),
                    "term_days": product.get('productTerm'),
                    "annual_yield": product.get('expectedYieldAnnual')
                },
                "investment": {
                    "amount": args.amount,
                    "expected_return": returns['total'],
                    "expected_interest": returns['interest']
                },
                "payment": payment,
                "qr_path": qr_path
            }
            print(json.dumps(output, indent=2))
            return 0
        
        # Human-readable output
        print("\n" + "=" * 60)
        print("Subscription Payment Link")
        print("=" * 60)
        print(f"\nProduct: {product.get('name')}")
        print(f"Term: {product.get('productTerm')} days")
        print(f"Annual Yield: {product.get('expectedYieldAnnual', 0) * 100:.2f}%")
        print(f"\nInvestment: {args.amount} USDT")
        print(f"Expected Return: {returns['total']} USDT (at maturity)")
        print(f"  - Principal: {returns['principal']} USDT")
        print(f"  - Interest: {returns['interest']} USDT")
        print(f"\n" + "-" * 60)
        print("Payment Link")
        print("-" * 60)
        print(f"\nEIP-681: {payment['eip681']}")
        print(f"\nMetaMask: {payment['metamask']}")
        print(f"\nReceiving Address: {receiving_address}")
        print(f"Amount (raw): {payment['amount_raw']}")
        
        if qr_path:
            print(f"\nQR Code: {qr_path}")
        
        print(f"\n" + "-" * 60)
        print("⚠️  Send exactly {0} USDT to complete subscription.".format(args.amount))
        print("-" * 60 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_calc(args):
    """Handle 'calc' command."""
    try:
        product = get_active_product()
        
        if not product:
            print("Error: No active product available")
            return 1
        
        returns = calculate_returns(
            args.amount,
            product.get('expectedYieldAnnual', 0.05),
            product.get('productTerm', 90)
        )
        
        if args.json:
            output = {
                "product_name": product.get('name'),
                "investment": args.amount,
                "annual_yield": product.get('expectedYieldAnnual'),
                "term_days": product.get('productTerm'),
                "returns": returns
            }
            print(json.dumps(output, indent=2))
            return 0
        
        print("\n" + "=" * 60)
        print("Investment Calculator")
        print("=" * 60)
        print(f"\nProduct: {product.get('name')}")
        print(f"Term: {product.get('productTerm')} days")
        print(f"Annual Yield: {product.get('expectedYieldAnnual', 0) * 100:.2f}%")
        print(f"\nInvestment: {args.amount} USDT")
        print(f"\nExpected Return: {returns['total']} USDT")
        print(f"  - Principal: {returns['principal']} USDT")
        print(f"  - Interest: {returns['interest']} USDT")
        print("\n" + "=" * 60 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_record(args):
    """Handle 'record' command."""
    try:
        record = record_investment(args.tx, args.amount)
        
        print("\n" + "=" * 60)
        print("Investment Recorded")
        print("=" * 60)
        print(f"\nTX Hash: {record['tx_hash']}")
        print(f"Amount: {record['amount']} USDT")
        print(f"Product: {record.get('product_name', 'N/A')}")
        print(f"Invested At: {record['invested_at']}")
        if record.get('maturity_date'):
            print(f"Maturity Date: {record['maturity_date']}")
        print("\n" + "=" * 60 + "\n")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_list(args):
    """Handle 'list' command."""
    try:
        investments = load_investments()
        
        if args.json:
            print(json.dumps(investments, indent=2))
            return 0
        
        if not investments:
            print("\nNo investment records found.")
            print("Use 'record --tx <hash> --amount <usdt>' to add a record.\n")
            return 0
        
        print("\n" + "=" * 60)
        print("Investment Records")
        print("=" * 60 + "\n")
        
        for i, inv in enumerate(investments, 1):
            print(f"{i}. TX: {inv.get('tx_hash', 'N/A')[:16]}...")
            print(f"   Amount: {inv.get('amount', 'N/A')} USDT")
            print(f"   Product: {inv.get('product_name', 'N/A')}")
            print(f"   Invested: {inv.get('invested_at', 'N/A')}")
            if inv.get('maturity_date'):
                print(f"   Maturity: {inv['maturity_date']}")
            print()
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Antalpha Prime RWA Investment Client",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # products command
    products_parser = subparsers.add_parser("products", help="Query available products")
    products_parser.add_argument("--json", action="store_true", help="Output as JSON")
    products_parser.set_defaults(func=cmd_products)
    
    # subscribe command
    subscribe_parser = subparsers.add_parser("subscribe", help="Generate payment link")
    subscribe_parser.add_argument("--amount", type=float, required=True, help="Investment amount in USDT")
    subscribe_parser.add_argument("--qr", type=str, help="Generate QR code and save to path")
    subscribe_parser.add_argument("--json", action="store_true", help="Output as JSON")
    subscribe_parser.set_defaults(func=cmd_subscribe)
    
    # calc command
    calc_parser = subparsers.add_parser("calc", help="Calculate investment returns")
    calc_parser.add_argument("--amount", type=float, required=True, help="Investment amount in USDT")
    calc_parser.add_argument("--json", action="store_true", help="Output as JSON")
    calc_parser.set_defaults(func=cmd_calc)
    
    # record command
    record_parser = subparsers.add_parser("record", help="Record an investment")
    record_parser.add_argument("--tx", type=str, required=True, help="Transaction hash")
    record_parser.add_argument("--amount", type=float, required=True, help="Investment amount in USDT")
    record_parser.set_defaults(func=cmd_record)
    
    # list command
    list_parser = subparsers.add_parser("list", help="List investment records")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    list_parser.set_defaults(func=cmd_list)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())