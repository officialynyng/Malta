from cogs.database.transactions_table import transactions
from cogs.exp_config import engine
import sqlalchemy as db
from datetime import datetime, timezone, timedelta

# Define CST timezone
CST = timezone(timedelta(hours=-6))

def now_cst():
    return datetime.now(CST)

def log_transaction(user_id: int, amount: int, type_: str, description: str = "", max_per_user: int = 100):
    with engine.begin() as conn:
        # Insert new transaction
        stmt = db.insert(transactions).values(
            user_id=user_id,
            amount=amount,
            type=type_,
            description=description,
            timestamp=now_cst()
        )
        conn.execute(stmt)

        # Delete oldest if over cap
        subquery = (
            select(transactions.c.id)
            .where(transactions.c.user_id == user_id)
            .order_by(desc(transactions.c.timestamp))
            .offset(max_per_user)
        )
        ids_to_delete = [row.id for row in conn.execute(subquery).fetchall()]
        if ids_to_delete:
            conn.execute(transactions.delete().where(transactions.c.id.in_(ids_to_delete)))

        print(f"[DEBUG]📘 Logged transaction for user {user_id}: {amount} ({type_}) - {description}")
