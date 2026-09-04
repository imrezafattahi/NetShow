from app.checks.ping import parse_ping
from app.config import Target, load_settings

LINUX_OK = """PING 1.1.1.1 (1.1.1.1) 56(84) bytes of data.
64 bytes from 1.1.1.1: icmp_seq=1 ttl=57 time=41.2 ms
64 bytes from 1.1.1.1: icmp_seq=2 ttl=57 time=41.5 ms

--- 1.1.1.1 ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 1002ms
rtt min/avg/max/mdev = 41.229/41.482/41.788/0.231 ms
"""

WINDOWS_OK = """Pinging 1.1.1.1 with 32 bytes of data:
Reply from 1.1.1.1: bytes=32 time=42ms TTL=57

Ping statistics for 1.1.1.1:
    Packets: Sent = 2, Received = 2, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 41ms, Maximum = 43ms, Average = 42ms
"""

UNREACHABLE = """PING 10.0.0.99 (10.0.0.99) 56(84) bytes of data.

--- 10.0.0.99 ping statistics ---
3 packets transmitted, 0 received, 100% packet loss, time 3070ms
"""

PARTIAL = """PING 10.0.0.14 (10.0.0.14) 56(84) bytes of data.
64 bytes from 10.0.0.14: icmp_seq=2 ttl=64 time=0.8 ms

--- 10.0.0.14 ping statistics ---
4 packets transmitted, 3 received, 25% packet loss, time 3050ms
rtt min/avg/max/mdev = 0.712/0.804/0.921/0.088 ms
"""


def test_parses_linux_output():
    result = parse_ping(LINUX_OK)
    assert result.up is True
    assert result.latency_ms == 41.482
    assert result.packet_loss == 0.0
    assert result.detail is None


def test_parses_windows_output():
    result = parse_ping(WINDOWS_OK)
    assert result.up is True
    assert result.latency_ms == 42.0
    assert result.packet_loss == 0.0


def test_detects_unreachable_host():
    result = parse_ping(UNREACHABLE)
    assert result.up is False
    assert result.packet_loss == 100.0
    assert result.detail


def test_keeps_partial_loss_visible():
    result = parse_ping(PARTIAL)
    assert result.up is True
    assert result.packet_loss == 25.0


def test_target_hostname_and_port():
    assert Target("api", "http", "https://api.example.com/health").hostname == "api.example.com"
    assert Target("api", "http", "https://api.example.com:8443/").port == 8443
    assert Target("api", "http", "https://api.example.com").port == 443


def test_settings_have_targets():
    settings = load_settings()
    assert settings.interval_seconds >= 10
    assert settings.targets, "config.json should define at least one target"
