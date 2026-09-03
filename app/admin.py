import argparse
import asyncio
import getpass

from app.database import async_session_factory, engine
from app.repositories import UserRepository
from app.services.users import (
    EmailAlreadyExists,
    LifecycleOperationProhibited,
    UserNotFound,
    UserService,
)


async def create_administrator(email: str, password: str) -> None:
    async with async_session_factory() as session:
        async with session.begin():
            service = UserService(UserRepository(session))
            await service.create_user(email, password, is_admin=True)


async def remove_user(email: str) -> None:
    async with async_session_factory() as session:
        async with session.begin():
            service = UserService(UserRepository(session))
            await service.delete_user_for_operations(email)


def read_password() -> str:
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("Passwords do not match")
    return password


async def run_command(arguments: argparse.Namespace) -> None:
    try:
        if arguments.command == "create-admin":
            await create_administrator(arguments.email, read_password())
            print(f"Created administrator {arguments.email.lower()}")
        else:
            await remove_user(arguments.email)
            print(f"Removed user {arguments.email.lower()}")
    except EmailAlreadyExists:
        raise SystemExit("A user with that email already exists")
    except UserNotFound:
        raise SystemExit("User not found")
    except LifecycleOperationProhibited:
        raise SystemExit("The last active administrator cannot be removed")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage application users")
    commands = parser.add_subparsers(dest="command", required=True)
    create_parser = commands.add_parser("create-admin")
    create_parser.add_argument("email")
    remove_parser = commands.add_parser("remove-user")
    remove_parser.add_argument("email")
    asyncio.run(run_command(parser.parse_args()))


if __name__ == "__main__":
    main()
