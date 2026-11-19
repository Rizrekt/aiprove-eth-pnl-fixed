"""
Local replay harness for the eth-backtest challenge.

The official repo publishes the dataset and the metric in prose only -
no harness and no fee schedule. This harness is a faithful
reimplementation of the README's stated rules:

  - signal decided on the CLOSE of bar t, executed at the OPEN of t+1
    (no lookahead, no phantom fills);
  - costs = maker/taker fees + slippage scaled by size:
      fee       = fee_rate * |delta| * exec_price      (taker default)
      slippage  = min(cap, slip_k * |delta| / bar_volume) applied
                  against the trader (buys pay up, sells get less);
  - equity marked to market at every close; max drawdown on that curve;
  - any open position is force-closed at the final close, with costs.

Default cost parameters are Binance-spot-like (the dataset is Binance
ETH/USDT spot): taker 10 bps, slippage 50 bps at 100% participation of
one bar's volume. Both are CLI-overridable for stress tests:

  python3 backtest.py                      # headline run
  python3 backtest.py --slip-k 0.02        # 4x slippage stress
  python3 backtest.py --fee 0.002          # 20 bps fee stress
  python3 backtest.py --size 5             # 5 ETH instead of 10
"""
import argparse, csv, math, sys

sys.path.insert(0, ".")
from strategy import Strategy

MAKER_FEE = 0.0010
TAKER_FEE = 0.0010
SLIP_K = 0.005      # slippage fraction at 100% participation (= 50 bps)
SLIP_CAP = 0.02     # 200 bps


def load_bars(path):
    rows = list(csv.DictReader(open(path)))
    return [dict(minute=int(r["minute"]), open=float(r["open"]),
                 high=float(r["high"]), low=float(r["low"]),
                 close=float(r["close"]), volume=float(r["volume"]))
            for r in rows]


def run(bars, size=10.0, fee=TAKER_FEE, slip_k=SLIP_K):
    strat = Strategy(size_eth=size)
    cash, pos = 0.0, 0.0
    fees = slip_cost = 0.0
    trades = []
    equity = []
    pending = 0.0
    for t, b in enumerate(bars):
        if t > 0:
            delta = pending - pos
            if abs(delta) > 1e-9:
                part = abs(delta) / b["volume"] if b["volume"] > 0 else 1.0
                slip = min(SLIP_CAP, slip_k * part)
                px = b["open"] * (1 + slip) if delta > 0 else b["open"] * (1 - slip)
                f = fee * abs(delta) * px
                cash -= delta * px + f
                fees += f
                slip_cost += abs(delta) * b["open"] * slip
                trades.append((b["minute"], delta, px, f))
                pos = pending
        pending = strat.on_bar(b["minute"], b["open"], b["high"],
                               b["low"], b["close"], b["volume"])
        equity.append(cash + pos * b["close"])
    if abs(pos) > 1e-9:  # force close at final close, with costs
        b = bars[-1]
        part = abs(pos) / b["volume"] if b["volume"] > 0 else 1.0
        slip = min(SLIP_CAP, slip_k * part)
        px = b["close"] * (1 - slip) if pos > 0 else b["close"] * (1 + slip)
        f = fee * abs(pos) * px
        cash += pos * px - f
        fees += f
        slip_cost += abs(pos) * b["close"] * slip
        trades.append((b["minute"], -pos, px, f))
        equity[-1] = cash
    peak, max_dd = -math.inf, 0.0
    for v in equity:
        peak = max(peak, v)
        max_dd = max(max_dd, peak - v)
    return dict(net_pnl=cash, max_dd=max_dd, n_trades=len(trades),
                fees=fees, slippage=slip_cost, trades=trades)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bars", default="bars.csv")
    ap.add_argument("--size", type=float, default=10.0)
    ap.add_argument("--fee", type=float, default=TAKER_FEE)
    ap.add_argument("--slip-k", type=float, default=SLIP_K)
    a = ap.parse_args()
    bars = load_bars(a.bars)
    m = run(bars, size=a.size, fee=a.fee, slip_k=a.slip_k)
    print(f"bars={len(bars)} size={a.size} ETH fee={a.fee} slip_k={a.slip_k}")
    for minute, delta, px, f in m["trades"]:
        print(f"  trade minute={minute:5d} delta={delta:+6.1f} ETH px={px:9.2f} fee={f:6.2f}")
    print(f"net_pnl_usd={m['net_pnl']:.2f} max_drawdown_usd={m['max_dd']:.2f} "
          f"trades={m['n_trades']} fees_usd={m['fees']:.2f} slippage_usd={m['slippage']:.2f}")


if __name__ == "__main__":
    main()
