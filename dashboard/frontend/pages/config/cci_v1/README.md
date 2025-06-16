# CCI Strategy Configuration Tool

Welcome to the CCI (Commodity Channel Index) configuration tool! This tool allows you to create, modify, visualize, and save configurations for a CCI-based directional trading strategy. Here's how to make the most of it.

## Features

- **Start with Default Configuration**: Begin with default configurations, or use values from existing configurations.
- **Modify Configuration Values**: Change various parameters according to your trading strategy needs.
- **Visualize Results**: See the impact of your changes through visual charts.
- **Save and Deploy**: Once satisfied, save the configuration for later deployment.

## How to Use

### 1. Load Default Configuration

First, load the default configuration for the CCI strategy. This provides a baseline setup that you can customize as needed.

### 2. User Input

Input various parameters for the strategy configuration. These parameters include:

- **Connector Name**: Choose a trading platform or exchange.
- **Trading Pair**: Select a cryptocurrency trading pair.
- **Leverage**: Set the leverage ratio. (Note: If you're using spot trading, set leverage to 1)
- **Total Amount (Quote Currency)**: Define the total amount you want to allocate for trading.
- **Maximum Executors per Side**: Specify the maximum number of executors per side.
- **Cooldown Time**: Set the cooling period between trades.
- **Position Mode**: Choose between different position modes.
- **Candles Connector**: Choose the data source for candle data.
- **Candles Trading Pair**: Select the trading pair for candle data.
- **Interval**: Set the time interval for candle data.
- **CCI Length**: Define the length of the CCI indicator calculation period.
- **Overbought Level**: Set the CCI overbought threshold (typically 100 or higher).
- **Oversold Level**: Set the CCI oversold threshold (typically -100 or lower).
- **Risk Management**: Set parameters for stop loss, take profit, time limits, and trailing stop loss settings.

### 3. Signal Configuration

The CCI strategy allows you to customize how signals are generated:

#### Overbought Settings
- **Level**: The CCI value that indicates overbought conditions (default: 100)
- **Crossing Direction**: Choose whether to generate signals when CCI crosses above or below the overbought level
- **Signal Type**: Choose whether to generate buy or sell signals when the overbought condition is triggered

#### Oversold Settings
- **Level**: The CCI value that indicates oversold conditions (default: -100)
- **Crossing Direction**: Choose whether to generate signals when CCI crosses above or below the oversold level
- **Signal Type**: Choose whether to generate buy or sell signals when the oversold condition is triggered

### 4. Visualizing Indicators

Visualize the CCI indicator on the trading interface to see the impact of your configuration. Here are some tips to help you fine-tune the indicator:

- **CCI Length**: Larger lengths will make the CCI indicator smoother and less sensitive to short-term price fluctuations, while smaller lengths will make it more responsive to recent price changes. In general, periods of 14-20 work well for most markets.
- **Overbought/Oversold Levels**: Traditional values are +100/-100, but in volatile markets, you might need higher thresholds (like +150/-150) to avoid entering trades too early.

### 5. Trading Signals Explanation

The CCI V1 strategy uses the Commodity Channel Index (CCI) to generate trading signals based on your configuration:

- **Signal Generation**: Signals are generated when the CCI crosses the overbought or oversold levels in the specified direction.
- **Signal Types**: You can configure whether crossing each level generates a buy or sell signal, allowing for flexible strategy design.
- **Traditional Setup**: In a traditional setup:
  - Oversold crossovers generate buy signals (market potentially oversold)
  - Overbought crossovers generate sell signals (market potentially overbought)

### 6. Executor Allocation

The total amount in quote currency will be divided between the maximum number of executors per side. For example, if the total amount is 1000 and the maximum executors per side is 5, each executor will have 200 for trading. If a signal is triggered, the first executor will place an order and wait for the cooldown time, after which the next executor will execute, and this pattern will continue for subsequent orders.

### 7. Save Configuration

Once you are satisfied with the configuration and visual results, save the configuration for future use. This allows you to deploy the same strategy later without having to reconfigure from scratch.

### Advantages and Considerations for CCI Strategy

- **Advantages**: CCI is a versatile indicator that can work in various market conditions. It identifies overbought and oversold conditions by measuring the deviation of the current price from the historical average price.
- **Considerations**: In strongly trending markets, CCI can remain in overbought or oversold territory for extended periods, potentially leading to premature counter-trend entries. Consider combining with other indicators to confirm signals.

---

Feel free to experiment with different configurations to find the optimal settings for your trading strategy. Happy trading! 