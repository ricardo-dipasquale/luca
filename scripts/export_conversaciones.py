#!/usr/bin/env python3
"""
Conversation Export Script for LUCA

This script exports all conversations and messages for each user from Neo4j to Excel format.
It extracts data from Usuario, Conversacion, and Mensaje nodes with their relationships.

The script:
- Exports all users and their conversations
- Includes all messages in chronological order (by mensaje_orden)
- Creates an Excel file with user conversation data
- Supports filtering by specific users
- Includes comprehensive conversation metadata

Output Excel structure:
- usuario_nombre: User's display name
- usuario_email: User's email address
- conversacion_id: Unique conversation identifier
- conversacion_titulo: Conversation title
- conversacion_materia: Educational subject
- conversacion_fecha: Conversation creation date
- mensaje_id: Unique message identifier
- mensaje_role: Message role (user/assistant)
- mensaje_contenido: Message content
- mensaje_fecha: Message timestamp
- mensaje_orden: Message order in conversation

Usage:
    python scripts/export_conversaciones.py [--output PATH] [--user EMAIL] [--verbose]
"""

import sys
import os
import logging
import argparse
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kg.connection import KGConnection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConversationExporter:
    """
    Conversation export utility for LUCA from Neo4j to Excel.
    """

    def __init__(self, output_file: str = "conversaciones_luca.xlsx"):
        """
        Initialize with output file path and Neo4j connection.

        Args:
            output_file: Path to the output Excel file
        """
        self.output_file = output_file

        try:
            self.kg = KGConnection()
            logger.info("Connected to Neo4j database successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Get all users from Neo4j database.

        Returns:
            List of user dictionaries with email and nombre
        """
        try:
            query = "MATCH (u:Usuario) RETURN u.email as email, u.nombre as nombre ORDER BY u.email"
            results = self.kg.execute_query(query)

            logger.info(f"Found {len(results)} users in database")
            return results

        except Exception as e:
            logger.error(f"Error getting users: {e}")
            raise

    def get_user_conversations_and_messages(self, user_email: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all conversations and messages for users.

        Args:
            user_email: Optional specific user email to filter by

        Returns:
            List of conversation and message data
        """
        try:
            # Build query with optional user filter
            if user_email:
                where_clause = "WHERE u.email = $user_email"
                params = {"user_email": user_email}
            else:
                where_clause = ""
                params = {}

            query = f"""
            MATCH (u:Usuario)-[:OWNS]->(c:Conversacion)-[:CONTAINS]->(m:Mensaje)
            {where_clause}
            RETURN
                u.nombre as usuario_nombre,
                u.email as usuario_email,
                c.id as conversacion_id,
                c.title as conversacion_titulo,
                c.subject as conversacion_materia,
                c.created_at as conversacion_fecha,
                c.updated_at as conversacion_actualizada,
                c.message_count as conversacion_num_mensajes,
                m.id as mensaje_id,
                m.role as mensaje_role,
                m.content as mensaje_contenido,
                m.created_at as mensaje_fecha,
                m.order as mensaje_orden
            ORDER BY u.email, c.created_at, m.order
            """

            results = self.kg.execute_query(query, params)

            if user_email:
                logger.info(f"Found {len(results)} messages for user {user_email}")
            else:
                logger.info(f"Found {len(results)} total messages across all users")

            return results

        except Exception as e:
            logger.error(f"Error getting conversations and messages: {e}")
            raise

    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics about conversations and messages.

        Returns:
            Dictionary with summary statistics
        """
        try:
            # Get user count
            user_query = "MATCH (u:Usuario) RETURN count(u) as total_users"
            user_result = self.kg.execute_query(user_query)
            total_users = user_result[0]["total_users"]

            # Get conversation count
            conv_query = "MATCH (c:Conversacion) RETURN count(c) as total_conversations"
            conv_result = self.kg.execute_query(conv_query)
            total_conversations = conv_result[0]["total_conversations"]

            # Get message count
            msg_query = "MATCH (m:Mensaje) RETURN count(m) as total_messages"
            msg_result = self.kg.execute_query(msg_query)
            total_messages = msg_result[0]["total_messages"]

            # Get conversations per user
            conv_per_user_query = """
            MATCH (u:Usuario)-[:OWNS]->(c:Conversacion)
            RETURN u.email as user_email, count(c) as conversation_count
            ORDER BY conversation_count DESC
            """
            conv_per_user_result = self.kg.execute_query(conv_per_user_query)

            # Get messages per user
            msg_per_user_query = """
            MATCH (u:Usuario)-[:OWNS]->(c:Conversacion)-[:CONTAINS]->(m:Mensaje)
            RETURN u.email as user_email, count(m) as message_count
            ORDER BY message_count DESC
            """
            msg_per_user_result = self.kg.execute_query(msg_per_user_query)

            # Get subject distribution
            subject_query = """
            MATCH (c:Conversacion)
            RETURN c.subject as subject, count(c) as conversation_count
            ORDER BY conversation_count DESC
            """
            subject_result = self.kg.execute_query(subject_query)

            return {
                "total_users": total_users,
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "conversations_per_user": conv_per_user_result,
                "messages_per_user": msg_per_user_result,
                "subjects": subject_result
            }

        except Exception as e:
            logger.error(f"Error getting conversation summary: {e}")
            return {"error": str(e)}

    def format_timestamp(self, timestamp_obj) -> str:
        """
        Format Neo4j timestamp to readable format, handling timezone issues.

        Args:
            timestamp_obj: Neo4j timestamp object or string

        Returns:
            Formatted timestamp string without timezone
        """
        try:
            if timestamp_obj is None:
                return None

            # Handle different timestamp formats from Neo4j
            if hasattr(timestamp_obj, 'strftime'):
                # It's already a datetime object, remove timezone info
                if hasattr(timestamp_obj, 'replace'):
                    # Remove timezone to make it Excel-compatible
                    dt_naive = timestamp_obj.replace(tzinfo=None)
                    return dt_naive.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    return timestamp_obj.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(timestamp_obj, str):
                # Parse Neo4j datetime format and convert to readable format
                dt = datetime.fromisoformat(timestamp_obj.replace('Z', '+00:00'))
                # Remove timezone to make it Excel-compatible
                dt_naive = dt.replace(tzinfo=None)
                return dt_naive.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return str(timestamp_obj)
        except Exception as e:
            logger.debug(f"Error formatting timestamp {timestamp_obj}: {e}")
            return str(timestamp_obj) if timestamp_obj else None

    def export_conversations_to_excel(self, user_email: Optional[str] = None) -> Dict[str, Any]:
        """
        Export conversations and messages to Excel file.

        Args:
            user_email: Optional specific user email to filter by

        Returns:
            Dictionary with export statistics
        """
        try:
            # Get conversation and message data
            data = self.get_user_conversations_and_messages(user_email)

            if not data:
                logger.warning("No conversation data found")
                return {"exported_records": 0, "error": "No data to export"}

            # Convert to DataFrame
            df = pd.DataFrame(data)

            # Format timestamps
            timestamp_columns = ['conversacion_fecha', 'conversacion_actualizada', 'mensaje_fecha']
            for col in timestamp_columns:
                if col in df.columns:
                    df[col] = df[col].apply(self.format_timestamp)

            # Sort by user, conversation date, and message order
            df = df.sort_values(['usuario_email', 'conversacion_fecha', 'mensaje_orden'])

            # Write to Excel with multiple sheets
            with pd.ExcelWriter(self.output_file, engine='openpyxl') as writer:
                # Main data sheet
                df.to_excel(writer, sheet_name='Conversaciones_Mensajes', index=False)

                # Summary sheet
                summary = self.get_conversation_summary()
                if "error" not in summary:
                    # Users summary
                    if summary.get('conversations_per_user'):
                        conv_per_user_df = pd.DataFrame(summary['conversations_per_user'])
                        conv_per_user_df.to_excel(writer, sheet_name='Conversaciones_Por_Usuario', index=False)

                    # Messages summary
                    if summary.get('messages_per_user'):
                        msg_per_user_df = pd.DataFrame(summary['messages_per_user'])
                        msg_per_user_df.to_excel(writer, sheet_name='Mensajes_Por_Usuario', index=False)

                    # Subjects summary
                    if summary.get('subjects'):
                        subjects_df = pd.DataFrame(summary['subjects'])
                        subjects_df.to_excel(writer, sheet_name='Materias', index=False)

                    # Overall statistics
                    stats_data = [
                        ['Total Usuarios', summary['total_users']],
                        ['Total Conversaciones', summary['total_conversations']],
                        ['Total Mensajes', summary['total_messages']],
                        ['Fecha Exportación', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                    ]
                    stats_df = pd.DataFrame(stats_data, columns=['Métrica', 'Valor'])
                    stats_df.to_excel(writer, sheet_name='Estadísticas', index=False)

            # Get unique users and conversations count
            unique_users = df['usuario_email'].nunique()
            unique_conversations = df['conversacion_id'].nunique()
            total_messages = len(df)

            logger.info(f"Excel export completed successfully")
            logger.info(f"  File: {self.output_file}")
            logger.info(f"  Users: {unique_users}")
            logger.info(f"  Conversations: {unique_conversations}")
            logger.info(f"  Messages: {total_messages}")

            return {
                "exported_records": total_messages,
                "unique_users": unique_users,
                "unique_conversations": unique_conversations,
                "output_file": self.output_file
            }

        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            raise

    def verify_export(self) -> Dict[str, Any]:
        """
        Verify the exported Excel file by reading it back.

        Returns:
            Dictionary with verification results
        """
        try:
            if not os.path.exists(self.output_file):
                return {"error": f"Export file not found: {self.output_file}"}

            # Read the main sheet
            df = pd.read_excel(self.output_file, sheet_name='Conversaciones_Mensajes')

            # Get basic statistics
            unique_users = df['usuario_email'].nunique()
            unique_conversations = df['conversacion_id'].nunique()
            total_messages = len(df)

            # Get sample data
            sample_data = df.head(3).to_dict('records')

            return {
                "file_exists": True,
                "total_records": total_messages,
                "unique_users": unique_users,
                "unique_conversations": unique_conversations,
                "columns": list(df.columns),
                "sample_data": sample_data
            }

        except Exception as e:
            logger.error(f"Error verifying export: {e}")
            return {"error": str(e)}

    def close(self):
        """Close the Neo4j connection."""
        self.kg.close()


def main():
    """Main function to run the conversation export script."""
    parser = argparse.ArgumentParser(description="Export conversations from Neo4j to Excel")
    parser.add_argument("--output", type=str, default="conversaciones_luca.xlsx",
                       help="Output Excel file path (default: conversaciones_luca.xlsx)")
    parser.add_argument("--user", type=str,
                       help="Export conversations for specific user email only")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--summary-only", action="store_true",
                       help="Show summary statistics without exporting")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check if output path is relative to project root
    output_file = args.output
    if not os.path.isabs(output_file):
        # Assume relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_file = os.path.join(project_root, output_file)

    logger.info(f"Starting conversation export to {output_file}")

    try:
        # Initialize exporter
        exporter = ConversationExporter(output_file)

        if args.summary_only:
            # Show summary only
            summary = exporter.get_conversation_summary()
            if "error" not in summary:
                logger.info("Database Summary:")
                logger.info(f"  Total Users: {summary['total_users']}")
                logger.info(f"  Total Conversations: {summary['total_conversations']}")
                logger.info(f"  Total Messages: {summary['total_messages']}")

                if summary.get('conversations_per_user'):
                    logger.info("  Top Users by Conversations:")
                    for user_data in summary['conversations_per_user'][:5]:
                        logger.info(f"    {user_data['user_email']}: {user_data['conversation_count']} conversations")

                if summary.get('subjects'):
                    logger.info("  Subjects:")
                    for subject_data in summary['subjects']:
                        logger.info(f"    {subject_data['subject']}: {subject_data['conversation_count']} conversations")

            exporter.close()
            return 0

        # Export conversations
        result = exporter.export_conversations_to_excel(args.user)

        # Print summary
        if "error" not in result:
            logger.info("Export Summary:")
            logger.info(f"  Exported: {result['exported_records']} messages")
            logger.info(f"  Users: {result['unique_users']}")
            logger.info(f"  Conversations: {result['unique_conversations']}")
            logger.info(f"  Output file: {result['output_file']}")

            # Verify export
            verification = exporter.verify_export()
            if "error" not in verification:
                logger.info("Export verification successful")
                logger.info(f"  File size: {len(verification['columns'])} columns")
                if verification['sample_data']:
                    logger.info("  Sample conversation:")
                    sample = verification['sample_data'][0]
                    logger.info(f"    User: {sample.get('usuario_nombre')} ({sample.get('usuario_email')})")
                    logger.info(f"    Conversation: {sample.get('conversacion_titulo')}")
        else:
            logger.error(f"Export failed: {result['error']}")

        exporter.close()
        logger.info("Conversation export completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Conversation export failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())