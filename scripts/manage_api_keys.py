#!/usr/bin/env python3
"""
Simple CLI script to manage API keys for the FBI Bot API.

This script allows you to:
- Create new API keys for friends
- List existing API keys
- Revoke API keys
- View usage statistics

Usage:
    python scripts/manage_api_keys.py create "John's Key" read "192.168.1.100,john.example.com"
    python scripts/manage_api_keys.py list
    python scripts/manage_api_keys.py revoke 1
    python scripts/manage_api_keys.py stats 1
"""

import asyncio
import sys
import json
from pathlib import Path

# Add the project root to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# These imports need to be after the path modification
try:
    from sqlmodel import select
    from app.auth.database import AuthSessionLocal
    from app.auth.models import ApiKey
    from app.auth.services import AuthService
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)


class ApiKeyManager:
    """Simple API key management CLI."""

    def __init__(self):
        self.db = AuthSessionLocal()

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    async def create_key(self, name: str, role: str, allowed_ips_str: str):
        """Create a new API key."""
        # Parse allowed IPs
        allowed_ips = [ip.strip() for ip in allowed_ips_str.split(',') if ip.strip()]

        if not allowed_ips:
            print("❌ Error: You must provide at least one allowed IP address")
            return

        if role not in ['admin', 'read']:
            print("❌ Error: Role must be 'admin' or 'read'")
            return

        try:
            # Create the API key
            api_key, plain_key = await AuthService.create_api_key(
                name=name,
                role=role,
                allowed_ips=allowed_ips,
                db=self.db
            )

            print("✅ API Key Created Successfully!")
            print(f"📝 Name: {name}")
            print(f"🔑 Role: {role}")
            print(f"🌐 Allowed IPs: {', '.join(allowed_ips)}")
            print(f"🔒 Key ID: {api_key.id}")
            print(f"📅 Created: {api_key.created_at}")
            print()
            print("🚨 IMPORTANT: Save this API key - it won't be shown again!")
            print("=" * 60)
            print(f"API Key: {plain_key}")
            print("=" * 60)

        except Exception as e:
            print(f"❌ Error creating API key: {str(e)}")

    def list_keys(self):
        """List all API keys."""
        try:
            keys = self.db.exec(
                select(ApiKey).order_by(ApiKey.created_at.desc())
            ).all()

            if not keys:
                print("📝 No API keys found.")
                return

            print("📋 API Keys:")
            print("-" * 80)
            print(f"{'ID':<4} {'Name':<20} {'Role':<6} {'Created':<20} {'Last Used':<20}")
            print("-" * 80)

            for key in keys:
                last_used = key.last_used_at.strftime("%Y-%m-%d %H:%M") if key.last_used_at else "Never"
                created = key.created_at.strftime("%Y-%m-%d %H:%M")

                print(f"{key.id:<4} {key.name[:19]:<20} {key.role:<6} {created:<20} {last_used:<20}")

            print("-" * 80)
            print(f"Total: {len(keys)} keys")

        except Exception as e:
            print(f"❌ Error listing API keys: {str(e)}")

    async def revoke_key(self, key_id: int):
        """Revoke (delete) an API key."""
        try:
            # First, show info about the key
            key = self.db.exec(select(ApiKey).where(ApiKey.id == key_id)).first()
            if not key:
                print(f"❌ API key with ID {key_id} not found.")
                return

            print("🗑️  About to revoke API key:")
            print(f"   ID: {key.id}")
            print(f"   Name: {key.name}")
            print(f"   Role: {key.role}")
            print(f"   Created: {key.created_at}")

            # Confirm deletion
            response = input("Are you sure you want to revoke this key? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("❌ Revocation cancelled.")
                return

            # Revoke the key
            success = await AuthService.revoke_api_key(key_id, self.db)

            if success:
                print("✅ API key revoked successfully!")
            else:
                print("❌ Failed to revoke API key.")

        except Exception as e:
            print(f"❌ Error revoking API key: {str(e)}")

    async def show_stats(self, key_id: int):
        """Show usage statistics for an API key."""
        try:
            key = self.db.exec(select(ApiKey).where(ApiKey.id == key_id)).first()
            if not key:
                print(f"❌ API key with ID {key_id} not found.")
                return

            print(f"📊 Usage Statistics for: {key.name}")
            print("-" * 50)

            # Get usage stats
            stats = await AuthService.get_usage_stats(key, self.db, days=30)

            print(f"📈 Total Requests (30 days): {stats['total_requests']}")
            print(f"📅 Requests Today: {stats['requests_today']}")
            print(f"❌ Error Requests: {stats['error_requests']}")
            print(f"✅ Success Rate: {stats['success_rate']:.1f}%")
            print("📝 Key Info:")
            print(f"   Role: {key.role}")
            print(f"   Created: {key.created_at}")
            print(f"   Last Used: {key.last_used_at or 'Never'}")

            # Show allowed IPs
            allowed_ips = json.loads(key.allowed_ips)
            print(f"   Allowed IPs: {', '.join(allowed_ips)}")

        except Exception as e:
            print(f"❌ Error getting stats: {str(e)}")

    def show_help(self):
        """Show help message."""
        print("🔑 FBI Bot API Key Manager")
        print("=" * 40)
        print()
        print("Commands:")
        print("  create <name> <role> <allowed_ips>  Create a new API key")
        print("  list                                List all API keys")
        print("  revoke <key_id>                     Revoke an API key")
        print("  stats <key_id>                      Show usage statistics")
        print("  help                                Show this help")
        print()
        print("Examples:")
        print('  python scripts/manage_api_keys.py create "John\'s Key" read "192.168.1.100,john.example.com"')
        print("  python scripts/manage_api_keys.py list")
        print("  python scripts/manage_api_keys.py revoke 1")
        print("  python scripts/manage_api_keys.py stats 1")
        print()
        print("Roles:")
        print("  admin  - Full access (you)")
        print("  read   - Read-only access (friends)")


async def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        ApiKeyManager().show_help()
        return

    command = sys.argv[1].lower()
    manager = ApiKeyManager()

    try:
        if command == "create":
            if len(sys.argv) != 5:
                print("❌ Usage: create <name> <role> <allowed_ips>")
                print('   Example: create "John\'s Key" read "192.168.1.100,john.example.com"')
                return

            name, role, allowed_ips = sys.argv[2], sys.argv[3], sys.argv[4]
            await manager.create_key(name, role, allowed_ips)

        elif command == "list":
            manager.list_keys()

        elif command == "revoke":
            if len(sys.argv) != 3:
                print("❌ Usage: revoke <key_id>")
                return

            try:
                key_id = int(sys.argv[2])
                await manager.revoke_key(key_id)
            except ValueError:
                print("❌ Key ID must be a number")

        elif command == "stats":
            if len(sys.argv) != 3:
                print("❌ Usage: stats <key_id>")
                return

            try:
                key_id = int(sys.argv[2])
                await manager.show_stats(key_id)
            except ValueError:
                print("❌ Key ID must be a number")

        elif command == "help":
            manager.show_help()

        else:
            print(f"❌ Unknown command: {command}")
            manager.show_help()

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
