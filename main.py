"""Entry point for the FertiCalc UI prototype."""

from ferticalc import FerticalcApp


def main() -> None:
    app = FerticalcApp()
    app.run()


if __name__ == "__main__":
    main()
