#!/usr/bin/env python3
"""
User Import Script for LUCA

This script imports users from usuarios-luca.xlsx and creates/updates Usuario nodes in Neo4j.
It uses the first column as name (nombre), third column as email, and fourth column as password.

The script:
- Reads from usuarios-luca.xlsx in the project root
- Creates or updates Usuario nodes (no duplicates)
- Uses MERGE to avoid duplicating existing users
- Validates email format (must end with @uca.edu.ar)
- Adds created_at timestamp for new users
- Updates existing users if data has changed

Usage:
    python scripts/import_usuarios.py [--dry-run] [--verbose] [--file PATH]
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


class UserImporter:
    """
    User import utility for LUCA from Excel spreadsheet.
    """

    def __init__(self, excel_file: str = "usuarios-luca.xlsx"):
        """
        Initialize with Excel file path and Neo4j connection.

        Args:
            excel_file: Path to the Excel file containing user data
        """
        self.excel_file = excel_file

        try:
            self.kg = KGConnection()
            logger.info("Connected to Neo4j database successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def validate_excel_file(self) -> bool:
        """
        Validate that the Excel file exists and has the expected structure.

        Returns:
            bool: True if file is valid, False otherwise
        """
        if not os.path.exists(self.excel_file):
            logger.error(f"Excel file not found: {self.excel_file}")
            return False

        try:
            df = pd.read_excel(self.excel_file)

            if df.shape[1] < 4:
                logger.error(f"Excel file must have at least 4 columns, found {df.shape[1]}")
                return False

            logger.info(f"Excel file validated: {df.shape[0]} rows, {df.shape[1]} columns")
            return True

        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            return False

    def load_users_from_excel(self) -> List[Dict[str, str]]:
        """
        Load user data from Excel file.

        Returns:
            List of user dictionaries with nombre, email, password
        """
        try:
            df = pd.read_excel(self.excel_file)

            # Get column names (first row becomes headers)
            columns = df.columns.tolist()

            users = []
            for _, row in df.iterrows():
                # Use first column as nombre, third as email, fourth as password
                nombre = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
                email = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
                password = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""

                # Skip rows with missing essential data
                if not all([nombre, email, password]):
                    logger.warning(f"Skipping row with missing data: {row.iloc[0]}, {row.iloc[2]}")
                    continue

                # Validate email format
                if not email.endswith("@uca.edu.ar"):
                    logger.warning(f"Skipping user {nombre} - email must end with @uca.edu.ar: {email}")
                    continue

                users.append({
                    "nombre": nombre,
                    "email": email,
                    "password": password
                })

            logger.info(f"Loaded {len(users)} valid users from Excel file")
            return users

        except Exception as e:
            logger.error(f"Error loading users from Excel: {e}")
            raise

    def get_existing_users(self) -> Dict[str, Dict[str, Any]]:
        """
        Get existing users from Neo4j database.

        Returns:
            Dictionary mapping email to user properties
        """
        try:
            query = "MATCH (u:Usuario) RETURN u.email as email, u.nombre as nombre, u.password as password, u.created_at as created_at"
            results = self.kg.execute_query(query)

            existing_users = {}
            for record in results:
                existing_users[record["email"]] = {
                    "nombre": record["nombre"],
                    "password": record["password"],
                    "created_at": record["created_at"]
                }

            logger.info(f"Found {len(existing_users)} existing users in database")
            return existing_users

        except Exception as e:
            logger.error(f"Error getting existing users: {e}")
            raise

    def import_users(self, users: List[Dict[str, str]], dry_run: bool = False) -> Dict[str, int]:
        """
        Import users into Neo4j database.

        Args:
            users: List of user dictionaries
            dry_run: If True, only show what would be imported without making changes

        Returns:
            Dictionary with counts of created, updated, and skipped users
        """
        stats = {"created": 0, "updated": 0, "skipped": 0}

        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made to database")

        existing_users = self.get_existing_users()

        for user in users:
            email = user["email"]
            nombre = user["nombre"]
            password = user["password"]

            try:
                if email in existing_users:
                    # Check if user data has changed
                    existing = existing_users[email]
                    if existing["nombre"] == nombre and existing["password"] == password:
                        logger.debug(f"User {email} unchanged, skipping")
                        stats["skipped"] += 1
                        continue

                    # Update existing user
                    if not dry_run:
                        update_query = """
                        MATCH (u:Usuario {email: $email})
                        SET u.nombre = $nombre, u.password = $password
                        RETURN u
                        """
                        self.kg.execute_write_query(update_query, {
                            "email": email,
                            "nombre": nombre,
                            "password": password
                        })

                    logger.info(f"{'Would update' if dry_run else 'Updated'} user: {nombre} ({email})")
                    stats["updated"] += 1

                else:
                    # Create new user
                    if not dry_run:
                        create_query = """
                        CREATE (u:Usuario {
                            email: $email,
                            nombre: $nombre,
                            password: $password,
                            created_at: datetime()
                        })
                        RETURN u
                        """
                        self.kg.execute_write_query(create_query, {
                            "email": email,
                            "nombre": nombre,
                            "password": password
                        })

                    logger.info(f"{'Would create' if dry_run else 'Created'} new user: {nombre} ({email})")
                    stats["created"] += 1

            except Exception as e:
                logger.error(f"Error processing user {nombre} ({email}): {e}")
                stats["skipped"] += 1
                continue

        return stats

    def verify_import(self) -> Dict[str, Any]:
        """
        Verify the import by getting current user count and sample data.

        Returns:
            Dictionary with verification results
        """
        try:
            # Get total user count
            count_query = "MATCH (u:Usuario) RETURN count(u) as total_users"
            count_result = self.kg.execute_query(count_query)
            total_users = count_result[0]["total_users"]

            # Get sample users
            sample_query = "MATCH (u:Usuario) RETURN u.nombre as nombre, u.email as email, u.created_at as created_at ORDER BY u.created_at DESC LIMIT 5"
            sample_results = self.kg.execute_query(sample_query)

            return {
                "total_users": total_users,
                "sample_users": sample_results
            }

        except Exception as e:
            logger.error(f"Error verifying import: {e}")
            return {"error": str(e)}

    def close(self):
        """Close the Neo4j connection."""
        self.kg.close()


def main():
    """Main function to run the user import script."""
    parser = argparse.ArgumentParser(description="Import users from Excel to Neo4j")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be imported without making changes")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--file", type=str, default="usuarios-luca.xlsx",
                       help="Path to Excel file (default: usuarios-luca.xlsx)")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check if file path is relative to project root
    excel_file = args.file
    if not os.path.isabs(excel_file):
        # Assume relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        excel_file = os.path.join(project_root, excel_file)

    logger.info(f"Starting user import from {excel_file}")

    try:
        # Initialize importer
        importer = UserImporter(excel_file)

        # Validate Excel file
        if not importer.validate_excel_file():
            logger.error("Excel file validation failed")
            return 1

        # Load users from Excel
        users = importer.load_users_from_excel()
        if not users:
            logger.warning("No valid users found in Excel file")
            return 0

        # Import users
        stats = importer.import_users(users, dry_run=args.dry_run)

        # Print summary
        logger.info("Import Summary:")
        logger.info(f"  Created: {stats['created']} users")
        logger.info(f"  Updated: {stats['updated']} users")
        logger.info(f"  Skipped: {stats['skipped']} users")
        logger.info(f"  Total processed: {sum(stats.values())} users")

        # Verify import (only if not dry run)
        if not args.dry_run:
            verification = importer.verify_import()
            if "error" not in verification:
                logger.info(f"Verification: {verification['total_users']} total users in database")
                if verification['sample_users']:
                    logger.info("Recent users:")
                    for user in verification['sample_users']:
                        logger.info(f"  - {user['nombre']} ({user['email']})")

        importer.close()
        logger.info("User import completed successfully")
        return 0

    except Exception as e:
        logger.error(f"User import failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())