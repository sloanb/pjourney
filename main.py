"""Entry point for pjourney TUI application."""

from pjourney.app import PJourneyApp


def main():
    app = PJourneyApp()
    app.run()


if __name__ == "__main__":
    main()
