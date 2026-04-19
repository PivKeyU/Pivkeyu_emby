import asyncio
import glob
import os
from datetime import datetime
from pathlib import Path

from bot import LOGGER


class BackupDBUtils:
    @staticmethod
    def _ensure_backup_dir(backup_dir: str) -> None:
        Path(backup_dir).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _rotate_backups(backup_dir: str, database_name: str, suffix: str, max_backup_count: int) -> None:
        all_backups = sorted(glob.glob(os.path.join(backup_dir, f"{database_name}-*.{suffix}")))
        while len(all_backups) > max_backup_count:
            os.remove(all_backups[0])
            all_backups.pop(0)

    @staticmethod
    async def _run_subprocess_shell(command: str) -> int:
        process = await asyncio.create_subprocess_shell(command)
        await process.communicate()
        return int(process.returncode or 0)

    @staticmethod
    async def _run_subprocess_exec(*args, env=None) -> int:
        process = await asyncio.create_subprocess_exec(*args, env=env)
        await process.communicate()
        return int(process.returncode or 0)

    @staticmethod
    async def backup_mysql_db(host, port, user, password, database_name, backup_dir, max_backup_count):
        BackupDBUtils._ensure_backup_dir(backup_dir)
        backup_file = os.path.join(backup_dir, f"{database_name}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.sql")
        command = f"mysqldump -h{host} --no-tablespaces -P{port} -u{user} -p'{password}' {database_name} > {backup_file}"
        skip_ssl_command = f"mysqldump -h{host} --skip-ssl --no-tablespaces -P{port} -u{user} -p'{password}' {database_name} > {backup_file}"
        try:
            return_code = await BackupDBUtils._run_subprocess_shell(command)
            if return_code != 0:
                LOGGER.warning("BOT数据库备份失败，使用 skip-ssl 方式尝试备份")
                return_code = await BackupDBUtils._run_subprocess_shell(skip_ssl_command)
            if return_code != 0:
                LOGGER.error(f"BOT数据库备份失败, error code: {return_code}")
                return None
            LOGGER.info(f"BOT数据库备份成功,文件保存为 {backup_file}")
            BackupDBUtils._rotate_backups(backup_dir, database_name, "sql", max_backup_count)
            return backup_file
        except Exception as e:
            LOGGER.error(f"BOT数据库备份失败, error: {str(e)}")
            return None

    @staticmethod
    async def backup_mysql_db_docker(container_name, user, password, database_name, backup_dir, max_backup_count):
        BackupDBUtils._ensure_backup_dir(backup_dir)
        backup_file_in_container = f"{database_name}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.sql"
        backup_file_on_host = os.path.join(backup_dir, backup_file_in_container)
        command = (
            f'docker exec {container_name} sh -c '
            f'"mysqldump --no-tablespaces -u{user} -p\'{password}\' {database_name} > {backup_file_in_container}"'
        )
        skip_ssl_command = (
            f'docker exec {container_name} sh -c '
            f'"mysqldump --skip-ssl --no-tablespaces -u{user} -p\'{password}\' {database_name} > {backup_file_in_container}"'
        )
        try:
            return_code = await BackupDBUtils._run_subprocess_shell(command)
            if return_code != 0:
                LOGGER.warning("BOT数据库备份失败，使用 skip-ssl 方式尝试备份")
                return_code = await BackupDBUtils._run_subprocess_shell(skip_ssl_command)
            if return_code != 0:
                LOGGER.error(f"BOT数据库备份失败, error code: {return_code}")
                return None
            await BackupDBUtils._run_subprocess_shell(
                f"docker cp {container_name}:{backup_file_in_container} {backup_file_on_host}"
            )
        except Exception as e:
            LOGGER.error(f"BOT数据库备份失败, error: {str(e)}")
            return None
        finally:
            await BackupDBUtils._run_subprocess_shell(f"docker exec {container_name} rm -f {backup_file_in_container}")
        LOGGER.info(f"BOT数据库备份成功,文件保存为 {backup_file_on_host}")
        BackupDBUtils._rotate_backups(backup_dir, database_name, "sql", max_backup_count)
        return backup_file_on_host

    @staticmethod
    async def backup_postgres_db(host, port, user, password, database_name, backup_dir, max_backup_count):
        BackupDBUtils._ensure_backup_dir(backup_dir)
        backup_file = os.path.join(backup_dir, f"{database_name}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.dump")
        env = dict(os.environ)
        env["PGPASSWORD"] = str(password)
        try:
            return_code = await BackupDBUtils._run_subprocess_exec(
                "pg_dump",
                "-h",
                str(host),
                "-p",
                str(port),
                "-U",
                str(user),
                "-d",
                str(database_name),
                "-F",
                "c",
                "-f",
                backup_file,
                env=env,
            )
            if return_code != 0:
                LOGGER.error(f"BOT数据库备份失败, error code: {return_code}")
                return None
            LOGGER.info(f"BOT数据库备份成功,文件保存为 {backup_file}")
            BackupDBUtils._rotate_backups(backup_dir, database_name, "dump", max_backup_count)
            return backup_file
        except Exception as e:
            LOGGER.error(f"BOT数据库备份失败, error: {str(e)}")
            return None

    @staticmethod
    async def backup_postgres_db_docker(container_name, user, password, database_name, backup_dir, max_backup_count):
        BackupDBUtils._ensure_backup_dir(backup_dir)
        backup_file_in_container = f"{database_name}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.dump"
        backup_file_on_host = os.path.join(backup_dir, backup_file_in_container)
        command = (
            f'docker exec {container_name} sh -c '
            f'"PGPASSWORD=\'{password}\' pg_dump -U {user} -d {database_name} -F c -f {backup_file_in_container}"'
        )
        try:
            return_code = await BackupDBUtils._run_subprocess_shell(command)
            if return_code != 0:
                LOGGER.error(f"BOT数据库备份失败, error code: {return_code}")
                return None
            await BackupDBUtils._run_subprocess_shell(
                f"docker cp {container_name}:{backup_file_in_container} {backup_file_on_host}"
            )
        except Exception as e:
            LOGGER.error(f"BOT数据库备份失败, error: {str(e)}")
            return None
        finally:
            await BackupDBUtils._run_subprocess_shell(f"docker exec {container_name} rm -f {backup_file_in_container}")
        LOGGER.info(f"BOT数据库备份成功,文件保存为 {backup_file_on_host}")
        BackupDBUtils._rotate_backups(backup_dir, database_name, "dump", max_backup_count)
        return backup_file_on_host
