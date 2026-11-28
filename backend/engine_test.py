import sys, os, asyncio
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

os.environ['PYTHONUTF8'] = '1'
sys.path.insert(0, '.')
from trading.bot_engine import engine

async def test():
    engine.start()
    await asyncio.sleep(8)
    print('IS_RUNNING:', engine.is_running)
    for log in engine.logs:
        print(log['level'], log['time'], log['message'])

asyncio.run(test())
