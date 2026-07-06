import sqlite3
from datetime import datetime
from config import DATABASE_FILE, logger

class DatabaseManager:
    def __init__(self, db_path=DATABASE_FILE):
        self.db_path = db_path
        self.init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes database tables if they do not exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        username TEXT,
                        wallet_balance REAL,
                        currency TEXT,
                        account_status TEXT,
                        updated_at TEXT
                    )
                """)
                
                # Deposits table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS deposits (
                        ref_number TEXT PRIMARY KEY,
                        amount REAL,
                        datetime TEXT,
                        method TEXT,
                        status TEXT,
                        user_id TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Withdrawals table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS withdrawals (
                        ref_number TEXT PRIMARY KEY,
                        amount REAL,
                        datetime TEXT,
                        status TEXT,
                        user_id TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Bets table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bets (
                        bet_id TEXT PRIMARY KEY,
                        event_name TEXT,
                        stake REAL,
                        odds REAL,
                        status TEXT,
                        profit_loss REAL,
                        settlement_time TEXT,
                        user_id TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Analytics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        total_deposits REAL,
                        total_withdrawals REAL,
                        total_bets INTEGER,
                        total_wins INTEGER,
                        total_losses INTEGER,
                        net_pnl REAL,
                        roi REAL,
                        updated_at TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                conn.commit()
                logger.info("SQLite Database initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing database: {e}", exc_info=True)
            raise

    def save_user(self, user_id, username, wallet_balance, currency, account_status):
        """Saves or updates user profile information."""
        try:
            updated_at = datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (user_id, username, wallet_balance, currency, account_status, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username=excluded.username,
                        wallet_balance=excluded.wallet_balance,
                        currency=excluded.currency,
                        account_status=excluded.account_status,
                        updated_at=excluded.updated_at
                """, (user_id, username, wallet_balance, currency, account_status, updated_at))
                conn.commit()
                logger.info(f"User profile saved: {user_id}")
        except Exception as e:
            logger.error(f"Failed to save user {user_id}: {e}", exc_info=True)

    def save_deposits(self, deposits_list, user_id):
        """Saves a list of deposit records."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for dep in deposits_list:
                    cursor.execute("""
                        INSERT INTO deposits (ref_number, amount, datetime, method, status, user_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(ref_number) DO UPDATE SET
                            amount=excluded.amount,
                            datetime=excluded.datetime,
                            method=excluded.method,
                            status=excluded.status,
                            user_id=excluded.user_id
                    """, (dep["ref_number"], dep["amount"], dep["datetime"], dep["method"], dep["status"], user_id))
                conn.commit()
                logger.info(f"Saved/Updated {len(deposits_list)} deposits for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save deposits for user {user_id}: {e}", exc_info=True)

    def save_withdrawals(self, withdrawals_list, user_id):
        """Saves a list of withdrawal records."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for wd in withdrawals_list:
                    cursor.execute("""
                        INSERT INTO withdrawals (ref_number, amount, datetime, status, user_id)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(ref_number) DO UPDATE SET
                            amount=excluded.amount,
                            datetime=excluded.datetime,
                            status=excluded.status,
                            user_id=excluded.user_id
                    """, (wd["ref_number"], wd["amount"], wd["datetime"], wd["status"], user_id))
                conn.commit()
                logger.info(f"Saved/Updated {len(withdrawals_list)} withdrawals for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save withdrawals for user {user_id}: {e}", exc_info=True)

    def save_bets(self, bets_list, user_id):
        """Saves a list of bet records."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for bet in bets_list:
                    cursor.execute("""
                        INSERT INTO bets (bet_id, event_name, stake, odds, status, profit_loss, settlement_time, user_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(bet_id) DO UPDATE SET
                            event_name=excluded.event_name,
                            stake=excluded.stake,
                            odds=excluded.odds,
                            status=excluded.status,
                            profit_loss=excluded.profit_loss,
                            settlement_time=excluded.settlement_time,
                            user_id=excluded.user_id
                    """, (bet["bet_id"], bet["event_name"], bet["stake"], bet["odds"], bet["status"], 
                          bet["profit_loss"], bet["settlement_time"], user_id))
                conn.commit()
                logger.info(f"Saved/Updated {len(bets_list)} bets for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save bets for user {user_id}: {e}", exc_info=True)

    def save_analytics(self, user_id, stats):
        """Saves the computed analytics metrics."""
        try:
            updated_at = datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO analytics (user_id, total_deposits, total_withdrawals, total_bets, 
                                           total_wins, total_losses, net_pnl, roi, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, stats["total_deposits"], stats["total_withdrawals"], stats["total_bets"],
                      stats["total_wins"], stats["total_losses"], stats["net_pnl"], stats["roi"], updated_at))
                conn.commit()
                logger.info(f"Saved analytical snapshot for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to save analytics for user {user_id}: {e}", exc_info=True)

    def get_user_data(self, user_id):
        """Retrieves complete database records for a user as a dictionary of lists."""
        data = {
            "user_id": user_id,
            "wallet_balance": 0.0,
            "username": "",
            "currency": "",
            "account_status": "",
            "deposits": [],
            "withdrawals": [],
            "bets": []
        }
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Fetch user details
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                user_row = cursor.fetchone()
                if user_row:
                    data["wallet_balance"] = user_row["wallet_balance"]
                    data["username"] = user_row["username"]
                    data["currency"] = user_row["currency"]
                    data["account_status"] = user_row["account_status"]

                # Fetch deposits
                cursor.execute("SELECT amount, datetime, method, status, ref_number FROM deposits WHERE user_id = ?", (user_id,))
                data["deposits"] = [dict(row) for row in cursor.fetchall()]

                # Fetch withdrawals
                cursor.execute("SELECT amount, datetime, status, ref_number FROM withdrawals WHERE user_id = ?", (user_id,))
                data["withdrawals"] = [dict(row) for row in cursor.fetchall()]

                # Fetch bets
                cursor.execute("SELECT bet_id, event_name, stake, odds, status, profit_loss, settlement_time FROM bets WHERE user_id = ?", (user_id,))
                data["bets"] = [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Error reading data for user {user_id}: {e}", exc_info=True)
        return data
