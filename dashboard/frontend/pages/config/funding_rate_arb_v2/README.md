# Funding Rate Arbitrage Strategy V2

This strategy implements an automated funding rate arbitrage between different perpetual futures exchanges. It monitors funding rates across multiple exchanges and executes trades when profitable opportunities arise.

## Features

- Multi-exchange support (Binance, OKX, Bybit, Hyperliquid)
- Real-time funding rate monitoring
- Customizable entry and exit conditions
- Position size management
- Risk management with stop-loss
- Visual funding rate comparison
- Support for multiple trading pairs

## Configuration Parameters

### Basic Configuration

- **Tokens**: Trading pairs to monitor (e.g., BTC, ETH)
- **Connectors**: Exchanges to use for arbitrage
- **Leverage**: Trading leverage (1-100x)
- **Position Mode**: HEDGE or ONEWAY

### Strategy Parameters

- **Minimum Funding Rate Profitability**: Minimum funding rate difference to enter position
- **Position Size**: Position size in quote currency
- **Take Profit Threshold**: Profit target for position exit
- **Stop Loss Threshold**: Maximum acceptable funding rate difference loss
- **Trade Profitability Condition**: Option to only enter trades that are immediately profitable

## Usage

1. Select the tokens you want to trade
2. Choose the exchanges you want to use
3. Configure your leverage and position mode
4. Set your strategy parameters
5. Monitor the funding rate charts
6. Save your configuration

## Risk Management

- Always start with small position sizes
- Monitor your positions regularly
- Use appropriate leverage based on market conditions
- Set stop-loss levels to protect against adverse market movements

## Visualization

The strategy includes interactive charts showing:
- Historical funding rates for each exchange
- Profitability thresholds
- Stop loss levels

## Notes

- Funding rates are fetched in real-time using the CCXT library
- Historical data is available for up to 30 days
- The strategy automatically calculates funding rate differences between exchanges
- Position sizes are adjusted based on available margin and risk parameters 