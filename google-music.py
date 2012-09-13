from errno import ENOENT
import logging
import pickle
import re
from sys import argv
from stat import S_IFDIR, S_IFLNK, S_IFREG
from time import time
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

import helpers

class GoogleMusic(LoggingMixIn, Operations):

    def __init__(self, email, password):
        helpers.login(email, password)
        self.files = {}
        self.files['/'] = dict(st_mode=(S_IFDIR | 0755), st_ctime=time(), st_mtime=time(), st_atime=time(), st_nlink=2)

    def getattr(self, path, fh=None):
        size = helpers.get_track_size(path)
        return dict(st_mode=(S_IFDIR | 0755), st_nlink=2, st_ctime=time(), st_mtime=time(), st_atime=time(), st_size=size)

    def readdir(self, path, fh):
        if path == '/':
            return ['.', '..'] + [artist['artist'] for artist in helpers.get_artists()]
        elif len(re.findall('/', path)) == 1:
            positions = re.finditer('/', path)
            for match in positions:
                position = match.span()[1]
            return ['.', '..'] + [album['album'] for album in helpers.get_albums(path[position:])]
        elif len(re.findall('/', path)) == 2:
            artist, album = path[1:].split('/')
            return ['.', '..'] + ['%02d - %s' % (track['track'], track['title']) for track in helpers.get_tracks(artist, album)]
            #return ['.', '..', artist, album]
        else:
            return ['.', '..', path]

if __name__ == '__main__':
    if len(argv) != 4:
        print('usage: %s <google email> <password> <mountpoint>' % argv[0])
        exit(1)

    logging.getLogger().setLevel(logging.DEBUG)
    fuse = FUSE(GoogleMusic(argv[1], argv[2]), argv[3], foreground=True)