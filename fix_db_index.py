import asyncio
import aiomysql
import os
from dotenv import load_dotenv, dotenv_values

async def add_index():
    env_path = os.getenv("DOTENV_PATH", "/home/app/bot-discord/.env")
    try:
        env_vals = dotenv_values(env_path)
    except Exception:
        env_vals = dotenv_values()

    host = os.getenv("DB_HOST", "127.0.0.1")
    db = os.getenv("DB_NAME", "bot_fazer")
    user = os.getenv("DB_USER", "botfazer")
    pwd = os.getenv("DB_PASSWORD", "")
    
    # Fallback to env file if env vars not set
    if not pwd and "DB_PASSWORD" in env_vals:
        pwd = env_vals["DB_PASSWORD"]
    if not user and "DB_USER" in env_vals:
        user = env_vals["DB_USER"]
        
    print(f"Connecting to {host}...")
    pool = await aiomysql.create_pool(host=host, db=db, user=user, password=pwd, autocommit=True)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            print("Checking existing indexes...")
            await cur.execute("SHOW INDEX FROM transactions WHERE Key_name = 'idx_transactions_created_at'")
            if await cur.fetchone():
                print("Index already exists.")
            else:
                print("Adding index idx_transactions_created_at...")
                await cur.execute("CREATE INDEX idx_transactions_created_at ON transactions(created_at)")
                print("Index added successfully.")
            
            # Also check for type + created_at composite index which might be even better for the specific query
            # Query is: WHERE type='credit' AND created_at >= ...
            print("Checking composite index idx_transactions_type_created...")
            await cur.execute("SHOW INDEX FROM transactions WHERE Key_name = 'idx_transactions_type_created'")
            if await cur.fetchone():
                print("Composite index already exists.")
            else:
                print("Adding composite index idx_transactions_type_created...")
                await cur.execute("CREATE INDEX idx_transactions_type_created ON transactions(type, created_at)")
                print("Composite index added successfully.")

    pool.close()
    await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(add_index())
