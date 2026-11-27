"""
Агент: модель NVIDIA (через OpenRouter) + инструменты MCP-сервера server.py.

1. Запускает server.py как MCP-сервер (stdio).
2. Получает список инструментов и передаёт его модели.
3. Выполняет вызовы инструментов, которые запрашивает модель,
   и возвращает ей результаты, пока модель не даст итоговый ответ.

Запуск:
  uv run agent.py "Посчитай подсеть 192.168.1.10/26"
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DEFAULT_MODEL = "nvidia/nemotron-3.5-lightning:free"
MODEL = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
MAX_STEPS = 8

SYSTEM_PROMPT = (
    "Ты сетевой помощник. Для расчётов подсетей, проверки адресов, ping, DNS "
    "и портов обязательно используй доступные инструменты, а не считай в уме. "
    "Отвечай на русском языке, кратко и по делу."
)


def mcp_tool_to_openai(tool) -> dict:
    """Описание инструмента MCP -> формат tools для OpenAI-совместимого API."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema,
        },
    }


def tool_result_text(result) -> str:
    """Текст из результата вызова инструмента MCP."""
    parts = [c.text for c in result.content if getattr(c, "type", "") == "text"]
    return "\n".join(parts) if parts else str(result)


async def run(question: str) -> None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("Не найден OPENROUTER_API_KEY. Скопируйте .env.example в .env и вставьте ключ.")

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(BASE_DIR / "server.py")],
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            print(f"Модель: {MODEL}")
            print(f"Инструменты MCP: {', '.join(t.name for t in tools)}")
            print(f"Вопрос: {question}\n")

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ]
            openai_tools = [mcp_tool_to_openai(t) for t in tools]

            for _ in range(MAX_STEPS):
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=openai_tools,
                )
                message = response.choices[0].message

                if not message.tool_calls:
                    print("Ответ модели:")
                    print(message.content)
                    return

                messages.append(message.model_dump(exclude_none=True))
                for call in message.tool_calls:
                    args = json.loads(call.function.arguments or "{}")
                    print(f"-> вызов {call.function.name}({json.dumps(args, ensure_ascii=False)})")
                    result = await session.call_tool(call.function.name, args)
                    text = tool_result_text(result)
                    print(f"<- {text}\n")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": text,
                    })

            print("Модель не дала итоговый ответ за отведённое число шагов.")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    question = " ".join(sys.argv[1:]) or "Посчитай подсеть 192.168.1.10/26"
    asyncio.run(run(question))


if __name__ == "__main__":
    main()
