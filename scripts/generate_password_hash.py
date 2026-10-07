"""
Standalone utility: generate a Werkzeug password hash for a given plaintext
password. Useful if you want to write a manual SQL INSERT for a user instead
of using scripts/seed_admin.py or the Admin -> Add User screen.

Usage:
    python scripts/generate_password_hash.py "MySecretPassword123"

If no argument is given, you'll be prompted interactively (input is hidden).
"""

import sys
import getpass

from werkzeug.security import generate_password_hash


def main():
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = getpass.getpass("Enter password to hash: ")

    if not password:
        print("No password provided. Aborting.")
        sys.exit(1)

    hashed = generate_password_hash(password)
    print("\nGenerated password hash (use this in a manual SQL INSERT):\n")
    print(hashed)
    print(f"\nExample:\n"
          f"INSERT INTO users (username, password_hash, role, full_name, email, is_active)\n"
          f"VALUES ('someuser', '{hashed}', 'receptionist', 'Some User', "
          f"'someuser@example.com', TRUE);")


if __name__ == "__main__":
    main()
