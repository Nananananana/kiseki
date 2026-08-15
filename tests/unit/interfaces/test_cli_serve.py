"""The serve command binds to loopback unless told otherwise.

"No account, no upload, no network required" means the network is
opt-in: reaching the server from another device takes an explicit
--host, never a default.
"""

from kiseki.interfaces.cli import build_parser


class TestServeParser:
    def test_serve_defaults_to_loopback(self) -> None:
        args = build_parser().parse_args(["serve"])
        assert args.host == "127.0.0.1"
        assert args.port == 8765
        assert args.run is not None
