from gmusicapi import Api
from filecache import filecache
import sqlite3
import re

api = Api()
conn = sqlite3.connect('music.sqlite3', check_same_thread = False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

def login(email, password):
    attempts = 0

    while not api.is_authenticated() and attempts < 3:
        api.login(email, password)
        attempts += 1

    if api.is_authenticated():
        print 'Logged in'
        initialise_database()
        store_songs(get_songs())
        print 'Songs cached'
    else:
        print 'Could not log in'
        exit(1)

def initialise_database():
    cursor.execute('''CREATE TABLE IF NOT EXISTS songs (
                song_id VARCHAR NOT NULL PRIMARY KEY,
                comment VARCHAR,
                rating INTEGER,
                last_played INTEGER,
                disc INTEGER,
                composer VARCHAR,
                year INTEGER,
                album VARCHAR,
                title VARCHAR,
                album_artist VARCHAR,
                type INTEGER,
                track INTEGER,
                total_tracks INTEGER,
                beats_per_minute INTEGER,
                genre VARCHAR,
                play_count INTEGER,
                creation_date INTEGER,
                name VARCHAR,
                artist VARCHAR,
                url VARCHAR,
                total_discs INTEGER,
                duration_millis INTEGER,
                album_art_url VARCHAR,
                display_name VARCHAR,
                stream_url VARCHAR
        )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS playlists (
                playlist_id VARCHAR NOT NULL PRIMARY KEY,
                name VARCHAR,
                type VARCHAR,
                fetched BOOLEAN
        )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS playlists_songs (
                playlist_id VARCHAR,
                song_id VARCHAR,
                FOREIGN KEY(playlist_id) REFERENCES playlists(playlist_id) ON DELETE CASCADE,
                FOREIGN KEY(song_id) REFERENCES songs(song_id) ON DELETE CASCADE
        )''')

    cursor.execute('''CREATE INDEX IF NOT EXISTS playlistindex ON playlists_songs(playlist_id)''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS songindex ON playlists_songs(song_id)''')

    conn.commit()

def store_songs(songs, playlist_id = 'all_songs'):
    new_songs = []
    playlist_songs = []

    clear_playlist(playlist_id, songs)

    for api_song in songs:
        song = {
            'song_id': api_song['id'],
            'comment': api_song['comment'],
            'rating': api_song['rating'],
            'last_played': api_song['lastPlayed'],
            'disc': api_song['disc'],
            'composer': api_song['composer'],
            'year': api_song['year'],
            'album': re.sub('/', '_', api_song['album']),
            'title': api_song['title'],
            'album_artist': api_song['albumArtist'],
            'type': api_song['type'],
            'track': api_song['track'],
            'total_tracks': api_song['totalTracks'],
            'beats_per_minute': api_song['beatsPerMinute'],
            'genre': api_song['genre'],
            'play_count': api_song['playCount'],
            'creation_date': api_song['creationDate'],
            'name': api_song['name'],
            'artist': api_song['artist'],
            'url': api_song['url'],
            'total_discs': api_song['totalDiscs'],
            'duration_millis': api_song['durationMillis'],
            'album_art_url': api_song.get('albumArtUrl', None),
            'display_name': get_song_display_name(api_song)
        }

        existing_song = cursor.execute("SELECT * FROM songs WHERE song_id = ?", (api_song['id'],)).fetchone()
        if existing_song is not None:
            cursor.execute("UPDATE songs SET comment=:comment, rating=:rating, last_played=:last_played, disc=:disc, composer=:composer, year=:year, album=:album, title=:title, album_artist=:album_artist, type=:type, track=:track, total_tracks=:total_tracks, beats_per_minute=:beats_per_minute, genre=:genre, play_count=:play_count, creation_date=:creation_date, name=:name, artist=:artist, url=:url, total_discs=:total_discs, duration_millis=:duration_millis, album_art_url=:album_art_url, display_name=:display_name WHERE song_id=:song_id", song)
        else:
            new_songs.append(song)

        playlist_song = (playlist_id, api_song['id'])
        playlist_songs.append(playlist_song)

    cursor.executemany('INSERT INTO songs VALUES (:song_id, :comment, :rating, :last_played, :disc, :composer, :year, :album, :title, :album_artist, :type, :track, :total_tracks, :beats_per_minute, :genre, :play_count, :creation_date, :name, :artist, :url, :total_discs, :duration_millis, :album_art_url, :display_name, NULL)', new_songs)

    if playlist_id != 'all_songs':
        cursor.execute("UPDATE playlists SET fetched = 1 WHERE playlist_id = ?", (playlist_id,))
        cursor.executemany("INSERT INTO playlists_songs VALUES (?, ?)", playlist_songs)

    conn.commit()

def get_song_display_name(song):
    song = song.get
    track = str(song('track')).zfill(2)
    name = song('name').strip()

    return track + ' - ' + name


def clear_playlist(playlist_id, songs):
    if playlist_id == 'all_songs':
        song_ids = []
        for song in songs:
            song_ids.append(song['id'])

        cursor.execute("DELETE FROM playlists_songs WHERE playlist_id = ?", (playlist_id,))
        cursor.execute("DELETE FROM songs")
    else:
        cursor.execute("DELETE FROM playlists_songs WHERE playlist_id = ?", (playlist_id,))

    conn.commit()

@filecache(3600)
def get_songs():
    if api.is_authenticated():
        return api.get_all_songs()

def get_artists():
    artists = cursor.execute('SELECT DISTINCT(artist) FROM songs')

    return filter(None, artists.fetchall())

def get_albums(artist_name):
    albums = cursor.execute('SELECT DISTINCT(album) FROM songs WHERE artist=?', (artist_name,))

    return filter(None, albums.fetchall())

def get_tracks(artist_name, album_name):
    tracks = cursor.execute('SELECT * FROM songs WHERE artist=? AND album=?', (artist_name, album_name))

    return filter(None, tracks.fetchall())

def get_track_size(path):
    if len(re.findall('/', path)) == 3:
        artist, album, filename = path[1:].split('/')
        track = re.sub('[0-9][0-9] - ', '', filename)

        song = cursor.execute('SELECT * FROM songs WHERE artist=? AND album=? AND name=?', (artist, album, track))

        size = song.fetchone()['duration_millis'] * 16
    else:
        size = 0

    return size