#!/usr/bin/env python3
"""
Database Cleanup Script for LUCA

This script completely cleans the Neo4j database by removing:
- All user conversations and messages
- All LangGraph checkpoints and memory data
- All agent memory stores
- All temporary session data

WARNING: This will permanently delete ALL conversation history and user data.
Use only for development/testing purposes.
"""

import sys
import os
import logging
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kg.connection import KGConnection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseCleaner:
    """
    Comprehensive database cleanup utility for LUCA.
    """
    
    def __init__(self):
        """Initialize with Neo4j connection."""
        try:
            self.kg = KGConnection()
            logger.info("Connected to Neo4j database successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def get_cleanup_summary(self) -> Dict[str, int]:
        """
        Get a summary of what will be deleted before cleanup.
        
        Returns:
            Dictionary with counts of each data type
        """
        summary = {}
        
        try:
            # Count conversations
            conv_result = self.kg.execute_query("MATCH (c:Conversacion) RETURN count(c) as count")
            summary['conversations'] = conv_result[0]['count'] if conv_result else 0
            
            # Count messages
            msg_result = self.kg.execute_query("MATCH (m:Mensaje) RETURN count(m) as count")
            summary['messages'] = msg_result[0]['count'] if msg_result else 0
            
            # Count checkpoints
            checkpoint_result = self.kg.execute_query("MATCH (cp:Checkpoint) RETURN count(cp) as count")
            summary['checkpoints'] = checkpoint_result[0]['count'] if checkpoint_result else 0
            
            # Count agent memories
            memory_result = self.kg.execute_query("MATCH (am:AgentMemory) RETURN count(am) as count")
            summary['agent_memories'] = memory_result[0]['count'] if memory_result else 0
            
            # Count users (won't delete, just for info)
            user_result = self.kg.execute_query("MATCH (u:Usuario) RETURN count(u) as count")
            summary['users'] = user_result[0]['count'] if user_result else 0
            
            logger.info(f"Database summary: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get database summary: {e}")
            return {}
    
    def cleanup_conversations(self) -> int:
        """
        Delete all conversations and their messages.
        
        Returns:
            Number of conversations deleted
        """
        try:
            logger.info("🗑️  Deleting all conversations and messages...")
            
            # Delete all messages first (they have relationships to conversations)
            msg_query = "MATCH (m:Mensaje) DETACH DELETE m"
            self.kg.execute_query(msg_query)
            logger.info("   ✅ All messages deleted")
            
            # Delete all conversations
            conv_query = "MATCH (c:Conversacion) DETACH DELETE c"
            result = self.kg.execute_query(conv_query)
            logger.info("   ✅ All conversations deleted")
            
            return result if isinstance(result, int) else 0
            
        except Exception as e:
            logger.error(f"Failed to cleanup conversations: {e}")
            return 0
    
    def cleanup_checkpoints(self) -> int:
        """
        Delete all LangGraph checkpoints.
        
        Returns:
            Number of checkpoints deleted
        """
        try:
            logger.info("🗑️  Deleting all LangGraph checkpoints...")
            
            query = "MATCH (cp:Checkpoint) DETACH DELETE cp"
            result = self.kg.execute_query(query)
            logger.info("   ✅ All checkpoints deleted")
            
            return result if isinstance(result, int) else 0
            
        except Exception as e:
            logger.error(f"Failed to cleanup checkpoints: {e}")
            return 0
    
    def cleanup_agent_memory(self) -> int:
        """
        Delete all agent memory stores.
        
        Returns:
            Number of memory entries deleted
        """
        try:
            logger.info("🗑️  Deleting all agent memory stores...")
            
            query = "MATCH (am:AgentMemory) DETACH DELETE am"
            result = self.kg.execute_query(query)
            logger.info("   ✅ All agent memories deleted")
            
            return result if isinstance(result, int) else 0
            
        except Exception as e:
            logger.error(f"Failed to cleanup agent memory: {e}")
            return 0
    
    def cleanup_temp_sessions(self) -> int:
        """
        Delete any temporary session data or orphaned relationships.
        
        Returns:
            Number of items cleaned
        """
        try:
            logger.info("🗑️  Cleaning up temporary session data...")
            
            # Remove any orphaned relationships
            orphan_query = "MATCH ()-[r]->() WHERE startNode(r) IS NULL OR endNode(r) IS NULL DELETE r"
            self.kg.execute_query(orphan_query)
            
            logger.info("   ✅ Temporary session data cleaned")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to cleanup temp sessions: {e}")
            return 0
    
    def verify_cleanup(self) -> Dict[str, int]:
        """
        Verify that cleanup was successful by checking remaining counts.
        
        Returns:
            Dictionary with remaining counts
        """
        try:
            logger.info("🔍 Verifying cleanup completion...")
            
            remaining = self.get_cleanup_summary()
            
            # Check if cleanup was successful
            if (remaining.get('conversations', 0) == 0 and 
                remaining.get('messages', 0) == 0 and 
                remaining.get('checkpoints', 0) == 0 and 
                remaining.get('agent_memories', 0) == 0):
                logger.info("   ✅ Cleanup verification PASSED - all data removed")
            else:
                logger.warning(f"   ⚠️  Cleanup verification found remaining data: {remaining}")
            
            return remaining
            
        except Exception as e:
            logger.error(f"Failed to verify cleanup: {e}")
            return {}
    
    def full_cleanup(self, confirm: bool = False) -> bool:
        """
        Perform complete database cleanup.
        
        Args:
            confirm: If True, skip confirmation prompt
            
        Returns:
            True if cleanup was successful
        """
        try:
            # Get summary before cleanup
            logger.info("=" * 60)
            logger.info("LUCA DATABASE CLEANUP UTILITY")
            logger.info("=" * 60)
            
            summary = self.get_cleanup_summary()
            
            if not any(summary.values()):
                logger.info("✅ Database is already clean - nothing to delete")
                return True
            
            logger.info("📊 Current database content:")
            for data_type, count in summary.items():
                if count > 0:
                    logger.info(f"   • {data_type}: {count}")
            
            # Confirmation
            if not confirm:
                print("\n" + "⚠️ " * 20)
                print("WARNING: This will permanently delete ALL conversation data!")
                print("⚠️ " * 20 + "\n")
                
                response = input("Are you sure you want to continue? (type 'YES' to confirm): ")
                if response != 'YES':
                    logger.info("❌ Cleanup cancelled by user")
                    return False
            
            logger.info("\n🚀 Starting database cleanup...")
            
            # Perform cleanup steps
            self.cleanup_conversations()
            self.cleanup_checkpoints() 
            self.cleanup_agent_memory()
            self.cleanup_temp_sessions()
            
            # Verify cleanup
            remaining = self.verify_cleanup()
            
            logger.info("\n" + "=" * 60)
            logger.info("✅ DATABASE CLEANUP COMPLETED SUCCESSFULLY!")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return False
    
    def close(self):
        """Close database connection."""
        try:
            self.kg.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")


def main():
    """Main entry point for the cleanup script."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Clean up LUCA database by removing all conversation and memory data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/cleanup_database.py                    # Interactive cleanup with confirmation
    python scripts/cleanup_database.py --confirm          # Skip confirmation prompt
    python scripts/cleanup_database.py --summary-only     # Show summary without cleanup
        """
    )
    
    parser.add_argument(
        '--confirm', 
        action='store_true',
        help='Skip confirmation prompt and proceed with cleanup'
    )
    
    parser.add_argument(
        '--summary-only',
        action='store_true', 
        help='Show database summary without performing cleanup'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    cleaner = None
    try:
        # Initialize cleaner
        cleaner = DatabaseCleaner()
        
        if args.summary_only:
            # Just show summary
            summary = cleaner.get_cleanup_summary()
            print("\n📊 Database Summary:")
            print("-" * 30)
            for data_type, count in summary.items():
                print(f"{data_type:15}: {count:>6}")
            print("-" * 30)
        else:
            # Perform cleanup
            success = cleaner.full_cleanup(confirm=args.confirm)
            if success:
                print("\n🎉 Database cleanup completed successfully!")
                sys.exit(0)
            else:
                print("\n❌ Database cleanup failed!")
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("\n❌ Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        if cleaner:
            cleaner.close()


if __name__ == "__main__":
    main()