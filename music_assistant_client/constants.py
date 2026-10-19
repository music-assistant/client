"""Constants for the Music Assistant client."""

from typing import Final

# Minimum server schema for the scalar provider filter on artist tracks and albums.
ARTIST_PROVIDER_FILTER_SCHEMA_VERSION: Final[int] = 31

# Minimum server schema for requesting library listings on behalf of a user.
LIBRARY_USER_SCHEMA_VERSION: Final[int] = 35

# Minimum server schema for library sorting and sort discovery.
TYPED_LISTING_SCHEMA_VERSION: Final[int] = 86

# Minimum server schema for album-track sorting, search, paging and nonlibrary sort discovery.
ALBUM_TRACKS_LISTING_SCHEMA_VERSION: Final[int] = 89

# Minimum server schema for artist listings, track albums and similar tracks.
ARTIST_LISTING_SCHEMA_VERSION: Final[int] = 92

# Minimum server schema for playlist-track and podcast-episode sorting, search and paging.
PLAYLIST_PODCAST_LISTING_SCHEMA_VERSION: Final[int] = 93

# Minimum server schema for version and browse listings, and genre-track/album search.
VERSIONS_BROWSE_LISTING_SCHEMA_VERSION: Final[int] = 94

# Minimum server schema for typed playback sorting.
PLAY_MEDIA_SORT_SCHEMA_VERSION: Final[int] = 95

# Minimum server schema for favorite/album-type and episode-exclusion filters,
# not basic sorting or paging.
LISTING_FILTER_SCHEMA_VERSION: Final[int] = 96

# Minimum server schema for stable seeded random ordering across pages.
RANDOM_SEED_SCHEMA_VERSION: Final[int] = 98

# Client contract checked against the server's min_supported_schema_version at connect time,
# not a feature gate.
API_SCHEMA_VERSION: Final[int] = 46
