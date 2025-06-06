import argparse
import getpass
import sys
import os
import subprocess
from pathlib import Path
import military_crypto_lib
from .container import SecureContainer


def get_password(prompt="Enter decryption key: ") -> str:
    return getpass.getpass(prompt)


def init_container(args):
    container_path = Path(args.container)
    if container_path.exists():
        print(f"Error: Container already exists at {container_path}")
        sys.exit(1)
    
    key = get_password("Enter encryption key for new container: ")
    confirm_key = get_password("Confirm encryption key: ")
    
    if key != confirm_key:
        print("Error: Keys do not match")
        sys.exit(1)
    
    container = SecureContainer(str(container_path))
    try:
        container.create_empty(key)
        print(f"Empty container created: {container_path}")
    except Exception as e:
        print(f"Error creating container: {e}")
        sys.exit(1)


def add_file(args):
    container_path = Path(args.container)
    if not container_path.exists():
        print(f"Error: Container not found at {container_path}")
        sys.exit(1)
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found at {file_path}")
        sys.exit(1)
    
    key = get_password()
    container = SecureContainer(str(container_path))
    
    try:
        container.add_file(str(file_path), key, args.target)
        target_name = args.target if args.target else file_path.name
        print(f"File added to container: {target_name}")
    except Exception as e:
        print(f"Error adding file: {e}")
        print(e)
        sys.exit(1)


def mount_container(args):
    container_path = Path(args.container)
    if not container_path.exists():
        print(f"Error: Container not found at {container_path}")
        sys.exit(1)
    
    key = get_password()
    container = SecureContainer(str(container_path))
    
    try:
        mount_path = container.mount(key)
        print(f"Container mounted at: {mount_path}")
        print("\nFiles in container:")
        files = container.list_files()
        if files:
            for file in files:
                print(f"  {file}")
        else:
            print("  (empty)")
        
        print(f"\nYou can now edit files at: {mount_path}")
        print("Available commands:")
        print("  ls - List files")
        print("  edit <file> - Edit a file")
        print("  save - Save changes and exit")
        print("  exit - Exit without saving")
        
        while True:
            try:
                cmd = input("\n> ").strip().split()
                if not cmd:
                    continue
                
                if cmd[0] == "ls":
                    files = container.list_files()
                    if files:
                        for file in files:
                            print(f"  {file}")
                    else:
                        print("  (empty)")
                
                elif cmd[0] == "edit" and len(cmd) > 1:
                    file_to_edit = mount_path / cmd[1]
                    if file_to_edit.exists():
                        editor = os.environ.get('EDITOR', 'nano')
                        subprocess.call([editor, str(file_to_edit)])
                    else:
                        print(f"File not found: {cmd[1]}")
                
                elif cmd[0] == "save":
                    container.save(key)
                    print("Changes saved to container")
                    break
                
                elif cmd[0] == "exit":
                    print("Exiting without saving changes")
                    break
                
                else:
                    print("Unknown command. Use: ls, edit <file>, save, or exit")
            
            except KeyboardInterrupt:
                print("\nExiting without saving changes")
                break
            except EOFError:
                print("\nExiting without saving changes")
                break
    
    except Exception as e:
        print(f"Error mounting container: {e}")
        sys.exit(1)
    
    finally:
        container.unmount()


def main() -> None:
    parser = argparse.ArgumentParser(description="Zero File Share - Secure container management")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    init_parser = subparsers.add_parser('init', help='Initialize empty container')
    init_parser.add_argument('container', help='Path to container file')
    
    add_parser = subparsers.add_parser('add', help='Add file to container')
    add_parser.add_argument('container', help='Path to container file')
    add_parser.add_argument('file', help='Path to file to add')
    add_parser.add_argument('--target', help='Target path within container')
    
    mount_parser = subparsers.add_parser('mount', help='Mount container for editing')
    mount_parser.add_argument('container', help='Path to container file')
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_container(args)
    elif args.command == 'add':
        add_file(args)
    elif args.command == 'mount':
        mount_container(args)
    else:
        parser.print_help()
        sys.exit(1)
