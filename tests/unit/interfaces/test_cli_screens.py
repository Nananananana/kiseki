"""The screens command exists and takes a limit."""

from kiseki.interfaces.cli import build_parser


class TestScreensParser:
    def test_screens_is_registered(self) -> None:
        args = build_parser().parse_args(["screens", "--limit", "5"])
        assert args.limit == 5
        assert args.run is not None
