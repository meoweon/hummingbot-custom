# Spot-Perpetual Arbitrage Strategy Configuration Tool

Welcome to the Spot-Perpetual Arbitrage Strategy Configuration Tool! This tool allows you to create, modify, visualize, and save configurations for the spot-perpetual arbitrage strategy, which profits from price differences between spot and perpetual markets.

## Features

- **Cross-Market Trading**: Trade between spot and perpetual markets
- **Price Difference Monitoring**: Track and visualize price differences
- **Dynamic Position Management**: Flexible position sizing and risk management
- **Visual Configuration**: See price action and differences directly
- **Save and Deploy**: Save your configuration for later deployment

## How to Use

### 1. Basic Configuration

Start by configuring the basic parameters:
- **Spot Exchange**: Choose your preferred spot exchange
- **Perpetual Exchange**: Choose your preferred perpetual exchange
- **Trading Pair**: Select the cryptocurrency trading pair (e.g., "BTC-USDT")
- **Position Mode**: Choose between HEDGE or ONE-WAY mode
- **Leverage**: Set the leverage ratio for perpetual trading

### 2. Chart Configuration

Configure how you want to visualize the market data:
- **Interval**: Choose the timeframe for the candlesticks (1m to 1d)
- **Days to Display**: Select how many days of historical data to show

### 3. Strategy Parameters

Fine-tune your strategy with these parameters:

a. **Order Configuration**:
- **Total Quote Amount**: Total amount in quote currency to use for trading
- **Minimum Price Difference**: Minimum price difference percentage to trigger trades

b. **Advanced Parameters**:
- **Min Trade Size**: Minimum trade size in base currency
- **Max Trade Size**: Maximum trade size in base currency
- **Max Position Size**: Maximum total position size
- **Cooldown Time**: Minimum time between trades

c. **Market Parameters**:
- **Spot Market Slippage**: Maximum allowed slippage for spot orders
- **Perpetual Market Slippage**: Maximum allowed slippage for perpetual orders

## Understanding Spot-Perpetual Arbitrage

The spot-perpetual arbitrage strategy profits from price differences between spot and perpetual markets. Here's how it works:

### Basic Concept
- Monitor price differences between markets
- Open positions when profitable opportunities arise
- Close positions when price differences converge
- Manage risk with position limits and slippage controls

### Strategy Mechanics
- When perpetual price > spot price + threshold:
  1. Buy on spot market
  2. Sell on perpetual market
  3. Wait for prices to converge
  4. Close positions for profit

- When spot price > perpetual price + threshold:
  1. Sell on spot market
  2. Buy on perpetual market
  3. Wait for prices to converge
  4. Close positions for profit

### Risk Management
- Position size limits
- Market slippage controls
- Cooldown periods between trades
- Maximum position size cap

## Best Practices

1. **Market Selection**
   - Choose liquid markets
   - Monitor price correlations
   - Consider exchange fees
   - Watch for market inefficiencies

2. **Position Management**
   - Start with conservative sizes
   - Balance position ratios
   - Monitor price convergence
   - Track overall exposure

3. **Risk Control**
   - Set appropriate slippage limits
   - Use reasonable leverage
   - Maintain sufficient margin
   - Consider market conditions

4. **Performance Optimization**
   - Track profit and loss
   - Monitor execution costs
   - Analyze trade distribution
   - Adjust parameters based on results

## Technical Details

### Entry Conditions
```
Long Spot/Short Perp:
Perp Price > Spot Price * (1 + min_price_diff_pct)

Short Spot/Long Perp:
Spot Price > Perp Price * (1 + min_price_diff_pct)
```

### Position Sizing
```
Position Size = min(
    max(
        order_amount_quote / current_price,
        min_trade_size
    ),
    max_trade_size
)
```

### Profit Calculation
```
Profit = Price Difference * Position Size - Trading Fees
```

## Troubleshooting

1. **No Trades Opening**
   - Check if price differences meet minimum threshold
   - Verify sufficient balance and leverage
   - Check market liquidity
   - Confirm exchange connectivity

2. **Unexpected Losses**
   - Review market slippage settings
   - Check position sizing
   - Analyze market movements
   - Monitor price convergence

3. **Strategy Performance**
   - Track price difference patterns
   - Monitor execution costs
   - Analyze market conditions
   - Adjust parameters if needed

## Support

For additional support:
- Check the documentation
- Join the community forum
- Contact technical support 