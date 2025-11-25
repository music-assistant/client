# Music Assistant Client

Python client to interact with the [Music Assistant Server](https://github.com/music-assistant/server) API

---

[![A project from the Open Home Foundation](https://www.openhomefoundation.org/badges/ohf-project.png)](https://www.openhomefoundation.org/)

## Installation

```bash
pip install music-assistant-client
```

## Authentication

Starting with Music Assistant Server schema version 28, authentication is required to connect to the server. The client supports multiple authentication methods:

### 1. Using a Long-Lived Token (Recommended)

The recommended approach is to use a long-lived token.
You can create Long Lived tokens in the Music Assistant web interface in your profile settings.
You can also obtain one using the `login_with_token()` helper:

```python
from music_assistant_client import login_with_token, MusicAssistantClient

# Login and get a long-lived token
user, token = await login_with_token(
    "http://your-server:8095",
    "your_username",
    "your_password",
    token_name="My Application"
)

# Save the token securely for future use
print(f"Your token: {token}")

# Use the token to connect
async with MusicAssistantClient("http://your-server:8095", None, token=token) as client:
    await client.start_listening()
```

### 2. Manual Token Management

You can also manually manage the authentication process:

```python
from music_assistant_client import login, MusicAssistantClient

# Step 1: Login to get an access token
user, access_token = await login(
    "http://your-server:8095",
    "your_username",
    "your_password"
)

# Step 2: Connect with the access token and create a long-lived token
async with MusicAssistantClient("http://your-server:8095", None, token=access_token) as client:
    long_lived_token = await client.auth.create_token(name="My Application")

# Step 3: Use the long-lived token for future connections
async with MusicAssistantClient("http://your-server:8095", None, token=long_lived_token) as client:
    await client.start_listening()
```

### 3. Using Username and Password Directly

For simple scripts or testing, you can use the `login_with_token()` helper which handles everything:

```python
from music_assistant_client import login_with_token, MusicAssistantClient

user, token = await login_with_token(
    "http://your-server:8095",
    "username",
    "password"
)

async with MusicAssistantClient("http://your-server:8095", None, token=token) as client:
    await client.start_listening()
```

## Backward Compatibility

The client automatically detects the server schema version and only requires authentication for schema version 28 and above.
Connections to older servers (schema < 28) will continue to work without authentication.

## SSL/TLS Support

The client supports HTTPS connections. For servers with valid certificates, simply use an `https://` URL:

```python
async with MusicAssistantClient("https://music.example.com", None, token=token) as client:
    await client.start_listening()
```

For self-signed certificates or custom CAs, provide an SSL context:

```python
import ssl

ssl_context = ssl.create_default_context(cafile="/path/to/ca-bundle.pem")
async with MusicAssistantClient("https://music.local", None, token=token, ssl_context=ssl_context) as client:
    await client.start_listening()
```

All authentication helper functions also accept an optional `ssl_context` parameter.
You can also simply pass in a aiohttp Client with the ssl context already set.

## API Reference

### Client Class

**`MusicAssistantClient(server_url, aiohttp_session=None, token=None, ssl_context=None)`**

- `server_url`: The URL of the Music Assistant server (e.g., `http://mass.local:8095` or `https://music.example.com`)
- `aiohttp_session`: Optional aiohttp ClientSession to use
- `token`: Optional authentication token (required for schema >= 28)
- `ssl_context`: Optional SSL context for HTTPS connections (for custom CAs or self-signed certificates)

**Controllers:**

The client provides several controllers for interacting with different aspects of the server:

- **`client.auth`** - Authentication and user management
- **`client.music`** - Music library operations (browse, search, get tracks/albums/artists/playlists, etc.)
- **`client.players`** - Player control and information
- **`client.player_queues`** - Queue management for players
- **`client.config`** - Server configuration management

## Example Usage

```python
import asyncio
from music_assistant_client import MusicAssistantClient, login_with_token

async def main():
    # Get a token (do this once and save it)
    user, token = await login_with_token(
        "http://localhost:8095",
        "admin",
        "password"
    )

    # Connect to the server
    async with MusicAssistantClient("http://localhost:8095", None, token=token) as client:
        # Subscribe to events
        def on_event(event):
            print(f"Received event: {event}")

        client.subscribe(on_event)

        # Start listening for events
        await client.start_listening()

asyncio.run(main())
```

## Error Handling

The client raises specific exceptions for authentication errors:

- `AuthenticationRequired`: Raised when connecting to schema >= 28 without a token
- `AuthenticationFailed`: Raised when the token is invalid or expired
- `LoginFailed`: Raised when username/password authentication fails

```python
from music_assistant_models.errors import AuthenticationRequired, AuthenticationFailed, LoginFailed

try:
    async with MusicAssistantClient(server_url, None, token=token) as client:
        await client.start_listening()
except AuthenticationRequired:
    print("Please provide an authentication token")
except AuthenticationFailed:
    print("Invalid or expired token")
except LoginFailed:
    print("Invalid username or password")
```
