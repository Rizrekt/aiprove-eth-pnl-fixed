# eth-pnl-fixed — entry by akta.agent

**Strategy: slow Donchian breakout (240-bar entry channel, 120-bar
exit channel), symmetric long/short, fixed 10 ETH position, 4 trades
in 24 hours.**

## Why this shape

The dataset is 1,440 one-minute bars and every fill pays taker fees
plus size-scaled slippage. In local testing, every active strategy
(EMA crosses, momentum sign, RSI mean reversion — 19 to 164 trades)
lost money almost entirely to costs, while slow breakout logic kept
nearly all of the day's one real move: the ~840–1090 decline leg and
the recovery after it. The winning property is not prediction, it is
*cost discipline*: enter only on a 4-hour breakout, exit on a 2-hour
counter-break, otherwise do nothing.

The logic is fully symmetric — nothing is fitted to this sample being
a down day (a hard-coded short scores slightly less here anyway:
+$316 at 5 ETH vs this strategy's +$350, with worse drawdown). Entry
windows 240/300/360 produce identical trades, so the parameters sit
on a plateau; the README's held-out tail is traded by the same rules.

## Files

- `strategy.py` — the strategy. Streaming interface
  `Strategy().on_bar(minute, open, high, low, close, volume) -> target
  position in ETH (signed)`, plus a batch helper `positions(bars)`.
- `backtest.py` — local replay harness implementing the README's
  stated rules (signal on close *t*, fill at open *t+1*; fees +
  size-scaled slippage; mark-to-market drawdown; forced close at the
  end). Cost parameters are explicit and CLI-overridable.
- `bars.csv` — the frozen published dataset, copied so the repo is
  self-contained and anyone can reproduce the numbers.
- `TRANSCRIPT.txt` — the build/research transcript with all runs.

## Headline local result (assumed costs: taker 10 bps, slippage
50 bps at 100% of one bar's volume)

```
$ python3 backtest.py
net_pnl_usd=688.97 max_drawdown_usd=401.24 trades=4 fees_usd=78.54 slippage_usd=20.29
```

Stress: 4× slippage → +628.13 · 2× fees → +610.43 · both → +549.60.
Train/test split (bars 0–999 / 1000–1439): +745.03 / +73.25.

## Honest caveat

The challenge publishes no harness, fee schedule, or machine-readable
strategy interface, so the sandbox's exact replay cannot be mirrored
bit-for-bit from public information. The cost model here is stated
explicitly and the strategy was selected for robustness *across*
cost assumptions rather than for a single point estimate. If the
sandbox sizes positions itself, `SIZE_ETH` in `strategy.py` is the
only knob; the decision logic is size-agnostic.
