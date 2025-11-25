#!/bin/bash
# Sync Music Assistant Python client from server API using Claude Code
# This script launches Claude Code with instructions to sync the client library methods
# from the server's API documentation.

# Default server URL
SERVER_URL="${1:-http://localhost:8095}"

echo "=== Music Assistant Client Sync (Claude Code) ==="
echo "Server: $SERVER_URL"
echo ""

# Check if server is reachable
if ! curl -sf "$SERVER_URL/info" > /dev/null 2>&1; then
    echo "Error: Cannot reach server at $SERVER_URL"
    echo "Please ensure the Music Assistant server is running."
    exit 1
fi

echo "Server is reachable. Launching Claude Code..."
echo ""

# Launch Claude Code with the sync instructions
claude --add-dir "../core" --add-dir "/tmp" --permission-mode bypassPermissions "Please sync the Music Assistant Python client library from the server API documentation.

## Context

The Music Assistant server exposes its API at runtime with structured API documentation.
The Python client library needs to stay in sync with these API commands.

**Important Resources:**
- Server repository: https://github.com/music-assistant/server
- The server repository is most likely also available locally (check \`../core\` and \`../server\`).
- Client repository: Current working directory
- Server API docs endpoint: SERVER_URL/api-docs
- Server info endpoint: SERVER_URL/info (contains schema_version)
- The music_assistant_models package contains all model definitions used in the API (which are shared between server and client).

## Task Overview

Update the Python client controller files to match the current server API:
1. Add new API methods that don't exist in the client
2. Update existing methods if their signatures or docstrings have changed
3. Remove obsolete methods that no longer exist in the API
4. Ensure all type imports from \`music_assistant_models\` are correct

## Step-by-Step Instructions

### Step 1: Fetch API Data

1. Fetch the server info to get the current schema version:
   SERVER_URL/info
   Extract the \`schema_version\` field - this will be used for all new/updated methods.

2. Fetch the API commands and schemas:
   SERVER_URL/api-docs/commands
   SERVER_URL/api-docs/schemas
   Parse the commands and schemas pages to get a list of API commands, their parameters, return types, and descriptions.

### Step 2: Process Each Controller

Process these controller files in the client:
- \`music_assistant_client/auth.py\` - handles \"Auth\" category
- \`music_assistant_client/config.py\` - handles \"Config\" category
- \`music_assistant_client/metadata.py\` - handles \"Metadata\" category
- \`music_assistant_client/music.py\` - handles \"Music\" category
- \`music_assistant_client/player_queues.py\` - handles \"Player Queues\" category
- \`music_assistant_client/players.py\` - handles \"Players\" category

**Skip these API categories entirely:**
- Logging
- Builtin Player
- General (already handled in main client logic)
- Providers (already handled in main client logic)

### Step 3: For Each Controller, Process Commands

For each API command in the controller's category:

#### A. Determine if Command Should Be Skipped

Skip these specific commands (they use cached data or are already handled):
- \`players/all\` - players are cached locally
- \`players/get*\` - player retrieval uses cache
- \`player_queues/all\` - player queues are cached locally
- \`player_queues/get\` - already handled in code with special logic
- Any command in ignored categories

#### B. Generate Method Name from Command Path

Use these naming conventions:

**Music category** (command: \`music/MEDIA_TYPE/ACTION\`):
- \`music/artists/get\` → \`get_artist\` (get_singular)
- \`music/tracks/library_items\` → \`get_library_tracks\` (get_library_plural)
- \`music/albums/count\` → \`album_count\` (singular_count, not count_albums)
- \`music/albums/remove\` → \`remove_album\` (action_singular)
- \`music/tracks/update\` → \`update_track\` (action_singular)
- \`music/tracks/preview\` → \`track_preview\` (singular_preview)
- \`music/albums/album_versions\` → \`album_versions\` (singular_versions)
- \`music/tracks/similar_tracks\` → \`similar_tracks\` (no prefix)
- \`music/podcasts/podcast_episode\` → \`podcast_episode\` (singular)

**Config category** (command: \`config/TYPE/ACTION\`):
- \`config/core/get\` → \`get_core_config\`
- \`config/players/save\` → \`save_player_config\`
- \`config/providers/get_value\` → \`get_provider_config_value\`
- \`config/players/get_entries\` → \`get_player_config_entries\` (NOT get_entries_player_config)

**Players category**:
- \`players/cmd/volume_set\` → \`volume_set\`
- \`players/create_group\` → \`create_group\`
- etc.
- No need to prefix with \"players_\" - just use the action name

**Player Queues category**:
- No need to prefix with \"player_queues_\" - just use the action name

#### C. Generate Method Code

Each method should follow this structure:

\`\`\`python
# For methods that return a value:
async def method_name(self, param1: Type1, param2: Type2 | None = None) -> ReturnType:
    \"\"\"Method description from API docs (single line preferred).\"\"\"
    return await self.client.send_command(
        \"command/path\",
        param1=param1,
        param2=param2,
        require_schema=28,  # Use current schema version from server
    )

# For methods that return None:
async def method_name(self, param1: Type1) -> None:
    \"\"\"Method description from API docs (single line preferred).\"\"\"
    await self.client.send_command(
        \"command/path\",
        param1=param1,
        require_schema=28,
    )
    # NOTE: No 'return' statement for None return type!

# For methods that return simple types (int, str, bool, etc.):
async def count_method(self) -> int:
    \"\"\"Return the count.\"\"\"
    return await self.client.send_command(
        \"command/path\",
        require_schema=28,
    )
    # NOTE: 'return' statement IS needed for non-None return types!
\`\`\`

**Docstring Guidelines:**
- Prefer single-line docstrings: \`\"\"\"Description.\"\"\"\`
- Keep descriptions concise (one sentence when possible)
- Multi-line docstrings should only be used when absolutely necessary
- This ensures pre-commit checks pass

**Important Type Handling:**

1. **Parameter Types** - Map API types to Python types:
   - \`string\` → \`str\`
   - \`boolean\` → \`bool\`
   - \`integer\` → \`int\`
   - \`number\` → \`float\`
   - \`Array of X\` → \`list[X]\`
   - \`X | Y | Z\` → \`X | Y | Z\` (preserve unions)
   - type Aliases (e.g., \`MediaItemType\`, \`ConfigValueType\`) → use the alias name
   - Use \`| None = None\` for optional parameters

2. **Return Type Handling:**
   - Simple types (\`str\`, \`bool\`, \`int\`, \`float\`, \`dict\`) → return as-is
   - Model types (\`Artist\`, \`Album\`, etc.) → deserialize with \`.from_dict()\`
   - List of models → list comprehension with \`.from_dict()\`
   - **MediaItemType Union type** (e.g., \`Artist | Album | Track\`) → use media_from_dict helper.
   - Be aware of type Aliases such as MediaItemType and ConfigValueType and try to use them for the type annotations on the method definitions to match the server.
   - Anything else: try to infer from context or check server code (or ask).

   Examples:
   \`\`\`python
   # Simple return
   return await self.client.send_command(...)

   # Single model return
   return Artist.from_dict(await self.client.send_command(...))

   # List of models
   return [Artist.from_dict(obj) for obj in await self.client.send_command(...)]

   # MediaItemType Union type handling
   return await media_from_dict(self.client.send_command(...))
   \`\`\`

3. **Long Signatures** - Break lines if signature > 100 characters:
   \`\`\`python
   async def method_name(self,
       param1: VeryLongType,
       param2: AnotherLongType | None = None,
   ) -> ReturnType:
   \`\`\`

4. **Docstrings** - Preserve API description formatting:
   - Single line: \`\"\"\"Description.\"\"\"\`
   - Multi-line:
     \`\`\`python
     \"\"\"
     First line.

     Additional paragraphs separated by blank lines.

     More details here.
     \"\"\"
     \`\`\`

#### D. Compare with Existing Method

For each command:
1. Check if a method already exists for this command path
2. If it exists:
   - Compare the generated signature/docstring with existing
   - If different, remove old method and add updated version
   - Print: \`↻ Updated: method_name\`
3. If it doesn't exist:
   - Add the new method
   - Print: \`+ Added: method_name\`
   - Add \"required_schema\" parameter with current schema version

#### E. Check for Obsolete Methods

After processing all API commands for a controller:
1. Find methods in the file that have \`send_command()\` calls
2. Extract their command paths
3. If a command path doesn't exist in the current API (and isn't in the skip list), remove the method
4. Print: \`✓ Removed: method_name (was: command/path)\`

### Step 4: Import Management

After updating methods in each controller file:

1. **Scan all method signatures** in the file to identify required types
2. **Determine import modules** for each type:

   **Media Items** (from \`music_assistant_models.media_items\`):
   - Artist, Album, Track, Radio, Playlist, Audiobook, Podcast, PodcastEpisode
   - ItemMapping, PagedItems, SearchResults, BrowseFolder

   **Players** (various modules):
   - Player → \`music_assistant_models.player\`
   - PlayerMedia → \`music_assistant_models.player\`
   - PlayerControl → \`music_assistant_models.player_control\`
   - PlayerQueue → \`music_assistant_models.player_queue\`
   - QueueItem → \`music_assistant_models.player_queue\`

   **Config** (various modules):
   - CoreConfig, ProviderConfig, PlayerConfig → \`music_assistant_models.config\`
   - ConfigEntry, ConfigEntryValue → \`music_assistant_models.config_entries\`
   - DSPConfig, DSPConfigPreset → \`music_assistant_models.dsp\`

   **Enums** (from \`music_assistant_models.enums\`):
   - MediaType, MediaItemType, RepeatMode, ConfigValueType, ProviderType, AlbumType

   **Other**:
   - ProviderManifest → \`music_assistant_models.provider\`
   - PluginSource → \`music_assistant_models.plugin_source\`
   - QueueOption → \`music_assistant_models.player_queue\`
   - SyncTask → (check server for correct import)
   - RecommendationFolder → (check server for correct import)

3. **Update imports intelligently**:
   - Parse existing imports in the file
   - Add missing imports
   - Merge with existing imports from the same module
   - Format imports:
     - Single line if ≤ 3 items and ≤ 60 chars: \`from module import A, B, C\`
     - Multi-line otherwise:
       \`\`\`python
       from module import (
           A,
           B,
           C,
           D,
       )
       \`\`\`
   - Place imports before \`if TYPE_CHECKING:\` block
   - Remove duplicate imports

4. **Special Cases**:
   - If unsure about a type's module, search the server repository for the type definition
   - Some types may be type aliases - check the server code
   - \`AsyncGenerator\` needs: \`from typing import AsyncGenerator\`
   - \`Sequence\` needs: \`from collections.abc import Sequence\`

### Step 5: Validation

After updating all files:
1. Run syntax check: \`python -m py_compile <file>\`
2. Check for common issues:
   - Missing imports
   - Duplicate imports
   - Methods with incorrect indentation
   - Methods inserted in wrong location (should be before private methods starting with \`_\`)

### Step 6: Summary Report

Print a summary for each controller:
\`\`\`
Config (music_assistant_client/config.py):
  ↻ Updated: 5 methods
  + Added: 2 methods
  ✓ Removed: 1 method
  📦 Updated imports: Added DSPConfig, DSPConfigPreset
  ✓ Syntax check passed
\`\`\`

## Special Notes

1. Look carefully at the existing methods how they handle the command sending and responses, for example the Models need to be handled with the "from-dict" approach.

2. **Method Placement**: Always insert new methods BEFORE any private methods (those starting with \`_\`). Look for the first method starting with \`async def _\` and insert before it.

3. **Docstring Formatting**: The API docs may have weird formatting. Clean it up but preserve the semantic meaning and line breaks that indicate paragraph boundaries.

4. **Schema Version**: Use the actual schema version from the server's \`/info\` endpoint, not a hardcoded value.

5. **Type Inference**: If a type is not in the standard mappings, look at the server repository to understand what module it comes from. The server code is the source of truth.

6. **Git Changes**: Do not create a git commit. Just update the files.

7. **No Confirmation**: This is an automated task. Do not ask for confirmation before making changes.

8. **Testing**: After making changes, ensure the client library still passes basic syntax checks.

9. **Logging**: Print clear messages about what changes were made for traceability.

10. **Linting**: Ensure the updated code still passes the pre-commit checks.

11. Once done making the adjustments to the code, make sure that you also bump the schema version in the constants (API_SCHEMA_VERSION) in the client code to match the server schema version.


## Error Handling

If you encounter issues:
- **Unknown type**: Search the server repository for the type definition
- **Conflicting imports**: Check which module actually exports the type
- **Method name collision**: Check if there's a sync variant of the method (like \`get()\` and async \`get()\`)
- **Parsing errors**: Look at similar existing methods in the file for patterns
- **Return type is Any**: If the API docs show \"Any\" as return type, check the server implementation to determine the actual return type. This usually means the server-side method is missing a return type annotation. Common cases:
  - Methods returning lists of items (like similar_tracks) → \`list[Track]\`
  - Methods returning single items → check the specific model type
  - Verify by checking how the result is used in the server code

## Additional Context

The server generates API documentation automatically from Python function signatures and docstrings using the \`@api_command\` decorator. When in doubt about parameter types or return types, you can look at the actual server implementation in the repository.

If you really have questions about the task because something is unclear, ask for clarification before proceeding.
Then also adjust the instructions in this file accordingly for future runs.
Otherwise, try to ask for clarification only if there's genuine ambiguity in how to implement something and keep questions to a bare minimum.

Do not add the "require_schema" to existing methods, you only need to do that for NEW methods.

**IMPORTANT**: This is an automated sync task. Try to NOT ask for confirmation before reading or editing files.
Proceed directly with all file operations (Read, Edit, Write, Bash commands) without requesting permission (if possible).
Only ask questions if there's genuine ambiguity in how to implement something.

If you need to download any files or create temporary scripts, do so without asking for permission and create them in some temp folder and clean them up afterwards.

Begin the sync process now. Be thorough and careful with type handling.
Please respond with a confirmation that you have read this prompts and you are starting the sync.
Also provide a brief summary of your planned approach before proceeding."

echo ""
echo "=== Claude Code session ended ==="
