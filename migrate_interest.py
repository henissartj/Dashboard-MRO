import asyncio
import aiomysql
import os
from dotenv import load_dotenv

async def apply_migration():
    load_dotenv()
    
    user = os.getenv("DB_USER", "botfazer")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "127.0.0.1")
    db = os.getenv("DB_NAME", "bot_fazer")
    
    print(f"Connecting to {host} as {user}...")
    
    try:
        pool = await aiomysql.create_pool(host=host, port=3306,
                                          user=user, password=password,
                                          db=db, autocommit=True)
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                print("Checking 'last_interest' column in 'users' table...")
                await cur.execute("SHOW COLUMNS FROM users LIKE 'last_interest'")
                if not await cur.fetchone():
                    print("Adding 'last_interest' column...")
                    await cur.execute("ALTER TABLE users ADD COLUMN last_interest TIMESTAMP NULL")
                else:
                    print("'last_interest' column already exists.")

                print("Checking 'bank_tier' column in 'users' table...")
                await cur.execute("SHOW COLUMNS FROM users LIKE 'bank_tier'")
                if not await cur.fetchone():
                    print("Adding 'bank_tier' column...")
                    await cur.execute("ALTER TABLE users ADD COLUMN bank_tier INT DEFAULT 0")
                else:
                    print("'bank_tier' column already exists.")
                    
        print("Migration completed successfully.")
        pool.close()
        await pool.wait_closed()
        
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    asyncio.run(apply_migration())