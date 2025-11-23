"""Example script to test the MusicAssistant client."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os

from music_assistant_client import MusicAssistantClient, login_with_token

# Get parsed passed in arguments.
parser = argparse.ArgumentParser(description="MusicAssistant Client Example.")
parser.add_argument(
    "url",
    type=str,
    help="URL of MASS server, e.g. http://localhost:8095",
)
parser.add_argument(
    "--token",
    type=str,
    help="Authentication token (can also be set via MASS_TOKEN env var)",
)
parser.add_argument(
    "--username",
    type=str,
    help="Username for authentication (will create a token)",
)
parser.add_argument(
    "--password",
    type=str,
    help="Password for authentication (will create a token)",
)
parser.add_argument(
    "--log-level",
    type=str,
    default="info",
    help="Provide logging level. Example --log-level debug, default=info, "
    "possible=(critical, error, warning, info, debug)",
)

args = parser.parse_args()


if __name__ == "__main__":
    # configure logging
    logging.basicConfig(level=args.log_level.upper())

    async def run_mass() -> None:
        """Run the MusicAssistant client."""
        # Determine token to use
        token = args.token or os.getenv("MASS_TOKEN")

        # If username and password provided, login and get token
        if args.username and args.password:
            print(f"Logging in as {args.username}...")  # noqa: T201
            user, token = await login_with_token(
                args.url, args.username, args.password, "Example Script"
            )
            print(f"Successfully logged in as {user.username}")  # noqa: T201
            print(f"Token: {token}")  # noqa: T201
            print("Save this token for future use!")  # noqa: T201

        # Connect to the server
        async with MusicAssistantClient(args.url, None, token=token) as client:
            print(f"Connected to Music Assistant Server {client.server_info.server_id}")  # noqa: T201
            print(f"Server Version: {client.server_info.server_version}")  # noqa: T201
            print(f"Schema Version: {client.server_info.schema_version}")  # noqa: T201

            # start listening
            await client.start_listening()

    # run the client
    asyncio.run(run_mass())
