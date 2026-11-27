# mcp-net-helper

MCP-сервер с сетевыми инструментами и агент, который подключает к ним модель **NVIDIA Nemotron** через **OpenRouter**.

## Инструменты сервера

| Инструмент | Что делает |
|------------|------------|
| `subnet_info` | Параметры подсети: адрес сети, маска, wildcard, broadcast, диапазон хостов |
| `same_subnet` | Проверяет, находятся ли два адреса в одной подсети |
| `ping` | Проверяет доступность хоста |
| `dns_lookup` | Возвращает IP-адреса доменного имени |
| `port_check` | Проверяет, открыт ли TCP-порт на хосте |

## Файлы

- `server.py`: MCP-сервер (FastMCP, транспорт stdio)
- `agent.py`: агент. Запускает сервер, передаёт модели список инструментов и выполняет её вызовы
- `pyproject.toml`: зависимости проекта
- `.env.example`: шаблон для ключа OpenRouter

## Установка

Нужен [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Beks011/mcp-net-helper.git
cd mcp-net-helper
uv sync
```

## 1. Запуск через терминал

Проверка самого MCP-сервера в MCP Inspector:

```bash
uv run mcp dev server.py
```

## 2. Подключение к платформе (Claude Code / Claude Desktop)

Claude Code:

```bash
claude mcp add net-helper -- uv run --directory /полный/путь/к/mcp-net-helper server.py
```

Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "net-helper": {
      "command": "uv",
      "args": ["run", "--directory", "C:\\полный\\путь\\к\\mcp-net-helper", "server.py"]
    }
  }
}
```

После подключения инструменты доступны в чате, например: «посчитай подсеть 192.168.1.10/26».

## 3. Модель NVIDIA через ключ OpenRouter

1. Создайте ключ на https://openrouter.ai/keys
2. Скопируйте шаблон и вставьте ключ в `OPENROUTER_API_KEY`:

```bash
cp .env.example .env
```

3. Запустите агента:

```bash
uv run agent.py "В одной ли сети 10.0.0.5 и 10.0.1.7 при маске 255.255.254.0?"
```

По умолчанию используется бесплатная модель `nvidia/nemotron-3.5-lightning:free`. Другую модель можно задать переменной `OPENROUTER_MODEL` в `.env`.

Пример вывода:

```
Модель: nvidia/nemotron-3.5-lightning:free
Инструменты MCP: subnet_info, same_subnet, ping, dns_lookup, port_check
Вопрос: Посчитай подсеть 192.168.1.10/26

-> вызов subnet_info({"address": "192.168.1.10/26"})
<- {"network": "192.168.1.0", "mask": "255.255.255.192", "broadcast": "192.168.1.63", ...}

Ответ модели:
...
```

Файл `.env` с ключом добавлен в `.gitignore` и в репозиторий не попадает.
