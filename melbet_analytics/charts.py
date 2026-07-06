import os
from pathlib import Path
from config import logger

def generate_charts(user_data: dict, output_dir: Path) -> list[str]:
    """
    Generates analytics charts (PnL over time, Deposit vs Withdrawal, Win/Loss ratio) 
    using matplotlib, if installed. Gracefully bypasses if matplotlib is not available.
    """
    generated_paths = []
    
    try:
        import matplotlib
        # Use a non-interactive backend to avoid GUI/thread errors in async environments
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("Matplotlib is not installed. Skipping graphical chart generation. "
                       "Install matplotlib using 'pip install matplotlib' to enable charts.")
        return generated_paths

    user_id = user_data.get("user_id", "UNKNOWN")
    bets = user_data.get("bets", [])
    deposits = user_data.get("deposits", [])
    withdrawals = user_data.get("withdrawals", [])
    
    # 1. Win/Loss Ratio Pie Chart
    if bets:
        try:
            wins = sum(1 for b in bets if b["status"] == "WIN")
            losses = sum(1 for b in bets if b["status"] == "LOSS")
            voids = sum(1 for b in bets if b["status"] == "VOID")
            
            labels = []
            sizes = []
            colors = []
            
            if wins > 0:
                labels.append('Wins')
                sizes.append(wins)
                colors.append('#2ECC71') # Green
            if losses > 0:
                labels.append('Losses')
                sizes.append(losses)
                colors.append('#E74C3C') # Red
            if voids > 0:
                labels.append('Void/Refund')
                sizes.append(voids)
                colors.append('#F1C40F') # Yellow
                
            if sizes:
                plt.figure(figsize=(6, 6))
                plt.pie(
                    sizes, labels=labels, colors=colors, autopct='%1.1f%%', 
                    startangle=140, textprops={'fontsize': 12, 'weight': 'bold'}
                )
                plt.title(f"Bet Distribution (Win/Loss/Void)\nUser: {user_id}", fontsize=14, weight='bold', pad=20)
                plt.tight_layout()
                
                pie_path = output_dir / f"win_loss_ratio_{user_id}.png"
                plt.savefig(pie_path, dpi=150)
                plt.close()
                generated_paths.append(str(pie_path))
                logger.info(f"Win/Loss ratio chart saved to: {pie_path}")
        except Exception as e:
            logger.error(f"Failed to generate Win/Loss pie chart: {e}", exc_info=True)

    # 2. Cumulative PnL Over Time
    if bets:
        try:
            import pandas as pd
            df_bets = pd.DataFrame(bets)
            # Try parsing dates and sorting
            df_bets["datetime"] = pd.to_datetime(df_bets["settlement_time"], errors='coerce')
            df_bets = df_bets.dropna(subset=["datetime"]).sort_values(by="datetime")
            
            if not df_bets.empty:
                df_bets["cumulative_pnl"] = df_bets["profit_loss"].cumsum()
                
                plt.figure(figsize=(10, 5))
                plt.plot(
                    df_bets["datetime"], df_bets["cumulative_pnl"], 
                    marker='o', color='#3498DB', linewidth=2, label='Cumulative PnL'
                )
                plt.axhline(0, color='red', linestyle='--', alpha=0.6)
                plt.title(f"Net Profit/Loss Trend Over Time\nUser: {user_id}", fontsize=14, weight='bold', pad=15)
                plt.xlabel("Date / Time of Settlement", fontsize=11)
                plt.ylabel("Cumulative Profit/Loss", fontsize=11)
                plt.grid(True, linestyle=':', alpha=0.6)
                plt.xticks(rotation=30)
                plt.tight_layout()
                
                pnl_path = output_dir / f"pnl_trend_{user_id}.png"
                plt.savefig(pnl_path, dpi=150)
                plt.close()
                generated_paths.append(str(pnl_path))
                logger.info(f"PnL trend chart saved to: {pnl_path}")
        except Exception as e:
            logger.error(f"Failed to generate PnL trend chart: {e}", exc_info=True)

    # 3. Deposits vs Withdrawals Bar Chart
    if deposits or withdrawals:
        try:
            success_deps = [d for d in deposits if d["status"] == "SUCCESS"]
            success_wds = [w for w in withdrawals if w["status"] == "SUCCESS"]
            
            total_dep = sum(d["amount"] for d in success_deps)
            total_wd = sum(w["amount"] for w in success_wds)
            
            plt.figure(figsize=(7, 5))
            categories = ['Total Deposits', 'Total Withdrawals']
            amounts = [total_dep, total_wd]
            colors = ['#27AE60', '#C0392B']
            
            bars = plt.bar(categories, amounts, color=colors, width=0.5)
            plt.title(f"Financial Summary (Deposits vs Withdrawals)\nUser: {user_id}", fontsize=14, weight='bold', pad=15)
            plt.ylabel("Total Amount", fontsize=11)
            
            # Value labels on top of bars
            for bar in bars:
                height = bar.get_height()
                plt.text(
                    bar.get_x() + bar.get_width()/2.0, height + (height * 0.01 + 1), 
                    f"{height:,.2f}", ha='center', va='bottom', weight='bold'
                )
                
            plt.grid(axis='y', linestyle=':', alpha=0.6)
            plt.tight_layout()
            
            fin_path = output_dir / f"financial_summary_{user_id}.png"
            plt.savefig(fin_path, dpi=150)
            plt.close()
            generated_paths.append(str(fin_path))
            logger.info(f"Financial summary chart saved to: {fin_path}")
        except Exception as e:
            logger.error(f"Failed to generate Financial Summary chart: {e}", exc_info=True)

    return generated_paths
