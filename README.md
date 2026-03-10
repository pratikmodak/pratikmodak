## Indian Share Market Signal Bot (Starter)

This repository now includes a starter bot (`signal_bot.py`) that generates **BUY / SELL / HOLD** signals for NSE stocks (India market) using:

- SMA(20) vs SMA(50) crossover
- RSI(14) filter
- Yahoo Finance historical candles (`.NS` symbols)

> This is for educational/demo use only, not financial advice.

## Quick start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the signal bot:

```bash
python signal_bot.py --symbols RELIANCE TCS INFY
```

3. Optional: send signals to Telegram

```bash
export TELEGRAM_BOT_TOKEN="<your_bot_token>"
export TELEGRAM_CHAT_ID="<your_chat_id>"
python signal_bot.py --symbols RELIANCE TCS INFY --send-telegram
```

## How signals are generated

- **BUY**: 20-SMA crosses above 50-SMA and RSI < 70
- **SELL**: 20-SMA crosses below 50-SMA and RSI > 30
- **HOLD**: no fresh crossover confirmation

You can tune these rules in `calculate_signal()` based on your strategy.

## Notes for live usage

- For production, run this bot on a schedule (cron / cloud scheduler) every market session.
- Add risk controls (position sizing, stop-loss, max daily loss) before trading with real money.
- Consider exchange-grade data and broker APIs for execution.
