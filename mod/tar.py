"""This module exists for other modules to create and upload tar files \
that are automatically split when uploaded"""
from utils import Cog
import tempfile
import aiofiles
import os
import tarfile
import discord


__author__ = "Dark Kirb"
__license__ = "BSD-2clause"
__website__ = "https://github.com/DarkKirb/poyobot/blob/master/mod/tar.py"
__version__ = "1.0"


class TARInstance:
    def __init__(self, dest, tarfname):
        self.dest = dest
        self.tarfname = tarfname
        self.files = []

    async def __aenter__(self):
        self._tempdir = tempfile.TemporaryDirectory()
        self._tempdir_enter = self._tempdir.__enter__
        self._tempdir_exit = self._tempdir.__exit__
        self.tempdir = self._tempdir_enter()
        return self

    async def __aexit__(self, *ex):
        tar_count = 0
        tar_name_prefix = self.tarfname + "-"
        tar_name_prefix = os.path.join(self.tempdir, tar_name_prefix)
        tar_name_suffix = ".tar"
        tfn = tar_name_prefix + str(tar_count) + tar_name_suffix
        tf = tarfile.open(tfn, "w")
        size = 2 * 20 * 512
        for fname in self.files:
            size += os.path.getsize(fname)
            size += 512 - (size % 512)
            if size > 7 * 1024 * 1024:
                tf.close()
                tar_count += 1
                await self.dest.send(file=discord.File(tfn))
                tfn = tar_name_prefix + str(tar_count) + tar_name_suffix
                tf = tarfile.open(tfn, "w")
                size = 2 * 20 * 512
                size += os.path.getsize(fname)
                size += 512 - (size % 512)
            tf.add(fname)
        tf.close()
        await self.dest.send(file=discord.File(tfn))
        self._tempdir_exit(*ex)

    def open(self, fname, mode="w"):
        fname = os.path.join(self.tempdir, fname)
        if fname not in self.files:
            self.files.append(fname)
        return aiofiles.open(fname, mode)

    def mkdir(self, dname):
        os.makedirs(os.path.join(self.tempdir, dname), exist_ok=True)

    def __getitem__(self, fname):
        return self.open(fname)


class TAR(Cog):
    create = TARInstance


def setup(bot):
    global cog
    cog = TAR(bot)
