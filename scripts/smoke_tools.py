import asyncio
import json

from services.tools import execute_tool


async def main() -> None:
    print(await execute_tool("get_daily_summary", json.dumps({"date": "2026-07-26"})))
    print(await execute_tool("get_current_datetime", "{}"))
    print(await execute_tool("get_company_profile", "{}"))


if __name__ == "__main__":
    asyncio.run(main())
