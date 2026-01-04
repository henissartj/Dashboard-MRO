import asyncio
import aiomysql
import os

async def check():
    try:
        pool = await aiomysql.create_pool(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            db=os.getenv("DB_NAME", "bot_fazer"),
            user=os.getenv("DB_USER", "botfazer"),
            password=os.getenv("DB_PASSWORD", ""),
            autocommit=True
        )
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DESCRIBE users")
                rows = await cur.fetchall()
                print("Columns in users table:")
                columns = [r[0] for r in rows]
                print(columns)
                
                if "bank_2" not in columns:
                    print("Adding bank_2...")
                    await cur.execute("ALTER TABLE users ADD COLUMN bank_2 BIGINT NOT NULL DEFAULT 0")
                if "bank_3" not in columns:
                    print("Adding bank_3...")
                    await cur.execute("ALTER TABLE users ADD COLUMN bank_3 BIGINT NOT NULL DEFAULT 0")
                    
    except Exception as e:
        print(e)
    finally:
        pool.close()
        await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(check())
