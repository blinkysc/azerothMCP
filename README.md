# AzerothCore MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides AI assistants like Claude with read-only access to AzerothCore databases and wiki documentation. This enables AI-powered assistance for understanding creature scripts, SmartAI logic, database schemas, and game mechanics.

## Features

### Database Tools
- **query_database** - Execute read-only SQL queries against world, characters, or auth databases
- **get_table_schema** - Retrieve table structure/column definitions
- **list_tables** - List tables with optional pattern filtering

### Creature/NPC Tools
- **get_creature_template** - Get full creature data by entry ID
- **search_creatures** - Search creatures by name pattern
- **get_creature_with_scripts** - Get creature template with associated SmartAI scripts

### SmartAI Tools
- **get_smart_scripts** - Retrieve SmartAI scripts with auto-generated Keira3-style comments
- **explain_smart_script** - Get documentation for event/action/target types
- **trace_script_chain** - Debug and visualize SmartAI execution flow, following links, timed action lists, and data triggers
- **get_smartai_source** - Get actual C++ implementation from SmartScript.cpp for any event/action/target type
- **generate_sai_comments** - Generate human-readable comments for existing creature/gameobject scripts
- **generate_comment_for_script** - Generate a comment for a single new script row before inserting
- **generate_comments_for_scripts_batch** - Generate comments for multiple script rows at once

### Spell Lookup Tools
- **get_spell_name** - Look up a spell name by ID from Keira3's offline database
- **lookup_spell_names** - Batch lookup multiple spell names at once

### Source Code Tools
- **search_azerothcore_source** - Search AzerothCore source code for patterns
- **read_source_file** - Read specific source files from AzerothCore

### Wiki/Documentation Tools
- **search_wiki** - Search AzerothCore wiki documentation
- **read_wiki_page** - Read specific wiki pages

### Additional Entity Tools
- **get_gameobject_template** / **search_gameobjects** - GameObject lookup
- **search_spells** - Search spell_dbc by name or ID (disabled by default, for custom spells only)
- **get_quest_template** / **search_quests** - Quest lookup
- **diagnose_quest** - Comprehensive quest diagnostics (givers, enders, requirements, chain, conditions, issues)
- **get_item_template** / **search_items** - Item lookup

### SOAP / Worldserver Command Tools
- **soap_execute_command** - Execute any GM command on a running worldserver via SOAP
- **soap_server_info** - Get server uptime, player count, and version info
- **soap_reload_table** - Hot-reload database tables without server restart
- **soap_check_connection** - Test SOAP connectivity and authentication

## Requirements

- Python 3.10+
- MySQL with AzerothCore databases
- (Optional) Local copy of [AzerothCore wiki](https://github.com/azerothcore/wiki)

## Installation

1. Clone the repository (with submodules for Keira3 spell database):
```bash
git clone --recursive https://github.com/yourusername/azerothMCP.git
cd azerothMCP
```

If you already cloned without `--recursive`, initialize submodules:
```bash
git submodule update --init --recursive
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your configuration:
```env
# Database connection
DB_HOST=localhost
DB_PORT=3306
DB_USER=acore
DB_PASSWORD=acore

# Database names
DB_WORLD=acore_world
DB_CHARACTERS=acore_characters
DB_AUTH=acore_auth

# Wiki documentation path (optional)
# Clone https://github.com/azerothcore/wiki to ~/wiki
WIKI_PATH=~/wiki/docs

# AzerothCore source path (for source code tools)
AZEROTHCORE_SRC_PATH=~/azerothcore

# Read-only mode (default: true)
# Set to "false" to allow INSERT, UPDATE, DELETE queries
READ_ONLY=true

# Enable spell_dbc tool (default: false, for custom spells only)
ENABLE_SPELL_DBC=false

# MCP server port
MCP_PORT=8080

# SOAP Configuration (optional - for live server commands)
# Requires SOAP.Enabled = 1 in worldserver.conf
SOAP_ENABLED=false
SOAP_HOST=127.0.0.1
SOAP_PORT=7878
SOAP_USERNAME=your_admin_account
SOAP_PASSWORD=your_account_password
```

## Usage

### Running the Server

Start the MCP server:

```bash
source venv/bin/activate
python server.py
```

The server starts on `http://localhost:8080/sse` using Server-Sent Events (SSE) transport.

### Connecting with Claude Desktop

Add to your Claude Desktop MCP configuration:

**Linux:** `~/.config/Claude/claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "azerothcore": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

Then restart Claude Desktop. The AzerothCore tools will be available in your conversations.

### Connecting with Claude Code

Add to your Claude Code MCP settings (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "azerothcore": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

### Example Prompts

Once connected, you can ask things like:

- "What scripts does Hogger (entry 448) have?"
- "Show me the creature_template schema"
- "Search for creatures named 'Defias'"
- "Explain SmartAI event type 4"
- "Trace the script chain for creature 1234"
- "Find quests related to Westfall"
- "Generate comments for this SmartAI script"
- "What spell is ID 17364?"

## Wiki Setup (Optional)

To enable wiki search functionality, clone the AzerothCore wiki:

```bash
cd ~
git clone https://github.com/azerothcore/wiki.git
```

The server will search markdown files in `~/wiki/docs` by default. Update `WIKI_PATH` in your `.env` if your wiki is in a different location.

## SOAP Setup (Optional)

SOAP allows executing GM commands on a running worldserver. This enables live server management like reloading tables after database changes, checking server status, or managing accounts.

### 1. Enable SOAP in worldserver.conf

```conf
SOAP.Enabled = 1
SOAP.IP = "127.0.0.1"
SOAP.Port = 7878
```

### 2. Configure Environment Variables

The account must have administrator privileges (SEC_ADMINISTRATOR, gmlevel 3+):

```env
SOAP_ENABLED=true
SOAP_HOST=127.0.0.1
SOAP_PORT=7878
SOAP_USERNAME=your_admin_account
SOAP_PASSWORD=your_account_password
```

### Example SOAP Commands

Once configured, you can use prompts like:

- "Check if the worldserver is running"
- "Reload the creature_template table"
- "Get server info"
- "Execute command: lookup creature hogger"

## Security

By default, the server operates in **read-only mode**. Only `SELECT`, `SHOW`, and `DESCRIBE` queries are permitted.

To enable write operations (INSERT, UPDATE, DELETE) for full automation:

```env
READ_ONLY=false
```

**Warning:** Enabling write mode allows the AI to modify your database. Use with caution and ensure you have backups.

## License

GNU GPL v2 - See [LICENSE](LICENSE)

## Related Projects

- [AzerothCore](https://github.com/azerothcore/azerothcore-wotlk) - Open source WoW emulator
- [Keira3](https://github.com/azerothcore/Keira3) - Database editor for AzerothCore (spell database used for comment generation)
- [Model Context Protocol](https://modelcontextprotocol.io/) - Open protocol for AI context sharing
