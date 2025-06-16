
---

### English Version Documentation

#### Flexible Grid Strategy User Guide

##### 1. Strategy Overview
The Flexible Grid Strategy is an automated trading strategy designed for perpetual futures markets in cryptocurrencies (e.g., OKX Perpetual). It creates multiple trading levels within a user-defined price range, automatically executing open and take-profit orders to capture profits from market fluctuations.

**Key Features**:
- **Multi-Level Grid**: Divides a price range into multiple levels, each with independent open and take-profit parameters.
- **Long/Short Support**: Supports simultaneous long (`BUY`) and short (`SELL`) grids, adapting to various market trends.
- **Dynamic Price Tracking**: Uses the market mid-price (`mid_price`) and extreme prices (`highest_price`/`lowest_price`) for rebound-based opening and take-profit actions.
- **Flexible Order Types**: Supports limit orders (`LIMIT_MAKER`) and market orders (`MARKET`) to meet diverse trading needs.

**Use Cases**:
- Volatile Markets: Profits from price oscillations within a range through buying low and selling high.
- Long/Short Dual Mode: Runs long and short grids simultaneously, ideal for uncertain market trends.
- Automated Trading: Executes orders and manages positions without manual intervention.

---

##### 2. Strategy Parameters
Below are the main parameters and their meanings, based on the configuration interface (screenshot).

###### Basic Configuration
- **Exchange** (`connector_name`):
  - Select the trading platform, e.g., `okx_perpetual`.
  - Example: `okx_perpetual`
- **Trading Pair** (`trading_pair`):
  - Specify the trading pair, e.g., `BTC-USDT`.
  - Example: `BTC-USDT`
- **Leverage** (`leverage`):
  - Set the leverage multiplier to amplify capital efficiency.
  - Example: 10 (10x leverage)

###### Chart Configuration
- **Candles Data Source** (`candles_connector`):
  - Exchange used to fetch historical candle data, typically the same as `connector_name`.
  - Example: `okx_perpetual`
- **Candle Interval** (`interval`):
  - Time interval for chart candles, e.g., `15m` (15 minutes).
  - Example: `15m`
- **Days to Visualize** (`days_to_visualize`):
  - Number of days of historical data to display on the chart.
  - Example: 7 (7 days)

###### Capital Configuration
- **Total Amount Quote** (`total_amount_quote`):
  - Total capital used by the strategy, in the quote currency (e.g., USDT).
  - Example: 1000 (1000 USDT)
- **Minimum Order Amount** (`min_order_amount_quote`):
  - Minimum capital per order to avoid overly small orders.
  - Example: 10 (10 USDT)

###### Advanced Configuration
- **Position Mode** (`position_mode`):
  - Select position mode: `HEDGE` (supports simultaneous long/short positions), `ONEWAY` (single direction only).
  - Example: `HEDGE`
- **Number of Grid Levels** (`n_levels`):
  - Number of levels within each grid range, determining price point distribution.
  - Example: 3 (3 levels)
- **Maximum Open Orders** (`max_open_orders`):
  - Maximum number of pending open orders allowed at any time.
  - Example: 100
- **Order Frequency (Seconds)** (`order_frequency`):
  - Frequency at which the strategy checks and updates orders, in seconds.
  - Example: 60 (checks every 60 seconds)
- **Activation Bounds** (`activation_bounds`):
  - Price range for order activation and cancellation, as a percentage.
  - Example: 0.01 (1%)

###### Grid Range Configuration
- **Number of Grid Ranges** (`num_ranges`):
  - Number of independent grid ranges in the strategy, each being a sub-grid.
  - Example: 1 (1 range)
- **Direction** (`side`):
  - Trading direction, `BUY` (long) or `SELL` (short).
  - Example: `BUY`
- **Start Price** (`start_price`) and **End Price** (`end_price`):
  - Price range for the grid, with levels evenly distributed within this range.
  - Example: 83422.32 ~ 85650.10
- **Total Amount Percentage** (`total_amount_pct`):
  - Percentage of total capital allocated to this range; the sum of all ranges should be 100%.
  - Example: 50 (50%)
- **Open Order Type** (`open_order_type`) and **Take Profit Order Type** (`take_profit_order_type`):
  - Order type selection, `LIMIT_MAKER` (limit order) or `MARKET` (market order).
  - Example: `LIMIT_MAKER` (open), `LIMIT` (take-profit)

###### Grid Level Configuration
- **Open Ratio** (`open_ratio`):
  - Price increase (short) or decrease (long) ratio for the next level’s trigger price relative to the previous level’s open price.
  - Example: 0.0200 (2%)
- **Open Rebound Ratio** (`open_rebound_ratio`):
  - Rebound ratio for opening, based on `highest_price` (short) or `lowest_price` (long).
  - Example: 0.0100 (1%)
- **Take Profit Ratio** (`take_profit_ratio`):
  - Price decrease (short) or increase (long) ratio for take-profit relative to the open price.
  - Example: 0.0300 (3%)
- **Take Profit Rebound Ratio** (`take_profit_rebound_ratio`):
  - Rebound ratio for take-profit, based on `lowest_price` (short) or `highest_price` (long).
  - Example: 0.0150 (1.5%)
- **Amount Quote Ratio** (`amount_quote_ratio`):
  - Percentage of the range’s capital allocated to this level; the sum of all levels should be 100%.
  - Example: 0.2800 (28%)

---

##### 3. How to Use

###### Step 1: Launch the Strategy
1. **Access the Configuration Interface**:
   - Launch Hummingbot, navigate to the strategy configuration page, and select “Flexible Grid Strategy.”
2. **Set Basic Parameters**:
   - Configure the exchange (`okx_perpetual`), trading pair (`BTC-USDT`), leverage (10), etc.
3. **Configure Grid Ranges**:
   - Set `Number of Grid Ranges` (e.g., 1), specify the direction (`BUY` or `SELL`), price range (e.g., 83422.32~85650.10), and capital percentage (50%) for each range.
   - Select order types (`LIMIT_MAKER` or `MARKET`).
4. **Configure Level Parameters**:
   - Set `Number of Grid Levels` (e.g., 3), and specify open ratio, take-profit ratio, rebound ratios, and capital allocation for each level.
5. **Adjust Advanced Parameters**:
   - Set `Order Frequency` (60 seconds), `Maximum Open Orders` (100), `Activation Bounds` (0.01), etc.
6. **Save and Start**:
   - Click “Save Configuration” and start the strategy; Hummingbot will run automatically.

###### Step 2: Monitor and Adjust
- **Monitoring**:
  - View the chart; grid levels are displayed as horizontal lines (green for `BUY`, red for `SELL`).
  - Check logs for order status (pending, opened, or taken profit).
- **Adjustments**:
  - For high volatility markets, reduce `Order Frequency` (e.g., 5 seconds) for faster response.
  - If orders aren’t filling, adjust `Activation Bounds` (e.g., 0.005) or use `MARKET` orders.

---

##### 4. Strategy Logic
1. **Level Trigger**:
   - Each level has a trigger price (evenly distributed between `start_price` and `end_price`).
   - Long (`BUY`): When `mid_price` drops to the trigger price, enters `WAITING_OPEN_REBOUND`, tracking `lowest_price`.
   - Short (`SELL`): When `mid_price` rises to the trigger price, enters `WAITING_OPEN_REBOUND`, tracking `highest_price`.
2. **Open Rebound**:
   - Long: Triggers opening when `mid_price` rebounds from `lowest_price` by more than `open_rebound_ratio`.
   - Short: Triggers opening when `mid_price` drops from `highest_price` by more than `open_rebound_ratio`.
3. **Take Profit Rebound**:
   - Long: When `mid_price` rises to `actual_open_price * (1 + take_profit_ratio)`, enters `WAITING_TP_REBOUND`, tracking `highest_price`.
   - Short: When `mid_price` drops to `actual_open_price * (1 - take_profit_ratio)`, enters `WAITING_TP_REBOUND`, tracking `lowest_price`.
   - Take-profit price is determined based on the rebound ratio (`take_profit_rebound_ratio`).
4. **Order Management**:
   - Checks every `order_frequency` seconds, updates `highest_price` and `lowest_price`, and creates or cancels orders.
   - Pending order count is limited by `max_open_orders`.

---

##### 5. Example Scenarios
###### Scenario: Single-Direction Long Grid
- **Configuration**:
  - Total Capital: 1000 USDT
  - Number of Grid Ranges: 1 (Range 1, `BUY`)
  - Price Range: 83422.32~85650.10
  - Number of Levels: 3 (L1: 83422.32, L2: 84536.21, L3: 85650.10)
  - Capital Percentage: 50% (500 USDT)
  - L1 Capital Ratio: 0.28 (140 USDT)
  - Open Rebound Ratio: 0.01, Take Profit Ratio: 0.03
  - Order Frequency: 60 seconds
- **Execution**:
  - `mid_price` drops to 83422.32, L1 triggers, enters `WAITING_OPEN_REBOUND`.
  - `mid_price` drops to 83000 (`lowest_price` = 83000), rebounds to 83160 (\( 83000 \times 1.01 \), meets rebound condition).
  - At 60 seconds, places a buy order (`LIMIT_MAKER`), price 83160, quantity 140 USDT / 83160 ≈ 0.00168 BTC.
  - `mid_price` rises to 85650 (\( 83160 \times 1.03 \), triggers take-profit), sells for profit.

###### Scenario: Long/Short Dual Mode
- **Configuration**:
  - Number of Grid Ranges: 2
  - Range 1: `BUY`, 80000~82000, Capital Percentage 50%
  - Range 2: `SELL`, 82000~84000, Capital Percentage 50%
  - Number of Levels: 3
- **Execution**:
  - Range 1 (Long): Price drops to 80000, opens position, takes profit at 82400.
  - Range 2 (Short): Price rises to 84000, opens position, takes profit at 81600.

---

##### 6. Notes
- **Market Risks**:
  - Grid strategies perform best in ranging markets; in trending markets (e.g., sustained upward trend), they may lead to capital lockup or losses.
- **Parameter Tuning**:
  - High Volatility: Reduce `Order Frequency` (e.g., 5 seconds), use `MARKET` orders.
  - Low Volatility: Use `LIMIT_MAKER`, set larger `Activation Bounds` (e.g., 0.02).
- **Exchange Limits**:
  - Ensure API key permissions are correct; be aware of exchange limits on order quantity and frequency.
- **Capital Management**:
  - Allocate capital wisely (`total_amount_pct` and `amount_quote_ratio`) to avoid over-concentration in a single level.

---

##### 7. FAQ
- **Q: Why aren’t my orders filling?**
  - A: `Activation Bounds` may be too tight, causing frequent cancellations; or market volatility is low. Try reducing `Order Frequency` or using `MARKET` orders.
- **Q: How do I set up long/short dual mode?**
  - A: Set `Number of Grid Ranges` to 2, configure Range 1 as `BUY` and Range 2 as `SELL`, and allocate capital percentages.
- **Q: How often are `highest_price` and `lowest_price` updated?**
  - A: They are updated every `order_frequency` seconds (e.g., 60 seconds). For faster response, reduce `order_frequency`.

---