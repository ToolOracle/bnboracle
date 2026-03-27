# ⬡ bnbOracle

**BNB Chain Intelligence MCP Server** — 8 tools | Part of [ToolOracle](https://tooloracle.io)

![Tools](https://img.shields.io/badge/MCP_Tools-8-10B898?style=flat-square)
![Status](https://img.shields.io/badge/Status-Live-00C853?style=flat-square)
![Chain](https://img.shields.io/badge/Chain-BNB_Chain-F0B90B?style=flat-square)
![Tier](https://img.shields.io/badge/Tier-Free-2196F3?style=flat-square)

BEP-20 token risk, BSC contract verification, gas tracker, PancakeSwap DEX liquidity, protocol TVL, stablecoin peg check, wallet intelligence, DeFi yields. Evidence-grade data for institutional DeFi on BNB Chain.

## Quick Connect

```bash
npx -y mcp-remote https://feedoracle.io/mcp/bnboracle/
```

```json
{
  "mcpServers": {
    "bnboracle": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://feedoracle.io/mcp/bnboracle/"]
    }
  }
}
```

## Tools (8)

| Tool | Description |
|------|-------------|
| `bnb_overview` | BNB Chain overview: BNB price, gas, TVL, latest block |
| `bnb_token_risk` | BEP-20 token risk: holder concentration, contract info, supply |
| `bnb_contract_verify` | Contract verification: source code, ABI, proxy detection on BscScan |
| `bnb_gas` | Gas tracker with USD cost estimates — typical 0.05 gwei, very low fees |
| `bnb_protocol_tvl` | DeFi protocol TVL on BSC. Empty = top-20 protocols |
| `bnb_stablecoin_check` | Stablecoin peg check: USDT, USDC, BUSD, FDUSD, DAI on BNB Chain |
| `bnb_wallet_intel` | Wallet intelligence: BNB balance, recent transactions |
| `bnb_defi_yields` | Top DeFi yields on BNB Chain filtered by TVL and APY |

## Part of FeedOracle / ToolOracle

**Blockchain Oracle Suite:**
- [ethOracle](https://github.com/tooloracle/ethoracle) — Ethereum
- [xlmOracle](https://github.com/tooloracle/xlmoracle) — Stellar
- [xrplOracle](https://github.com/tooloracle/xrploracle) — XRP Ledger
- [bnbOracle](https://github.com/tooloracle/bnboracle) — BNB Chain (this repo)
- [aptOracle](https://github.com/tooloracle/aptoracle) — Aptos
- [baseOracle](https://github.com/tooloracle/baseoracle) — Base L2

## Links

- 🌐 Live: `https://feedoracle.io/mcp/bnboracle/`
- 🏠 Platform: [feedoracle.io](https://feedoracle.io)

---
*Built by [FeedOracle](https://feedoracle.io) — Evidence by Design*
