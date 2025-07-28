# Scripts Directory

This directory contains utility scripts for LUCA development and maintenance.

## Database Cleanup Script

### Overview

`cleanup_database.py` - Comprehensive database cleanup utility that removes all conversation data, checkpoints, and agent memory from Neo4j.

**⚠️ WARNING**: This script permanently deletes ALL user conversation data. Use only for development/testing.

### What Gets Deleted

- **Conversations** (`Conversacion` nodes) - All user conversations
- **Messages** (`Mensaje` nodes) - All conversation messages  
- **Checkpoints** (`Checkpoint` nodes) - All LangGraph workflow checkpoints
- **Agent Memory** (`AgentMemory` nodes) - All agent memory stores
- **Temporary Data** - Orphaned relationships and session data

### What Stays Intact

- **Users** (`Usuario` nodes) - User accounts remain unchanged
- **Knowledge Graph** - Course data (subjects, practices, exercises) remains intact
- **System Configuration** - Database constraints and indexes remain

### Usage

#### Command Line

```bash
# Interactive cleanup with confirmation prompt
python scripts/cleanup_database.py

# Auto-confirm cleanup (skip prompt)
python scripts/cleanup_database.py --confirm

# Show database summary without cleanup
python scripts/cleanup_database.py --summary-only

# Verbose logging
python scripts/cleanup_database.py --verbose
```

#### VSCode Debugger

Three launcher configurations are available in VSCode:

1. **Database Cleanup - Interactive** - Interactive mode with confirmation
2. **Database Cleanup - Auto Confirm** - Skip confirmation prompt  
3. **Database Summary Only** - Show summary without cleanup

Access via: `Run and Debug (Ctrl+Shift+D)` → Select configuration → `F5`

### Features

- **Safety Checks** - Shows summary before deletion
- **Confirmation Prompt** - Requires typing 'YES' to proceed
- **Comprehensive Logging** - Detailed progress and error reporting
- **Verification** - Confirms cleanup completion
- **Error Handling** - Graceful handling of connection issues

### Example Output

```
============================================================
LUCA DATABASE CLEANUP UTILITY
============================================================
📊 Current database content:
   • conversations: 25
   • messages: 150
   • checkpoints: 45
   • agent_memories: 12
   • users: 3

⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ 
WARNING: This will permanently delete ALL conversation data!
⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ 

Are you sure you want to continue? (type 'YES' to confirm): YES

🚀 Starting database cleanup...
🗑️  Deleting all conversations and messages...
   ✅ All messages deleted
   ✅ All conversations deleted
🗑️  Deleting all LangGraph checkpoints...
   ✅ All checkpoints deleted
🗑️  Deleting all agent memory stores...
   ✅ All agent memories deleted
🗑️  Cleaning up temporary session data...
   ✅ Temporary session data cleaned
🔍 Verifying cleanup completion...
   ✅ Cleanup verification PASSED - all data removed

============================================================
✅ DATABASE CLEANUP COMPLETED SUCCESSFULLY!
============================================================
```

### When to Use

- **Development Testing** - Clean state for testing conversation flows
- **Schema Migration** - Remove old data after schema changes (like the evaluation intent removal)
- **Performance Issues** - Clear accumulated test data
- **Fresh Start** - Reset environment for new development cycles
- **Demo Preparation** - Clean state for demonstrations

### Recovery

After cleanup, the system will automatically recreate necessary schema when users log in and start new conversations. All Knowledge Graph data (courses, practices, exercises) remains intact.

### Dependencies

- Neo4j connection (configured via environment variables)
- `kg.connection.KGConnection` module
- Standard Python logging and argparse

### Error Handling

The script includes comprehensive error handling for:
- Neo4j connection failures
- Query execution errors  
- Partial cleanup scenarios
- User interruption (Ctrl+C)

### Security Note

This script requires database write permissions. Ensure proper environment configuration and use only in development/testing environments.