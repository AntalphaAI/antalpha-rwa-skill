#!/usr/bin/env python3
"""
Antalpha Prime RWA Investment Client

Query RWA investment products and generate subscription payment links.

Usage:
    python3 rwa_client.py products
    python3 rwa_client.py subscribe --amount 100
    python3 rwa_client.py subscribe --amount 100 --chain ethereum --token USDC
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

# Default values (overridden by config file if exists)
DEFAULT_MCP_URL = "https://mcp.prime.antalpha.com/mcp"
DEFAULT_TIMEOUT = 30
DEFAULT_CHAIN = "ethereum"
DEFAULT_TOKEN = "USDT"


def load_config() -> Dict[str, Any]:
    """
    Load configuration from references/mcp.json.
    Returns default values if file doesn't exist.
    """
    default_config = {
        "mcp_url": DEFAULT_MCP_URL,
        "timeout_seconds": DEFAULT_TIMEOUT,
        "default_chain": DEFAULT_CHAIN,
        "default_token": DEFAULT_TOKEN,
        "chains": {
            "base": {
                "chain_id": 8453,
                "name": "Base",
                "rpc_url": "https://mainnet.base.org/",
                "tokens": {
                    "USDT": {
                        "address": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
                        "decimals": 6,
                        "symbol": "USDT"
                    },
                    "USDC": {
                        "address": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
                        "decimals": 6,
                        "symbol": "USDC"
                    }
                }
            },
            "ethereum": {
                "chain_id": 1,
                "name": "Ethereum",
                "rpc_url": "https://eth.llamarpc.com/",
                "tokens": {
                    "USDT": {
                        "address": "0xdac17f958d2ee523a2206206994597c13d831ec7",
                        "decimals": 6,
                        "symbol": "USDT"
                    },
                    "USDC": {
                        "address": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                        "decimals": 6,
                        "symbol": "USDC"
                    }
                }
            }
        }
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                file_config = json.load(f)
                # Merge with defaults (file config takes precedence)
                for key in file_config:
                    default_config[key] = file_config[key]
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load config file: {e}")
    
    return default_config


# Load configuration at module level
_CONFIG = load_config()
MCP_URL = _CONFIG["mcp_url"]
DEFAULT_CHAIN = _CONFIG.get("default_chain", "base")
DEFAULT_TOKEN = _CONFIG.get("default_token", "USDT")


def get_chain_config(chain_name: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific chain."""
    return _CONFIG.get("chains", {}).get(chain_name.lower())


def get_token_config(chain_name: str, token_symbol: str) -> Optional[Dict[str, Any]]:
    """Get token configuration for a specific chain."""
    chain = get_chain_config(chain_name)
    if chain:
        return chain.get("tokens", {}).get(token_symbol.upper())
    return None

# ============================================================================
# MCP Client
# ============================================================================

# Global session state
_mcp_session_id: Optional[str] = None


def _parse_sse_response(content: str) -> Dict[str, Any]:
    """Parse Server-Sent Events format response."""
    lines = content.strip().split('\n')
    for line in lines:
        if line.startswith('data: '):
            data_str = line[6:]  # Remove "data: " prefix
            result = json.loads(data_str)
            
            if 'error' in result:
                raise Exception(f"MCP Error: {result['error']}")
            
            return result.get('result', {})
    
    raise Exception("No data in SSE response")


def mcp_initialize() -> str:
    """
    Initialize MCP session and get session ID.
    
    Returns:
        Session ID for subsequent calls
    """
    global _mcp_session_id
    
    payload = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "antalpha-rwa-client",
                "version": "1.0"
            }
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
            result = _parse_sse_response(content)
            
            # Extract session ID from HTTP response headers
            session_id = response.headers.get('mcp-session-id')
            if not session_id:
                raise Exception("No session ID in initialize response headers")
            
            _mcp_session_id = session_id
            return session_id
            
    except HTTPError as e:
        raise Exception(f"HTTP Error {e.code}: {e.reason}")
    except URLError as e:
        raise Exception(f"URL Error: {e.reason}")
    except json.JSONDecodeError as e:
        raise Exception(f"JSON Decode Error: {e}")


def mcp_list_tools() -> List[Dict[str, Any]]:
    """
    List available MCP tools.
    
    Returns:
        List of available tools
    """
    global _mcp_session_id
    
    if not _mcp_session_id:
        mcp_initialize()
    
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "params": {},
        "id": 2
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "antalpha-rwa-client/1.0",
        "Mcp-Session-Id": _mcp_session_id
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
            result = _parse_sse_response(content)
            return result.get('tools', [])
            
    except HTTPError as e:
        # If session expired, re-initialize and retry
        if e.code == 401 or e.code == 403:
            mcp_initialize()
            headers["Mcp-Session-Id"] = _mcp_session_id
            request = Request(
                MCP_URL,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urlopen(request, timeout=30) as response:
                content = response.read().decode('utf-8')
                result = _parse_sse_response(content)
                return result.get('tools', [])
        raise Exception(f"HTTP Error {e.code}: {e.reason}")
    except URLError as e:
        raise Exception(f"URL Error: {e.reason}")
    except json.JSONDecodeError as e:
        raise Exception(f"JSON Decode Error: {e}")


def call_mcp_tool(tool_name: str, arguments: dict = None) -> Dict[str, Any]:
    """
    Call Antalpha Prime MCP API tool.
    
    Args:
        tool_name: Name of the MCP tool to call
        arguments: Tool arguments (optional)
    
    Returns:
        Parsed JSON response
    """
    global _mcp_session_id
    
    if not _mcp_session_id:
        mcp_initialize()
    
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {}
        },
        "id": 3
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "User-Agent": "antalpha-rwa-client/1.0",
        "Mcp-Session-Id": _mcp_session_id
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
            return _parse_sse_response(content)
            
    except HTTPError as e:
        # If session expired, re-initialize and retry once
        if e.code == 401 or e.code == 403:
            mcp_initialize()
            headers["Mcp-Session-Id"] = _mcp_session_id
            request = Request(
                MCP_URL,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urlopen(request, timeout=30) as response:
                content = response.read().decode('utf-8')
                return _parse_sse_response(content)
        raise Exception(f"HTTP Error {e.code}: {e.reason}")
    except URLError as e:
        raise Exception(f"URL Error: {e.reason}")
    except json.JSONDecodeError as e:
        raise Exception(f"JSON Decode Error: {e}")



def get_orders_by_address(wallet_address: str) -> List[Dict[str, Any]]:
    """
    Query all orders belonging to a specific wallet address.
    
    Args:
        wallet_address: Customer's wallet address
    
    Returns:
        List of orders for this address
    """
    result = call_mcp_tool("query-orders-by-address", {
        "address": wallet_address
    })
    
    # Extract orders from structuredContent
    content = result.get('content', [])
    structured = result.get('structuredContent', {})
    
    if structured and 'orders' in structured:
        return structured['orders']
    
    # Fallback: parse from text content
    for item in content:
        if item.get('type') == 'text':
            try:
                return json.loads(item['text'])
            except json.JSONDecodeError:
                pass
    
    return []


def get_products() -> List[Dict[str, Any]]:
    """Get list of RWA investment products."""
    result = call_mcp_tool("list-products")
    
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
    amount: float,
    chain: str = DEFAULT_CHAIN,
    token: str = DEFAULT_TOKEN
) -> Dict[str, Any]:
    """
    Generate EIP-681 payment link for token subscription.
    
    Args:
        receiving_address: Product receiving address
        amount: Amount in token
        chain: Chain name (base or ethereum)
        token: Token symbol (USDT or USDC)
    
    Returns:
        Dict with payment link and details
    """
    # Get chain and token config
    chain_config = get_chain_config(chain)
    if not chain_config:
        raise ValueError(f"Unsupported chain: {chain}")
    
    token_config = get_token_config(chain, token)
    if not token_config:
        raise ValueError(f"Unsupported token {token} on chain {chain}")
    
    chain_id = chain_config["chain_id"]
    token_address = token_config["address"]
    decimals = token_config["decimals"]
    
    # Calculate raw amount
    amount_raw = int(amount * (10 ** decimals))
    
    # EIP-681 format for ERC-20 token transfer
    # Format: ethereum:<token_contract>@<chain_id>/transfer?address=<recipient>&uint256=<amount>
    eip681_link = f"ethereum:{token_address}@{chain_id}/transfer?address={receiving_address}&uint256={amount_raw}"
    
    # MetaMask deep link for ERC-20 transfer
    metamask_link = f"https://metamask.app.link/send/{token_address}@{chain_id}/transfer?address={receiving_address}&uint256={amount_raw}"
    
    return {
        "eip681": eip681_link,
        "metamask": metamask_link,
        "receiving_address": receiving_address,
        "token_contract": token_address,
        "token_symbol": token,
        "amount": amount,
        "amount_raw": amount_raw,
        "chain": chain,
        "chain_id": chain_id,
        "decimals": decimals
    }


def generate_qr_code(link: str, output_path: str = None) -> Optional[str]:
    """
    Generate QR code using npx qrcode.
    
    Args:
        link: The URL or data to encode
        output_path: Optional custom output path. If not provided, generates to workspace.
    
    Returns:
        Path to generated QR code file, or None if failed
    """
    if output_path is None:
        # Default to workspace directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(SCRIPT_DIR.parent / f"payment_qr_{timestamp}.png")
    
    try:
        result = subprocess.run(
            ["npx", "qrcode", "-t", "png", "-o", output_path, link],
            capture_output=True,
            timeout=30
        )
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path
        return None
    except Exception:
        return None

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


def record_investment(tx_hash: str, amount: float, chain: str = None, token: str = None, product_id: str = None) -> Dict[str, Any]:
    """
    Record an investment.
    
    Args:
        tx_hash: Transaction hash
        amount: Investment amount
        chain: Chain name
        token: Token symbol
        product_id: Product ID (optional)
    
    Returns:
        Recorded investment record
    """
    product = get_active_product()
    
    record = {
        "tx_hash": tx_hash,
        "amount": amount,
        "chain": chain or DEFAULT_CHAIN,
        "token": token or DEFAULT_TOKEN,
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

def cmd_orders(args):
    """Handle 'orders' command."""
    try:
        orders = get_orders_by_address(args.address)
        
        if args.json:
            print(json.dumps(orders, indent=2))
            return 0
        
        if not orders:
            print(f"\nNo orders found for address: {args.address}\n")
            return 0
        
        print("\n" + "=" * 60)
        print(f"Orders for {args.address[:10]}...{args.address[-6:]}")
        print("=" * 60 + "\n")
        
        for i, order in enumerate(orders, 1):
            print(f"{i}. Order ID: {order.get('order_id', order.get('id', 'N/A'))}")
            print(f"   Product: {order.get('product_name', order.get('product', 'N/A'))}")
            print(f"   Amount: {order.get('amount', 'N/A')} {order.get('token', 'USDT')}")
            print(f"   Status: {order.get('status', 'N/A')}")
            print(f"   Subscribed: {order.get('subscribed_at', order.get('created_at', 'N/A'))}")
            if order.get('maturity_date'):
                print(f"   Maturity: {order['maturity_date']}")
            print()
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1


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
            # Support both old and new API field names
            # rate_apy is already in percent format (e.g., 5.5000), expectedYieldAnnual is decimal (e.g., 0.055)
            rate_apy = p.get('rate_apy')
            if rate_apy is not None:
                yield_pct = float(rate_apy)
            else:
                yield_pct = float(p.get('expectedYieldAnnual', 0)) * 100
            term = p.get('min_holding_days', p.get('productTerm', 'N/A'))
            min_sub = p.get('min_subscription', p.get('minSubscriptionUsdt', 'N/A'))
            status = p.get('status', 'Unknown')
            product_id = p.get('product_id', p.get('id', 'N/A'))
            
            # Get receiving address based on chain
            receiving_address = p.get('receive_address_base') or p.get('receive_address_eth') or p.get('receivingAddress', 'N/A')
            
            print(f"{i}. {p.get('name', 'Unknown')}")
            print(f"   ID: {product_id}")
            print(f"   Term: {term} days")
            print(f"   Annual Yield: {yield_pct:.2f}%")
            print(f"   Min Subscription: {min_sub} USDT")
            print(f"   Status: {status}")
            print(f"   Receiving Address: {receiving_address}")
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
        
        # Support both old and new API field names
        min_sub = float(product.get('min_subscription', product.get('minSubscriptionUsdt', 10)))
        if args.amount < min_sub:
            print(f"Error: Minimum subscription is {min_sub} USDT")
            return 1
        
        # Get receiving address based on chain
        chain = args.chain or DEFAULT_CHAIN
        receiving_address = product.get('receive_address_base') if chain == 'base' else product.get('receive_address_eth')
        receiving_address = receiving_address or product.get('receivingAddress')
        if not receiving_address:
            print("Error: Product has no receiving address")
            return 1
        
        # Get token from args or defaults
        token = args.token or DEFAULT_TOKEN
        
        # Generate payment link
        payment = generate_payment_link(receiving_address, args.amount, chain, token)
        
        # Calculate returns
        # rate_apy is in percent format (e.g., 5.5000), convert to decimal for calculation
        rate_apy = product.get('rate_apy')
        if rate_apy is not None:
            annual_yield = float(rate_apy) / 100
        else:
            annual_yield = float(product.get('expectedYieldAnnual', 0.05))
        term_days = product.get('min_holding_days', product.get('productTerm', 90))
        returns = calculate_returns(args.amount, annual_yield, term_days)
        
        # Generate QR code automatically to workspace
        qr_path = generate_qr_code(payment['metamask'])
        
        if args.json:
            output = {
                "success": True,
                "product": {
                    "id": product.get('product_id', product.get('id')),
                    "name": product.get('name'),
                    "term_days": term_days,
                    "annual_yield": annual_yield
                },
                "investment": {
                    "amount": args.amount,
                    "chain": chain,
                    "token": token,
                    "expected_return": returns['total'],
                    "expected_interest": returns['interest']
                },
                "payment": payment,
                "qr_path": qr_path
            }
            print(json.dumps(output, indent=2))
            return 0
        
        # Human-readable output
        chain_config = get_chain_config(chain)
        chain_name = chain_config.get("name", chain) if chain_config else chain
        
        print("\n" + "=" * 60)
        print("Subscription Payment Link")
        print("=" * 60)
        print(f"\nProduct: {product.get('name')}")
        print(f"Term: {term_days} days")
        print(f"Annual Yield: {annual_yield * 100:.2f}%")
        print(f"\nInvestment: {args.amount} {token}")
        print(f"Chain: {chain_name}")
        print(f"Expected Return: {returns['total']} {token} (at maturity)")
        print(f"  - Principal: {returns['principal']} {token}")
        print(f"  - Interest: {returns['interest']} {token}")
        print(f"\n" + "-" * 60)
        print("Payment Options")
        print("-" * 60)
        print(f"\n[1] MetaMask Mobile (Deep Link):")
        print(f"    {payment['metamask']}")
        print(f"\n[2] QR Code (Mobile Scan):")
        if qr_path:
            print(f"    Generated: {qr_path}")
        else:
            print(f"    Failed to generate QR code")
        print(f"\n[3] Manual Transfer:")
        print(f"    Receiving Address: {receiving_address}")
        print(f"    Token Contract: {payment['token_contract']}")
        print(f"    Amount: {args.amount} {token}")
        print(f"    Chain: {chain_name}")
        
        print(f"\n" + "-" * 60)
        print(f"⚠️  Send exactly {args.amount} {token} on {chain_name} to complete subscription.")
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
        
        # Support both old and new API field names
        rate_apy = product.get('rate_apy')
        if rate_apy is not None:
            annual_yield = float(rate_apy) / 100
        else:
            annual_yield = float(product.get('expectedYieldAnnual', 0.05))
        term_days = product.get('min_holding_days', product.get('productTerm', 90))
        
        returns = calculate_returns(args.amount, annual_yield, term_days)
        
        if args.json:
            output = {
                "product_name": product.get('name'),
                "investment": args.amount,
                "annual_yield": annual_yield,
                "term_days": term_days,
                "returns": returns
            }
            print(json.dumps(output, indent=2))
            return 0
        
        print("\n" + "=" * 60)
        print("Investment Calculator")
        print("=" * 60)
        print(f"\nProduct: {product.get('name')}")
        print(f"Term: {term_days} days")
        print(f"Annual Yield: {annual_yield * 100:.2f}%")
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
        record = record_investment(args.tx, args.amount, args.chain, args.token)
        
        print("\n" + "=" * 60)
        print("Investment Recorded")
        print("=" * 60)
        print(f"\nTX Hash: {record['tx_hash']}")
        print(f"Amount: {record['amount']} {record.get('token', 'USDT')}")
        print(f"Chain: {record.get('chain', 'base')}")
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
            print(f"   Amount: {inv.get('amount', 'N/A')} {inv.get('token', 'USDT')}")
            print(f"   Chain: {inv.get('chain', 'base')}")
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
    
    # orders command
    orders_parser = subparsers.add_parser("orders", help="Query orders by wallet address")
    orders_parser.add_argument("--address", type=str, required=True, help="Wallet address to query orders")
    orders_parser.add_argument("--json", action="store_true", help="Output as JSON")
    orders_parser.set_defaults(func=cmd_orders)
    
    # products command
    products_parser = subparsers.add_parser("products", help="Query available products")
    products_parser.add_argument("--json", action="store_true", help="Output as JSON")
    products_parser.set_defaults(func=cmd_products)
    
    # subscribe command
    subscribe_parser = subparsers.add_parser("subscribe", help="Generate payment link")
    subscribe_parser.add_argument("--amount", type=float, required=True, help="Investment amount in USDT")
    subscribe_parser.add_argument("--chain", type=str, default=None, help="Chain name (base or ethereum)")
    subscribe_parser.add_argument("--token", type=str, default=None, help="Token symbol (USDT or USDC)")
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
    record_parser.add_argument("--chain", type=str, default=None, help="Chain name")
    record_parser.add_argument("--token", type=str, default=None, help="Token symbol")
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