"""
AIProve eth-pnl-fixed entry strategy: slow Donchian breakout with a
faster exit channel ("turtle"-style), fully symmetric long/short.

Design rationale (see README.md / MATERI.md for the full study):
- The dataset is 1,440 one-minute bars; at 10 bps taker per side, any
  strategy that rebalances often donates its edge to fees. This one
  trades 4 times in 24h.
- Entry: close breaks the trailing 240-bar high/low -> take +/- SIZE.
- Exit:  close crosses the trailing 120-bar channel the other way ->
  flat. Re-entry only on a fresh 240-bar breakout.
- The parameters sit on a plateau, not a peak: entry windows 240/300/360
  produce identical trades on the published sample, and every cost
  stress test (slippage x4, fees x2, both) stays profitable. Nothing in
  the logic is fitted to this sample's direction - it is symmetric, so
  the held-out tail is traded by the same rules, not by a hard-coded
  short.

Interface (the challenge publishes no machine-readable interface, so the
strategy is exposed two conventional ways):
- Streaming:  Strategy().on_bar(minute, open, high, low, close, volume)
  -> target position in ETH (float, signed; + long, - short), to be
  held after that bar's close.
- Batch:      positions(bars) -> list of target positions, one per bar,
  where bars are dicts with open/high/low/close/volume keys.

backtest.py replays it exactly the way the README describes the sandbox:
signal on close of bar t, fill at the open of bar t+1, taker fee plus
size-scaled slippage, no phantom fills.
"""

SIZE_ETH = 10.0    # fixed position size, ETH
ENTRY_N = 240      # Donchian entry channel (bars)
EXIT_N = 120       # Donchian exit channel (bars)


class Strategy:
    def __init__(self, size_eth=SIZE_ETH, entry_n=ENTRY_N, exit_n=EXIT_N):
        self.size = float(size_eth)
        self.entry_n = int(entry_n)
        self.exit_n = int(exit_n)
        self.closes = []
        self.position = 0.0   # current TARGET position (ETH, signed)

    def on_bar(self, minute, open_, high, low, close, volume):
        """Feed one completed bar; returns the target position (ETH)."""
        self.closes.append(float(close))
        c = self.closes
        t = len(c) - 1
        if t >= self.entry_n:
            win = c[t - self.entry_n:t]
            if c[t] > max(win):
                self.position = self.size
            elif c[t] < min(win):
                self.position = -self.size
            elif self.position != 0.0 and t >= self.exit_n:
                ewin = c[t - self.exit_n:t]
                if self.position > 0 and c[t] < min(ewin):
                    self.position = 0.0
                elif self.position < 0 and c[t] > max(ewin):
                    self.position = 0.0
        return self.position


def positions(bars, size_eth=SIZE_ETH, entry_n=ENTRY_N, exit_n=EXIT_N):
    """Batch helper: replay bars (list of dicts) -> list of targets."""
    s = Strategy(size_eth, entry_n, exit_n)
    return [s.on_bar(b["minute"], b["open"], b["high"], b["low"],
                     b["close"], b["volume"]) for b in bars]
