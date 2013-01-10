'''
    8tracks XBMC Plugin
    Copyright (C) 2011 t0mm0
    Copyright (C) 2013 Stephen B Chisholm

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import Addon
import os.path
import re
import simplejson as json
import urllib, urllib2
import xbmc
        
class EightTracks:
    _BASE_URL = 'http://8tracks.com'
    _SECURE_BASE_URL = 'https://8tracks.com'
    _API_KEY = 'a9c6e62af4f4bce76e73749dd071840b5d42fde0'    
    SORT_RECENT = 'recent'
    SORT_HOT = 'hot'
    SORT_POPULAR = 'popular'
    SORT_RANDOM = 'random'
    SORT_LIKED = 'liked'
    
    def __init__(self, username='', password=''):
        set_path = xbmc.translatePath(os.path.join(Addon.profile_path, 'set'))
        try:
            os.makedirs(os.path.dirname(set_path))
        except OSError:
            pass
            
        try:
            Addon.log('loading set number')
            f = open(set_path)
            self._set = f.readline().strip()    
            f.close()
        except IOError:
            Addon.log('getting set number')
            f = open(set_path, 'w')
            self._set = self.new_set()
            f.write(self._set)
            f.close()

        # get the user id
        if username and password:
            login = self.login(username, password)
            if login['logged_in']:
                self.user_id = login['current_user']['id']
            else: 
                Addon.show_error(['Invalid username or password.'])
                self.user_id = 0
        else:
            self.user_id = 0
        Addon.log('user_id: %s' % self.user_id)

    def logged_in(self):
        return bool(self.user_id)
    
    def new_set(self):
        return self._get_json('sets/new')['play_token']

    def mixes(self, sort='hot', tag='', search='', page=1):
        return self._get_json('mixes', {'sort': sort, 'tag': tag, 
                                        'q': search, 'page': page})
    def liked_mixes(self, page):
        return self._get_json('users/%d/mixes' % self.user_id, {'view': 'liked'})

    def play(self, mix_id):
        return self._get_json('sets/%s/play' % self._set, {'mix_id': mix_id})

    def next(self, mix_id):
        return self._get_json('sets/%s/next' % self._set, {'mix_id': mix_id})

    def next_mix(self, mix_id):
        return self._get_json('sets/%s/next_mix' % self._set, 
                              {'mix_id': mix_id})
    def report_song(self, track_id, mix_id):
        '''In order to be legal and pay royalties properly, 8tracks must report
        every performance of every song played to SoundExchange. A "performance"
        is counted when the 30 second mark of a song is reached. So at 30
        seconds, you must call the following:'''
        return self._get_json('sets/%s/report' % self._set, 
                              {'track_id': track_id, 'mix_id': mix_id})

    def tags(self, page):
        return self._get_json('tags', {'page': page})

    def login(self, username, password):
        return self._get_json('sessions', https=True, 
            data='login=%s&password=%s' % (username, password))

    def _build_url(self, path, queries={}, https=False):
        query = Addon.build_query(queries)
        if https:
            return '%s/%s?%s' % (self._SECURE_BASE_URL, path, query) 
        else:
            return '%s/%s?%s' % (self._BASE_URL, path, query) 

    def _fetch(self, url, form_data=False):
        if form_data:
            Addon.log('posting: %s %s' % (url, str(form_data)))
            req = urllib2.Request(url, form_data)
        else:
            Addon.log('getting: ' + url)
            req = url

        try:
            response = urllib2.urlopen(url)
            return response
        except urllib2.URLError, e:
            Addon.log(str(e), True)
            return False
        
    def _get_html(self, path, queries={}):
        html = False
        url = self._build_url(path, queries)

        response = self._fetch(url)
        if response:
            html = response.read()
        else:
            html = False
        return html

    def _get_json(self, method, queries={}, data='', https=False):
        json_response = None
        queries['api_key'] = self._API_KEY
        queries['api_version'] = 2
        url = self._build_url(method + '.json', queries, https)
        Addon.log('getting ' + url)
        try:
            if data:
                response = urllib2.urlopen(url, data)
            else:
                response = urllib2.urlopen(url)
            try:
                json_response = json.loads(response.read())
            except ValueError:
                Addon.show_error([Addon.get_string(30005)])
                return False
        except urllib2.HTTPError, e:
            if e.code == 422:
                return {'logged_in': False}
            else:
                Addon.show_error([Addon.get_string(30006), str(e.reason)])
        except urllib2.URLError, e:
            Addon.show_error([Addon.get_string(30006), str(e.reason)])
            return False

        if json_response is None:
            return False

        if json_response.get('errors', None):              
            Addon.show_error(str(json_response['errors'][0]))  
            return False 
        else:
            Addon.log(json.dumps(json_response, sort_keys=True,
                             indent=4, separators=(',', ': ')))
            return json_response
            
            
class EightTracksPlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        xbmc.Player.__init__(self)
        self.et = kwargs['et']
        self.pl = Addon.get_playlist(xbmc.PLAYLIST_MUSIC, True)
        self.ended = False
        self.track_playing = False
        self.track_id_lookup = {}

    def onPlayBackStarted(self):
        Addon.log('onPlayBackStarted')
        return super(EightTracksPlayer, self).onPlayBackStarted()
        
    def onPlayBackStopped(self):
        Addon.log('onPlayBackStopped')
        self.ended = True

    def onPlayBackEnded(self):
        Addon.log('onPlayBackEnded')
        return super(EightTracksPlayer, self).onPlayBackEnded()

    def onQueueNextItem(self):
        Addon.log('onQueueNextItem')
        self.add_next()
        return super(EightTracksPlayer, self).onQueueNextItem()
        
    def play_mix(self, mix_id, mix_name, user, img):
        track_reported = False
        reporting_time = 30 #seconds
        Addon.log('play_mix')
        self.mix_id = mix_id
        self.mix_name = mix_name
        self.user = user
        self.img = img
        self.add_next(True)
        #for the first time add two songs.
        self.add_next()
        self.play(self.pl)
        while not self.ended:
            if self.isPlaying():
                if not track_reported and self.getTime() >= reporting_time:
                    try:
                        Addon.log('report track here (track_id %d, mix_id %s)' % ( 
                                  self.track_id_lookup[self.getPlayingFile()], 
                                  self.mix_id))
                        self.et.report_song(
                            self.track_id_lookup[self.getPlayingFile()], self.mix_id)
                        track_reported = True
                    except KeyError:
                        Addon.log('unable to report current playing file %s' % (
                                self.getPlayingFile()))
                if track_reported and self.getTime() < reporting_time:
                    Addon.log('resetting the reported flag')
                    # reset the reported flag for the next track
                    track_reported = False
                Addon.log('%02d:%02d / %02d:%02d' % (
                          self.getTime()/60, self.getTime()%60,
                          self.getTotalTime()/60, self.getTotalTime()%60))
            Addon.log('player sleeping...')
            xbmc.sleep(1000)
        
    def add_next(self, first=False):
        Addon.log('add_next')
        if first:
            result = self.et.play(self.mix_id)
        else:
            result = self.et.next(self.mix_id)
        if result['set']['at_end']:
            Addon.log('moving to next mix')
            result = self.et.next_mix(self.mix_id)
            next_mix = result['next_mix']
            self.mix_id = next_mix['id']
            self.mix_name = next_mix['name']
            self.user = next_mix['user']['login']
            self.img = next_mix['cover_urls']['max200']
            result = self.et.play(self.mix_id)

        t = result['set']['track']
        comment = 'mix: %s by %s' % (self.mix_name, self.user)
        # keep the track id for reporting later on
        self.track_id_lookup[t['url']] = t['id']
        Addon.add_music_item(t['url'], {'title': t['name'], 
                                        'artist': t['performer'], 
                                        'comment': comment, 
                                        'album': t['release_name']},
                             img=self.img, playlist=self.pl)

