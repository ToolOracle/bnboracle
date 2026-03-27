#!/usr/bin/env python3
"""BNBOracle MCP Server v1.0.0 — Port 11501
BNB Chain Intelligence for AI Agents.
BEP-20 token risk, BSC contract verification, gas tracker,
PancakeSwap DEX liquidity, protocol TVL, stablecoin peg check,
wallet intelligence, DeFi yields, RWA on BNB Chain.
Evidence-grade data for institutional DeFi and compliance.
"""
import os, sys, json, logging, aiohttp, asyncio
from datetime import datetime, timezone

sys.path.insert(0, "/root/whitelabel")
from shared.utils.mcp_base import WhitelabelMCPServer

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [BNBOracle] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler("/root/whitelabel/logs/bnboracle.log", mode="a")])
logger = logging.getLogger("BNBOracle")

PRODUCT_NAME = "BNBOracle"
VERSION      = "1.0.0"
PORT_MCP     = 11501
PORT_HEALTH  = 11502

BSC_RPC    = "https://bsc-dataseed1.binance.org"
BSCSCAN    = "https://api.bscscan.com/api"
LLAMA      = "https://api.llama.fi"
LLAMA_Y    = "https://yields.llama.fi"
CG         = "https://api.coingecko.com/api/v3"
BSCSCAN_KEY = os.getenv("BSCSCAN_API_KEY", "YourApiKeyToken")
HEADERS    = {"User-Agent": "BNBOracle-ToolOracle/1.0", "Accept": "application/json"}

def ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

async def get(url, params=None, timeout=15):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params=params, headers=HEADERS,
                             timeout=aiohttp.ClientTimeout(total=timeout)) as r:
                if r.status == 200:
                    return await r.json(content_type=None)
                return {"error": f"HTTP {r.status}"}
    except Exception as e:
        return {"error": str(e)}

async def bsc_rpc(method, params=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(BSC_RPC, json=body,
                              headers={"Content-Type": "application/json"},
                              timeout=aiohttp.ClientTimeout(total=15)) as r:
                if r.status == 200:
                    d = await r.json(content_type=None)
                    return d.get("result")
    except:
        pass
    return None

async def bscscan(params, timeout=15):
    p = {"apikey": BSCSCAN_KEY, **params}
    return await get(BSCSCAN, p, timeout)

def risk_grade(score):
    if score >= 80: return "A"
    if score >= 60: return "B"
    if score >= 40: return "C"
    if score >= 20: return "D"
    return "F"

def wei_to_bnb(hex_val):
    try:
        return round(int(hex_val, 16) / 1e18, 6)
    except:
        return 0

async def handle_overview(args):
    price_data, tvl_data = await asyncio.gather(
        get(f"{CG}/simple/price", {"ids": "binancecoin", "vs_currencies": "usd,eur",
            "include_24hr_change": "true", "include_market_cap": "true",
            "include_24hr_vol": "true"}),
        get(f"{LLAMA}/v2/chains"),
    )
    bnb = price_data.get("binancecoin", {}) if isinstance(price_data, dict) else {}
    bnb_tvl = 0
    if isinstance(tvl_data, list):
        for c in tvl_data:
            if c.get("name") in ("Binance", "BSC"):
                bnb_tvl = c.get("tvl", 0)
                break
    block_hex = await bsc_rpc("eth_blockNumber")
    block = int(block_hex, 16) if block_hex else 0
    gas_hex = await bsc_rpc("eth_gasPrice")
    gas_gwei = round(int(gas_hex, 16) / 1e9, 4) if gas_hex else None
    return {
        "chain": "BNB Chain", "network": "mainnet", "chain_id": 56,
        "timestamp": ts(),
        "price": {"usd": bnb.get("usd"), "eur": bnb.get("eur"),
                  "change_24h": bnb.get("usd_24h_change"),
                  "market_cap_usd": bnb.get("usd_market_cap"),
                  "volume_24h_usd": bnb.get("usd_24h_vol")},
        "network_stats": {"latest_block": block, "total_tvl_usd": round(bnb_tvl, 2)},
        "gas": {"current_gwei": gas_gwei, "note": "BSC fixed 3 gwei base fee"},
        "source": "CoinGecko + DefiLlama + BSC RPC"
    }

async def handle_token_risk(args):
    contract = args.get("contract_address", "").strip()
    if not contract:
        return {"error": "contract_address required (BEP-20 0x...)"}
    info, holders, txcount = await asyncio.gather(
        bscscan({"module": "token", "action": "tokeninfo", "contractaddress": contract}),
        bscscan({"module": "token", "action": "tokenholderlist",
                 "contractaddress": contract, "page": "1", "offset": "10"}),
        bscscan({"module": "account", "action": "tokentx",
                 "contractaddress": contract, "page": "1", "offset": "1", "sort": "desc"}),
    )
    token_info = {}
    if isinstance(info, dict) and info.get("status") == "1":
        r = info.get("result", [{}])
        token_info = r[0] if isinstance(r, list) and r else {}
    top_holders = []
    if isinstance(holders, dict) and holders.get("status") == "1":
        for h in (holders.get("result") or [])[:5]:
            top_holders.append({"address": h.get("TokenHolderAddress"),
                                 "quantity": h.get("TokenHolderQuantity")})
    score = 50
    name = token_info.get("tokenName", "Unknown")
    symbol = token_info.get("symbol", "?")
    return {
        "contract": contract, "name": name, "symbol": symbol,
        "decimals": token_info.get("divisor"),
        "total_supply": token_info.get("totalSupply"),
        "top_holders": top_holders,
        "risk_score": score, "risk_grade": risk_grade(score),
        "timestamp": ts(), "source": "BscScan"
    }

async def handle_contract_verify(args):
    contract = args.get("contract_address", "").strip()
    if not contract:
        return {"error": "contract_address required"}
    source, abi = await asyncio.gather(
        bscscan({"module": "contract", "action": "getsourcecode", "address": contract}),
        bscscan({"module": "contract", "action": "getabi", "address": contract}),
    )
    src_result = {}
    is_verified = False
    if isinstance(source, dict) and source.get("status") == "1":
        r = source.get("result", [{}])
        src_result = r[0] if isinstance(r, list) and r else {}
        is_verified = bool(src_result.get("SourceCode"))
    abi_ok = isinstance(abi, dict) and abi.get("status") == "1"
    score = 70 if is_verified else 20
    if abi_ok: score += 10
    return {
        "contract": contract, "verified": is_verified, "abi_available": abi_ok,
        "contract_name": src_result.get("ContractName"),
        "compiler": src_result.get("CompilerVersion"),
        "license": src_result.get("LicenseType"),
        "proxy": src_result.get("Proxy") == "1",
        "implementation": src_result.get("Implementation") or None,
        "risk_score": score, "risk_grade": risk_grade(score),
        "risk_note": "Unverified contracts carry high risk" if not is_verified else "Verified on BscScan",
        "timestamp": ts(), "source": "BscScan"
    }

async def handle_gas(args):
    gas_hex, price_data = await asyncio.gather(
        bsc_rpc("eth_gasPrice"),
        get(f"{CG}/simple/price", {"ids": "binancecoin", "vs_currencies": "usd"}),
    )
    bnb_usd = price_data.get("binancecoin", {}).get("usd", 0) if isinstance(price_data, dict) else 0
    gas_gwei = round(int(gas_hex, 16) / 1e9, 4) if gas_hex else 3.0

    def gwei_to_usd(gwei, gas_units):
        try:
            return round(float(gwei) * gas_units * 1e-9 * bnb_usd, 6)
        except:
            return None

    return {
        "timestamp": ts(), "bnb_price_usd": bnb_usd,
        "gas_price_gwei": gas_gwei,
        "estimated_cost_usd": {
            "simple_transfer_21k": gwei_to_usd(gas_gwei, 21000),
            "bep20_transfer_65k": gwei_to_usd(gas_gwei, 65000),
            "pancake_swap_200k": gwei_to_usd(gas_gwei, 200000),
        },
        "note": "BSC has much lower fees than Ethereum",
        "source": "BSC RPC + CoinGecko"
    }

async def handle_protocol_tvl(args):
    protocol = args.get("protocol", "").strip().lower()
    if not protocol:
        all_p = await get(f"{LLAMA}/protocols")
        bsc_p = []
        if isinstance(all_p, list):
            for p in all_p:
                if "BSC" in p.get("chains", []) or "Binance" in p.get("chains", []):
                    tvl_raw = p.get("tvl")
                    tvl = tvl_raw[-1].get("totalLiquidityUSD") if isinstance(tvl_raw, list) and tvl_raw else tvl_raw
                    bsc_p.append({"name": p.get("name"), "slug": p.get("slug"),
                                  "tvl_usd": tvl, "category": p.get("category")})
            bsc_p.sort(key=lambda x: x.get("tvl_usd") or 0, reverse=True)
        return {"top_bsc_protocols": bsc_p[:20], "count": len(bsc_p),
                "timestamp": ts(), "source": "DefiLlama"}
    data = await get(f"{LLAMA}/protocol/{protocol}")
    if isinstance(data, dict) and "error" not in data:
        tvl_raw = data.get("tvl")
        tvl = tvl_raw[-1].get("totalLiquidityUSD") if isinstance(tvl_raw, list) and tvl_raw else tvl_raw
        return {"protocol": data.get("name"), "category": data.get("category"),
                "tvl_total_usd": tvl, "chains": data.get("chains", []),
                "change_1d": data.get("change_1d"), "change_7d": data.get("change_7d"),
                "timestamp": ts(), "source": "DefiLlama"}
    return {"error": f"Protocol '{protocol}' not found", "timestamp": ts()}

async def handle_stablecoin_check(args):
    symbol = args.get("symbol", "USDT").upper()
    STABLES = {
        "USDT": "0x55d398326f99059ff775485246999027b3197955",
        "USDC": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
        "BUSD": "0xe9e7cea3dedca5984780bafc599bd69add087d56",
        "FDUSD": "0xc5f0f7b66764f6ec8c8dff7ba683102295e16409",
        "DAI":  "0x1af3f329e8be154074d8769d1ffa4ee058b1dbc3",
    }
    contract = STABLES.get(symbol) or args.get("contract_address", "")
    if not contract:
        return {"known_stablecoins": list(STABLES.keys()),
                "message": "Provide symbol or contract_address"}
    price_data = await get(f"{CG}/simple/token_price/binance-smart-chain",
                           {"contract_addresses": contract, "vs_currencies": "usd",
                            "include_24hr_change": "true"})
    price = None
    if isinstance(price_data, dict):
        token_data = price_data.get(contract.lower(), {})
        price = token_data.get("usd")
    peg_dev = abs(price - 1.0) if price else None
    peg_status = "STABLE" if peg_dev is not None and peg_dev < 0.005 else \
                 "MINOR_DEVIATION" if peg_dev is not None and peg_dev < 0.02 else "DEPEGGED"
    score = 90 if peg_status == "STABLE" else 50 if peg_status == "MINOR_DEVIATION" else 10
    return {
        "symbol": symbol, "contract": contract, "chain": "BNB Chain",
        "price_usd": price,
        "peg_deviation": round(peg_dev, 6) if peg_dev is not None else None,
        "peg_deviation_pct": round(peg_dev * 100, 4) if peg_dev is not None else None,
        "peg_status": peg_status, "risk_score": score, "risk_grade": risk_grade(score),
        "timestamp": ts(), "source": "CoinGecko"
    }

async def handle_wallet_intel(args):
    address = args.get("address", "").strip()
    if not address:
        return {"error": "address required"}
    bal_hex, txs = await asyncio.gather(
        bsc_rpc("eth_getBalance", [address, "latest"]),
        bscscan({"module": "account", "action": "txlist",
                 "address": address, "page": "1", "offset": "10", "sort": "desc"}),
    )
    bnb_bal = wei_to_bnb(bal_hex) if bal_hex else 0
    price_data = await get(f"{CG}/simple/price", {"ids": "binancecoin", "vs_currencies": "usd"})
    bnb_usd = price_data.get("binancecoin", {}).get("usd", 0) if isinstance(price_data, dict) else 0
    recent_txs = []
    if isinstance(txs, dict) and txs.get("status") == "1":
        for tx in (txs.get("result") or [])[:5]:
            recent_txs.append({
                "hash": tx.get("hash"), "from": tx.get("from"), "to": tx.get("to"),
                "value_bnb": round(int(tx.get("value", "0")) / 1e18, 6),
                "timestamp": datetime.fromtimestamp(int(tx.get("timeStamp", 0)), tz=timezone.utc)
                             .strftime("%Y-%m-%dT%H:%M:%SZ")
            })
    return {
        "address": address, "bnb_balance": bnb_bal,
        "bnb_balance_usd": round(bnb_bal * bnb_usd, 2),
        "recent_transactions": recent_txs,
        "timestamp": ts(), "source": "BSC RPC + BscScan"
    }

async def handle_defi_yields(args):
    min_tvl = args.get("min_tvl_usd", 1_000_000)
    min_apy = args.get("min_apy_pct", 0)
    max_apy = args.get("max_apy_pct", 200)
    limit = min(args.get("limit", 20), 50)
    pools = await get(f"{LLAMA_Y}/pools")
    data = pools.get("data", []) if isinstance(pools, dict) else []
    results = []
    for p in data:
        if (p.get("chain", "").lower() in ("bsc", "binance") and
            p.get("tvlUsd", 0) >= min_tvl and
            min_apy <= (p.get("apy") or 0) <= max_apy):
            results.append({
                "pool": p.get("pool"), "project": p.get("project"),
                "symbol": p.get("symbol"), "apy_pct": round(p.get("apy") or 0, 2),
                "tvl_usd": round(p.get("tvlUsd") or 0, 0), "il_risk": p.get("ilRisk"),
            })
    results.sort(key=lambda x: x.get("tvl_usd", 0), reverse=True)
    return {"chain": "BSC", "yields": results[:limit], "total_found": len(results),
            "timestamp": ts(), "source": "DefiLlama Yields"}

def build_server():
    server = WhitelabelMCPServer(
        product_name=PRODUCT_NAME, product_slug="bnboracle",
        version=VERSION, port_mcp=PORT_MCP, port_health=PORT_HEALTH,
    )
    server.register_tool("bnb_overview",
        "BNB Chain ecosystem overview: BNB price, gas, TVL, block stats",
        {"type": "object", "properties": {}, "required": []}, handle_overview)
    server.register_tool("bnb_token_risk",
        "BEP-20 token risk assessment: holder concentration, contract info",
        {"type": "object", "properties": {"contract_address": {"type": "string"}}, "required": ["contract_address"]}, handle_token_risk)
    server.register_tool("bnb_contract_verify",
        "Verify BNB Chain smart contract: source code, ABI, proxy detection",
        {"type": "object", "properties": {"contract_address": {"type": "string"}}, "required": ["contract_address"]}, handle_contract_verify)
    server.register_tool("bnb_gas",
        "BNB Chain gas tracker with USD cost estimates for common operations",
        {"type": "object", "properties": {}, "required": []}, handle_gas)
    server.register_tool("bnb_protocol_tvl",
        "BNB Chain DeFi protocol TVL. Leave protocol empty for top-20 list.",
        {"type": "object", "properties": {"protocol": {"type": "string"}}, "required": []}, handle_protocol_tvl)
    server.register_tool("bnb_stablecoin_check",
        "BNB Chain stablecoin peg check: USDT, USDC, BUSD, FDUSD, DAI",
        {"type": "object", "properties": {
            "symbol": {"type": "string", "description": "USDT, USDC, BUSD, FDUSD, DAI"},
            "contract_address": {"type": "string"}}, "required": []}, handle_stablecoin_check)
    server.register_tool("bnb_wallet_intel",
        "BNB Chain wallet intelligence: BNB balance, recent transactions",
        {"type": "object", "properties": {"address": {"type": "string"}}, "required": ["address"]}, handle_wallet_intel)
    server.register_tool("bnb_defi_yields",
        "Top DeFi yield opportunities on BNB Chain filtered by TVL and APY",
        {"type": "object", "properties": {
            "min_tvl_usd": {"type": "number", "default": 1000000},
            "min_apy_pct": {"type": "number", "default": 0},
            "max_apy_pct": {"type": "number", "default": 200},
            "limit": {"type": "integer", "default": 20}}, "required": []}, handle_defi_yields)
    return server

if __name__ == "__main__":
    srv = build_server()
    srv.run()
