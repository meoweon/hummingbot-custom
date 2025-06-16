# DMAN V3 Strategy

## Strategy Overview

DMAN V3 is a mean reversion trading strategy based on Bollinger Bands, enhanced with Dollar-Cost Averaging (DCA) techniques. The strategy aims to enter trades when price deviates from its mean, using Bollinger Bands to identify overbought and oversold areas in the market, while implementing DCA to reduce entry risk.

## Core Features

- **Mean Reversion Trading**: Uses Bollinger Bands to detect price deviations, shorting in overbought areas and buying in oversold areas
- **Dynamic Order Spread**: Automatically adjusts order spreads based on market volatility (Bollinger Band width)
- **DCA Strategy**: Implements Dollar-Cost Averaging to distribute risk across multiple entry points
- **Flexible Risk Management**: Supports stop-loss, take-profit, and trailing stop functionality with dynamic adjustments based on market conditions
- **Multi-Market Support**: Can operate on multiple exchanges and trading pairs

## Suitable Market Scenarios

DMAN V3 performs optimally in the following market conditions:

### Ideal Markets

- **Range-bound/Sideways Markets**: Excels in markets that oscillate within a defined range, where mean reversion principles work most effectively
- **Markets with Regular Volatility Cycles**: Performs well when volatility expands and contracts in predictable patterns
- **Liquid Markets with Moderate Spreads**: Functions best in markets with sufficient liquidity to execute multiple DCA orders without excessive slippage

### Challenging Markets

- **Strong Trending Markets**: May generate false signals in strongly trending markets as price can continue moving away from the mean
- **Low Volatility Environments**: The strategy benefits from volatility to create meaningful price deviations
- **Illiquid Markets**: May struggle with order execution and experience higher slippage in thin markets

### Timeframe Considerations

- **Medium Timeframes**: Most effective on 1-hour to 4-hour charts where price movements are significant but not excessively volatile
- **Can Be Applied to Lower Timeframes**: For more active trading, but requires tighter risk management
- **Higher Timeframes**: For longer-term position building, requiring larger capital allocation and wider stop losses

## Parameter Explanation

### Bollinger Bands Configuration

- **BB Length**: The period for calculating Bollinger Bands, default is 20
- **Standard Deviation Multiplier**: The standard deviation multiplier for the bands, default is 2.0
- **Long Threshold**: BBP threshold that triggers a long signal when price is below this value, default is 0.2
- **Short Threshold**: BBP threshold that triggers a short signal when price is above this value, default is 0.8

### DCA Configuration

- **DCA Spreads**: Price deviations for each DCA level, e.g., "0.001,0.018,0.15,0.25"
- **DCA Amount Percentages**: Capital allocation for each DCA level, e.g., "0.25,0.25,0.25,0.25"
- **Dynamic Order Spread**: Option to dynamically adjust order spreads based on BB width
- **Dynamic Target**: Option to dynamically adjust targets based on market volatility
- **Activation Bounds**: Price boundaries to activate the next order

## Risk Management

- **Stop Loss**: Closes position at specified loss percentage
- **Take Profit**: Closes position at specified profit percentage
- **Time Limit**: Maximum holding time for orders
- **Trailing Stop**: Closes position when price retraces a specified amount from its peak

## Tips for Optimization

- Adjust BB parameters for different market environments
- Modify DCA configurations based on capital size and risk tolerance
- Regularly backtest and optimize strategy parameters
- Use leverage cautiously and control risk exposure per trade
- Consider adjusting thresholds for different market volatility regimes 