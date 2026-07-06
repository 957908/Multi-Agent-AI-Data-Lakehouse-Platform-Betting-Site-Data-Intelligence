import pandas as pd
from datetime import datetime
from config import logger

def calculate_overall_metrics(user_data: dict) -> dict:
    """Calculates overall high-level metrics for the account."""
    logger.info("Computing overall account analytics...")
    
    deposits = user_data.get("deposits", [])
    withdrawals = user_data.get("withdrawals", [])
    bets = user_data.get("bets", [])
    
    # Filter only SUCCESS transactions for totals
    success_deps = [d for d in deposits if d["status"] == "SUCCESS"]
    success_wds = [w for w in withdrawals if w["status"] == "SUCCESS"]
    
    total_deposits = sum(d["amount"] for d in success_deps)
    total_withdrawals = sum(w["amount"] for w in success_wds)
    
    total_bets = len(bets)
    total_wins = sum(1 for b in bets if b["status"] == "WIN")
    total_losses = sum(1 for b in bets if b["status"] == "LOSS")
    
    total_stake = sum(b["stake"] for b in bets)
    net_pnl = sum(b["profit_loss"] for b in bets)
    
    # ROI % = (Net PnL / Total Stake) * 100
    roi = (net_pnl / total_stake * 100) if total_stake > 0 else 0.0
    
    metrics = {
        "total_deposits": total_deposits,
        "total_withdrawals": total_withdrawals,
        "total_bets": total_bets,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "total_stake": total_stake,
        "net_pnl": net_pnl,
        "roi": round(roi, 2)
    }
    
    logger.info(f"Analytics computed: Net PnL={net_pnl}, ROI={metrics['roi']}%, Total Bets={total_bets}")
    return metrics

def generate_periodic_summaries(user_data: dict) -> dict:
    """Generates daily, weekly, and monthly summaries for transactions and betting."""
    logger.info("Generating periodic activity summaries...")
    
    summaries = {
        "daily": [],
        "weekly": [],
        "monthly": []
    }
    
    bets = user_data.get("bets", [])
    if not bets:
        logger.info("No betting records found; skipping periodic summaries.")
        return summaries
        
    df_bets = pd.DataFrame(bets)
    
    # Try parsing settlement times
    try:
        # Standardize dates, coerce errors
        df_bets["datetime"] = pd.to_datetime(df_bets["settlement_time"], errors='coerce')
        # Drop rows where datetime could not be parsed
        df_bets = df_bets.dropna(subset=["datetime"])
    except Exception as e:
        logger.warning(f"Failed to parse dates in betting data: {e}")
        return summaries

    if df_bets.empty:
        return summaries

    # Helper function to group and aggregate
    def aggregate_by_period(df, freq):
        grouped = df.groupby(pd.Grouper(key="datetime", freq=freq))
        records = []
        for period, group in grouped:
            if group.empty:
                continue
            
            p_bets = len(group)
            p_wins = sum(group["status"] == "WIN")
            p_losses = sum(group["status"] == "LOSS")
            p_stake = float(group["stake"].sum())
            p_pnl = float(group["profit_loss"].sum())
            p_roi = (p_pnl / p_stake * 100) if p_stake > 0 else 0.0
            
            # Format period string based on frequency
            if freq == 'D':
                period_str = period.strftime('%Y-%m-%d')
            elif freq == 'W-MON':
                # Start of week
                period_str = period.strftime('%Y-%m-%d')
            else: # Month
                period_str = period.strftime('%Y-%m')
                
            records.append({
                "period": period_str,
                "bets_count": p_bets,
                "wins": p_wins,
                "losses": p_losses,
                "total_stake": round(p_stake, 2),
                "profit_loss": round(p_pnl, 2),
                "roi": round(p_roi, 2)
            })
        return records

    summaries["daily"] = aggregate_by_period(df_bets, 'D')
    summaries["weekly"] = aggregate_by_period(df_bets, 'W-MON')
    summaries["monthly"] = aggregate_by_period(df_bets, 'ME')  # 'ME' is month-end frequency in newer pandas

    return summaries
