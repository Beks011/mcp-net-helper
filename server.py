"""
MCP-сервер с сетевыми инструментами.

Инструменты:
  subnet_info  - параметры подсети (адрес сети, маска, broadcast, диапазон хостов)
  same_subnet  - находятся ли два адреса в одной подсети
  ping         - проверка доступности хоста
  dns_lookup   - IP-адреса доменного имени
  port_check   - открыт ли TCP-порт на хосте

Запуск (stdio): uv run server.py
"""
import ipaddress
import platform
import socket
import subprocess

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("net-helper", log_level="WARNING")


def _network(address: str, mask: str | None = None) -> ipaddress.IPv4Network:
    """Собрать сеть из '192.168.1.10/24' или из адреса и маски."""
    text = f"{address}/{mask}" if mask else address
    return ipaddress.IPv4Network(text, strict=False)


@mcp.tool()
def subnet_info(address: str, mask: str | None = None) -> dict:
    """Параметры подсети.

    address: IP-адрес с префиксом (например 192.168.1.10/26) или без него.
    mask: маска (255.255.255.192) или длина префикса (26), если её нет в address.
    """
    net = _network(address, mask)
    hosts = net.num_addresses - 2 if net.prefixlen < 31 else net.num_addresses
    first = net.network_address + 1 if net.prefixlen < 31 else net.network_address
    last = net.broadcast_address - 1 if net.prefixlen < 31 else net.broadcast_address
    return {
        "network": str(net.network_address),
        "prefix": f"/{net.prefixlen}",
        "mask": str(net.netmask),
        "wildcard": str(net.hostmask),
        "broadcast": str(net.broadcast_address),
        "first_host": str(first),
        "last_host": str(last),
        "usable_hosts": hosts,
        "private": net.is_private,
    }


@mcp.tool()
def same_subnet(ip1: str, ip2: str, mask: str) -> dict:
    """Проверить, находятся ли два IPv4-адреса в одной подсети при заданной маске.

    mask: маска (255.255.254.0) или длина префикса (23).
    """
    net1 = _network(ip1, mask)
    net2 = _network(ip2, mask)
    return {
        "same_subnet": net1 == net2,
        "network_ip1": str(net1),
        "network_ip2": str(net2),
    }


@mcp.tool()
def ping(host: str, count: int = 4) -> str:
    """Отправить ICMP-запросы (ping) на хост и вернуть вывод команды."""
    count = max(1, min(count, 10))
    flag = "-n" if platform.system() == "Windows" else "-c"
    try:
        result = subprocess.run(
            ["ping", flag, str(count), host],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return "Команда ping не найдена в системе."
    except subprocess.TimeoutExpired:
        return f"Хост {host} не ответил за 30 секунд."
    return (result.stdout or result.stderr).strip()


@mcp.tool()
def dns_lookup(domain: str) -> dict:
    """Получить IP-адреса доменного имени."""
    try:
        infos = socket.getaddrinfo(domain, None)
    except socket.gaierror as e:
        return {"domain": domain, "error": str(e)}
    addresses = sorted({info[4][0] for info in infos})
    return {"domain": domain, "addresses": addresses}


@mcp.tool()
def port_check(host: str, port: int, timeout: float = 3.0) -> dict:
    """Проверить, открыт ли TCP-порт на хосте (например 80, 443, 22)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"host": host, "port": port, "open": True}
    except OSError as e:
        return {"host": host, "port": port, "open": False, "reason": str(e)}


if __name__ == "__main__":
    mcp.run()
