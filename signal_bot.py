from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import pandas as pd
import yfinance as yf


@dataclass
class SignalResult:
    symbol: str
    signal: str
    close: float
    fast_sma: float
    slow_sma: float
    rsi: float
    reason: str


def to_nse_symbol(raw_symbol: str) -> str:
    symbol = raw_symbol.strip().upper()
    if symbol.endswith(".NS"):
        return symbol
    return f"{symbol}.NS"


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def calculate_signal(
    data: pd.DataFrame,
    symbol: str,
    fast_window: int = 20,
    slow_window: int = 50,
) -> SignalResult:
    if len(data) < slow_window + 2:
        raise ValueError(f"Not enough historical candles for {symbol}. Need at least {slow_window + 2} rows.")

    close = data["Close"].astype(float)
    fast_sma = close.rolling(window=fast_window).mean()
    slow_sma = close.rolling(window=slow_window).mean()
    rsi = calculate_rsi(close)

    prev_fast = fast_sma.iloc[-2]
    prev_slow = slow_sma.iloc[-2]
    curr_fast = fast_sma.iloc[-1]
    curr_slow = slow_sma.iloc[-1]
    curr_rsi = rsi.iloc[-1]
    curr_close = close.iloc[-1]

    if prev_fast <= prev_slow and curr_fast > curr_slow and curr_rsi < 70:
        signal = "BUY"
        reason = "20-SMA crossed above 50-SMA with RSI below overbought threshold"
    elif prev_fast >= prev_slow and curr_fast < curr_slow and curr_rsi > 30:
        signal = "SELL"
        reason = "20-SMA crossed below 50-SMA with RSI above oversold threshold"
    else:
        signal = "HOLD"
        reason = "No fresh crossover confirmation"

    return SignalResult(
        symbol=symbol,
        signal=signal,
        close=round(curr_close, 2),
        fast_sma=round(curr_fast, 2),
        slow_sma=round(curr_slow, 2),
        rsi=round(float(curr_rsi), 2),
        reason=reason,
    )


def fetch_ohlc(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    data = ticker.history(period=period, interval=interval, auto_adjust=True)
    if data.empty:
        raise ValueError(f"No market data returned for {symbol}. Verify the symbol or try again later.")
    return data


def format_message(results: Iterable[SignalResult]) -> str:
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"📈 India Market Signal Update ({timestamp})"]
    for result in results:
        lines.append(
            "\n".join(
                [
                    f"{result.symbol}: {result.signal}",
                    f"Price: ₹{result.close}",
                    f"SMA20/SMA50: {result.fast_sma}/{result.slow_sma}",
                    f"RSI(14): {result.rsi}",
                    f"Reason: {result.reason}",
                ]
            )
        )
        lines.append("-" * 24)
    lines.append("⚠️ Educational use only, not investment advice.")
    return "\n".join(lines)


def send_telegram(message: str, bot_token: str, chat_id: str) -> None:
    from telegram import Bot

    bot = Bot(token=bot_token)
    bot.send_message(chat_id=chat_id, text=message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate BUY/SELL/HOLD signals for Indian stocks.")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["RELIANCE", "TCS", "INFY"],
        help="Stock symbols, with or without .NS suffix (example: RELIANCE TCS INFY).",
    )
    parser.add_argument("--period", default="6mo", help="History window passed to Yahoo Finance (default: 6mo).")
    parser.add_argument("--interval", default="1d", help="Candle interval (default: 1d).")
    parser.add_argument(
        "--send-telegram",
        action="store_true",
        help="Send the generated message to Telegram using TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results: list[SignalResult] = []

    for raw_symbol in args.symbols:
        symbol = to_nse_symbol(raw_symbol)
        try:
            data = fetch_ohlc(symbol=symbol, period=args.period, interval=args.interval)
            results.append(calculate_signal(data=data, symbol=symbol))
        except Exception as exc:  # noqa: BLE001
            results.append(
                SignalResult(
                    symbol=symbol,
                    signal="ERROR",
                    close=0,
                    fast_sma=0,
                    slow_sma=0,
                    rsi=0,
                    reason=str(exc),
                )
            )

    message = format_message(results)
    print(message)

    if args.send_telegram:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        if not token or not chat_id:
            raise RuntimeError("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID before using --send-telegram.")
        send_telegram(message=message, bot_token=token, chat_id=chat_id)


if __name__ == "__main__":
    main()
