from asyncio import gather
from dataclasses import dataclass
from datetime import datetime
from os import makedirs, readlink
from os import remove as rm
from os import stat
from os.path import isfile
from pathlib import Path, PurePath
from shutil import copy2, copytree
from shutil import move as mv
from shutil import rmtree
from stat import S_ISDIR, S_ISLNK, filemode
from typing import AbstractSet, Iterable, Mapping, Optional

from std2.asyncio import to_thread
from std2.stat import RW_R__R__, RWXR_XR_X

_FOLDER_MODE = RWXR_XR_X
_FILE_MODE = RW_R__R__


def ancestors(path: PurePath) -> AbstractSet[PurePath]:
    return {p for p in PurePath(path).parents}


def unify_ancestors(paths: AbstractSet[PurePath]) -> AbstractSet[PurePath]:
    return {p for p in paths if ancestors(p).isdisjoint(paths)}


@dataclass(frozen=True)
class FSstat:
    permissions: str
    user: str
    group: str
    date_mod: datetime
    size: int
    link: Optional[str]


try:
    from grp import getgrgid
    from pwd import getpwuid

    def _get_username(uid: int) -> str:
        try:
            return getpwuid(uid).pw_name
        except KeyError:
            return str(uid)

    def _get_groupname(gid: int) -> str:
        try:
            return getgrgid(gid).gr_name
        except KeyError:
            return str(gid)

except ImportError:

    def _get_username(uid: int) -> str:
        return str(uid)

    def _get_groupname(gid: int) -> str:
        return str(gid)


async def fs_stat(path: PurePath) -> FSstat:
    def cont() -> FSstat:
        stats = stat(path, follow_symlinks=False)
        permissions = filemode(stats.st_mode)
        user = _get_username(stats.st_uid)
        group = _get_groupname(stats.st_gid)
        date_mod = datetime.fromtimestamp(stats.st_mtime)
        size = stats.st_size
        link = readlink(path) if S_ISLNK(stats.st_mode) else None
        fs_stat = FSstat(
            permissions=permissions,
            user=user,
            group=group,
            date_mod=date_mod,
            size=size,
            link=link,
        )
        return fs_stat

    return await to_thread(cont)


async def exists(path: PurePath, follow: bool) -> bool:
    def cont() -> bool:
        try:
            stat(path, follow_symlinks=follow)
        except (OSError, ValueError):
            return False
        else:
            return True

    return await to_thread(cont)


async def exists_many(
    paths: Iterable[PurePath], follow: bool
) -> Mapping[PurePath, bool]:
    existance = await gather(*(exists(path, follow=follow) for path in paths))
    return {path: exi for path, exi in zip(paths, existance)}


async def is_file(path: PurePath) -> bool:
    return await to_thread(lambda: isfile(path))


async def _mkdir(path: PurePath) -> None:
    def cont() -> None:
        makedirs(path, mode=_FOLDER_MODE, exist_ok=True)

    await to_thread(cont)


async def mkdir(paths: Iterable[PurePath]) -> None:
    await gather(*map(_mkdir, paths))


async def _new(path: PurePath) -> None:
    def cont() -> None:
        makedirs(path.parent, mode=_FOLDER_MODE, exist_ok=True)
        Path(path).touch(mode=_FILE_MODE, exist_ok=True)

    await to_thread(cont)


async def new(paths: Iterable[PurePath]) -> None:
    await gather(*map(_new, paths))


async def _rename(src: PurePath, dst: PurePath) -> None:
    def cont() -> None:
        makedirs(dst.parent, mode=_FOLDER_MODE, exist_ok=True)
        mv(str(src), str(dst))

    await to_thread(cont)


async def rename(operations: Mapping[PurePath, PurePath]) -> None:
    await gather(*(_rename(src, dst) for src, dst in operations.items()))


async def _remove(path: PurePath) -> None:
    def cont() -> None:
        stats = stat(path, follow_symlinks=False)
        if S_ISDIR(stats.st_mode):
            rmtree(path)
        else:
            rm(path)

    await to_thread(cont)


async def remove(paths: Iterable[PurePath]) -> None:
    await gather(*map(_remove, paths))


async def _cut(src: PurePath, dest: PurePath) -> None:
    def cont() -> None:
        mv(str(src), str(dest))

    await to_thread(cont)


async def cut(operations: Mapping[PurePath, PurePath]) -> None:
    await gather(*(_cut(src, dst) for src, dst in operations.items()))


async def _copy(src: PurePath, dst: PurePath) -> None:
    def cont() -> None:
        stats = stat(src, follow_symlinks=False)
        if S_ISDIR(stats.st_mode):
            copytree(src, dst)
        else:
            copy2(src, dst, follow_symlinks=False)

    await to_thread(cont)


async def copy(operations: Mapping[PurePath, PurePath]) -> None:
    await gather(*(_copy(src, dst) for src, dst in operations.items()))
