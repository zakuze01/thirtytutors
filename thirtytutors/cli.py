"""Lite launcher: no package installation, asset fetching, or updater."""

import argparse


def main():
    from . import desktop

    parser = argparse.ArgumentParser(description="Companion Lite")
    parser.add_argument("--host", default="127.0.0.1", choices=["127.0.0.1"])
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    desktop.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
