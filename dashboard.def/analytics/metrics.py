"""Return and risk analytics.

Pure functions over pandas objects: no database access, no provider, no web
framework. This is the layer the Dash app and the desktop app both import,
so a figure shown in one is computed by the same code as in the other.
"""
import numpy as np
import pandas as pd

from config import RISK_FREE_RATE, TRADING_DAYS


# ---------------------------------------------------------------------------
# Returns
# ---------------------------------------------------------------------------

def log_returns(prices: pd.Series) -> pd.Series:
    """Daily continuously compounded returns. First observation is dropped."""
    return np.log(prices / prices.shift(1)).dropna()


def simple_returns(prices: pd.Series) -> pd.Series:
    """Arithmetic returns, used where log returns are not appropriate."""
    return prices.pct_change().dropna()


def resample_returns(prices: pd.Series, frequency: str = "D") -> pd.Series:
    """Log returns at the requested frequency.

    frequency: 'D' daily, 'W' weekly, 'ME' month end, 'YE' year end.
    Prices are resampled first and returns computed on the resampled series,
    which is not the same as summing daily returns when data is missing.
    """
    if frequency == "D":
        return log_returns(prices)
    return log_returns(prices.resample(frequency).last().dropna())


def cumulative_return(prices: pd.Series) -> pd.Series:
    """Price series rebased to 100 at the first observation."""
    if prices.empty:
        return prices
    return prices / prices.iloc[0] * 100


def total_return(prices: pd.Series) -> float:
    """Overall return over the whole period, as a decimal."""
    if len(prices) < 2:
        return float("nan")
    return float(prices.iloc[-1] / prices.iloc[0] - 1)


# ---------------------------------------------------------------------------
# Risk and risk-adjusted performance
# ---------------------------------------------------------------------------

def annualised_return(returns: pd.Series) -> float:
    """Mean daily log return scaled to one year."""
    return float(returns.mean() * TRADING_DAYS)


def annualised_volatility(returns: pd.Series) -> float:
    """Standard deviation scaled by the square root of time."""
    return float(returns.std(ddof=1) * np.sqrt(TRADING_DAYS))


def sharpe_ratio(returns: pd.Series, risk_free: float = RISK_FREE_RATE) -> float:
    """Excess return per unit of total volatility."""
    volatility = annualised_volatility(returns)
    if volatility == 0 or np.isnan(volatility):
        return float("nan")
    return (annualised_return(returns) - risk_free) / volatility


def sortino_ratio(returns: pd.Series, risk_free: float = RISK_FREE_RATE) -> float:
    """Like Sharpe, but only downside deviation is treated as risk."""
    downside = returns[returns < 0]
    if downside.empty:
        return float("nan")
    downside_vol = float(downside.std(ddof=1) * np.sqrt(TRADING_DAYS))
    if downside_vol == 0:
        return float("nan")
    return (annualised_return(returns) - risk_free) / downside_vol


def drawdown_series(prices: pd.Series) -> pd.Series:
    """Percentage distance from the running maximum, at every date."""
    return prices / prices.cummax() - 1


def max_drawdown(prices: pd.Series) -> float:
    """Worst peak-to-trough decline over the period, as a negative number."""
    if prices.empty:
        return float("nan")
    return float(drawdown_series(prices).min())


def value_at_risk(returns: pd.Series, confidence: float = 0.95) -> float:
    """Historical VaR: empirical quantile of the return distribution.

    No distributional assumption is made, which matters because financial
    returns have fatter tails than a normal distribution.
    """
    if returns.empty:
        return float("nan")
    return float(np.percentile(returns, (1 - confidence) * 100))


def expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float:
    """Average loss in the tail beyond the VaR threshold."""
    threshold = value_at_risk(returns, confidence)
    tail = returns[returns <= threshold]
    return float(tail.mean()) if not tail.empty else float("nan")


def beta_vs_benchmark(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Sensitivity to the benchmark, on the overlapping dates only."""
    aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    variance = aligned.iloc[:, 1].var(ddof=1)
    if variance == 0:
        return float("nan")
    return float(aligned.cov().iloc[0, 1] / variance)


def tracking_error(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Annualised standard deviation of the return difference."""
    aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    difference = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    return float(difference.std(ddof=1) * np.sqrt(TRADING_DAYS))


# ---------------------------------------------------------------------------
# Aggregates used by the dashboard
# ---------------------------------------------------------------------------

def summary(prices: pd.Series, benchmark: pd.Series | None = None) -> dict:
    """Metric block shown on the instrument risk page."""
    returns = log_returns(prices)
    result = {
        "Rendimento totale": total_return(prices),
        "Rendimento annualizzato": annualised_return(returns),
        "Volatilità annualizzata": annualised_volatility(returns),
        "Sharpe ratio": sharpe_ratio(returns),
        "Sortino ratio": sortino_ratio(returns),
        "Max drawdown": max_drawdown(prices),
        "VaR storico 95% (1g)": value_at_risk(returns),
        "Expected shortfall 95%": expected_shortfall(returns),
        "Osservazioni": len(returns),
    }
    if benchmark is not None and not benchmark.empty:
        benchmark_returns = log_returns(benchmark)
        result["Beta vs benchmark"] = beta_vs_benchmark(returns, benchmark_returns)
        result["Tracking error"] = tracking_error(returns, benchmark_returns)
    return result


def market_statistics(closes: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional table: one row per instrument in the market."""
    rows = []
    for column in closes.columns:
        series = closes[column].dropna()
        if len(series) < 2:
            continue
        returns = log_returns(series)
        rows.append({
            "Strumento": column,
            "Rendimento ann. (%)": annualised_return(returns) * 100,
            "Volatilità ann. (%)": annualised_volatility(returns) * 100,
            "Sharpe": sharpe_ratio(returns),
            "Max DD (%)": max_drawdown(series) * 100,
            "VaR 95% (%)": value_at_risk(returns) * 100,
        })
    return pd.DataFrame(rows)


def market_aggregates(closes: pd.DataFrame) -> dict:
    """Market-level figures required by the brief: mean and median across
    the instruments quoted in that market."""
    statistics = market_statistics(closes)
    if statistics.empty:
        return {}
    return {
        "Numero strumenti": len(statistics),
        "Rendimento medio ann. (%)": statistics["Rendimento ann. (%)"].mean(),
        "Rendimento mediano ann. (%)": statistics["Rendimento ann. (%)"].median(),
        "Volatilità media ann. (%)": statistics["Volatilità ann. (%)"].mean(),
        "Dispersione rendimenti (dev.std, %)": statistics["Rendimento ann. (%)"].std(ddof=1),
        "Sharpe medio": statistics["Sharpe"].mean(),
    }


def correlation_matrix(closes: pd.DataFrame) -> pd.DataFrame:
    """Correlation of daily log returns between the instruments of a market."""
    return closes.apply(log_returns).corr()


def rolling_volatility(prices: pd.Series, window: int = 60) -> pd.Series:
    """Annualised volatility on a moving window, for the time-series chart."""
    return log_returns(prices).rolling(window).std(ddof=1) * np.sqrt(TRADING_DAYS)