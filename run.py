#!/usr/bin/env python3
"""Start J.A.R.V.I.S."""

from jarvis import create_app
from jarvis.config import Config

config = Config.from_env()
app = create_app(config)

if __name__ == "__main__":
    print(f"\n  {config.assistant_name} online at http://{config.host}:{config.port}\n")
    app.run(host=config.host, port=config.port, debug=config.debug)
