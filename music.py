from mpd import MPDClient

#wrapper around the mpd client for with ... as ... access
class mpd_connection():
# class used to connect to the mpd server with a 'with' statment. This makes
# sure we always disconnect nicely
    def __init__(self):
        self.client = musicpd.MPDClient()
    def __enter__(self):
        self.client.timeout = 10
        self.client.connect("localhost", 6600)
        return self.client
    def __exit__(self, type, value, traceback):
        self.client.disconnect()

def start_shuffle_playlist(playlist):
    with mpd_connection() as mpd_client:
        mpd_client.clear() #clear current playlist
        mpd_client.load(playlist)
        mpd_client.shuffle()
        mpd_client.play(0)
        mpd_client.pause(0) #apparently necessary to really start playing
