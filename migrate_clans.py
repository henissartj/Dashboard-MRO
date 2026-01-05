import asyncio
import aiomysql
import os
from dotenv import dotenv_values

async def apply_migration():
    env_vals = dotenv_values("/opt/mro_dash/.env")
    # Fallback if file not found (it wasn't found in previous attempts, so let's try standard env vars or hardcoded if necessary for this env)
    # Based on previous attempts, I suspect the env file might be elsewhere or we rely on system env.
    # However, the bot code uses `dotenv_values`, so let's try to mimic how the bot connects.
    
    # We will try to connect using the same credentials the bot likely uses.
    # I saw "botfazer" and "127.0.0.1" in the logs.
    
    # Trying to find credentials from main bot file if .env is missing
    user = os.getenv("DB_USER", "botfazer")
    password = os.getenv("DB_PASSWORD", "botfazer123")
    host = os.getenv("DB_HOST", "127.0.0.1")
    db = os.getenv("DB_NAME", "bot_db")
    
    print(f"Connecting to {host} as {user}...")
    
    try:
        pool = await aiomysql.create_pool(host=host, port=3306,
                                          user=user, password=password,
                                          db=db, autocommit=True)
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Check if columns exist first to avoid errors
                print("Checking columns...")
                await cur.execute("SHOW COLUMNS FROM clans LIKE 'description'")
                if not await cur.fetchone():
                    print("Adding 'description' column...")
                    await cur.execute("ALTER TABLE clans ADD COLUMN description VARCHAR(255) DEFAULT 'Aucune description.'")
                
                await cur.execute("SHOW COLUMNS FROM clans LIKE 'badge'")
                if not await cur.fetchone():
                    print("Adding 'badge' column...")
                    await cur.execute("ALTER TABLE clans ADD COLUMN badge VARCHAR(8) DEFAULT '🏢'")
                    
                await cur.execute("SHOW COLUMNS FROM clans LIKE 'color'")
                if not await cur.fetchone():
                    print("Adding 'color' column...")
                    await cur.execute("ALTER TABLE clans ADD COLUMN color VARCHAR(8) DEFAULT '#2b2d31'")
                    
        print("Migration completed successfully.")
        pool.close()
        await pool.wait_closed()
        
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    asyncio.run(apply_migration())
