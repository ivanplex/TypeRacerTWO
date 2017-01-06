#!/usr/bin/env python

# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START imports]
import os
import sys
import urllib
import json
import random
import time

from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import ndb
#from django.utils import simplejson as json

import races
import models

import jinja2
import webapp2
import lxml.html

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
# [END imports]

class Generate(webapp2.RequestHandler):

    def get(self):

        for i in range(30, 130):
            result = urlfetch.fetch('http://www.seanwrona.com/typeracer/text.php?id=' + str(i))
            htmltree = lxml.html.fromstring(result.content)

            p_tags = htmltree.xpath('//p')
            p_content = [p.text_content() for p in p_tags]

            quote = p_content[0].strip()
            source = p_content[1].strip()

            print(str(i) + ' "' + quote + '" "' + source + '"')
            print(i);

            tempEx = models.Excerpt(id = i-30, passage = quote, source = source)
            tempEx.key = ndb.Key(models.Excerpt, i-30);
            tempEx.put()

class Load(webapp2.RequestHandler):
    def get(self):
        for i in range(0,100):
            tempEx = ndb.Key(models.Excerpt, i).get()
            print(str(i) + ' "' + tempEx.passage + '" "' + tempEx.source + '"');

# [START Leaderboard]
class Leaderboard(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        responseDict = dict()
        if user:
            query = models.Player.query(Player.user_id == user.user_id())
            player = query.fetch(1);
            responseDict["u"] = json.dumps(player[0].to_dict())
        else:
            PLAYERS_PER_PAGE = 10
            query = Player.query().order(-Player.wpm)
            leaders = query.fetch(PLAYERS_PER_PAGE)
            responseDict["lb"] = json.dumps(leaders.to_dict())
            self.response.write(responseDict)

# [START main_page]
class MainPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            nickname = user.nickname()

            logout_url = users.create_logout_url('/')

            template = JINJA_ENVIRONMENT.get_template('web/index.html')

            greeting = template.render(
                nick=nickname, logouturl=logout_url)
            self.response.write(greeting)
            return
        else:
            login_url = users.create_login_url('/')
            greeting = '<a href="{}">Sign in</a>'.format(login_url)
            self.response.write(
                '<html><body>{}</body></html>'.format(greeting))
            return


# [END main_page]

# [START change_player_name]
class Player(webapp2.RequestHandler):
    def post(self):
        user = users.get_current_user()

        if not user:
            self.redirect('/')
            return

        p = models.Player.get_by_user(models.Player, user)

        if not p:
            p = models.Player(nickname=user.nickname(), id=user.user_id())

        new_nickname = self.request.get("new_nickname", default_value="null")

        exists_in_db = not models.Player.get_by_nickname(models.Player, new_nickname) == None

        if new_nickname == "null" or len(new_nickname) >= 50 or len(new_nickname) == 0 or exists_in_db:
            self.response.set_status(400, 'Unrecognised Media Type')
            self.response.out.write('{"status":"error"}')
            return

        p.nickname = new_nickname
        p.put()

        self.response.out.write('{"status":"success"}')

# [END main_page]

# [START play]
class Play(webapp2.RequestHandler):

    # game logic handled by POSTs
    def post(self):
        # check if user is authenticated
        user = users.get_current_user()

        # redirect user to login if not authenticated
        if user is None:
            self.redirect('/')
            return

        # player id and current time
        current_time = int(time.time())
        player_id = user.user_id()

        # initialise variables if they do not exist and persist in registry
        app = webapp2.get_app()

        current_room = app.registry.get('current_room')
        rooms = app.registry.get('rooms')

        # what is the current room we are filling up
        if not current_room:
            current_room = random.randrange(sys.maxint)
            app.registry['current_room'] = current_room

        # rooms existing in memory
        if not rooms:
            rooms = {}
            app.registry['rooms'] = rooms

        # performs input santitation on content type -- we only accept JSON
        if self.request.headers.get('content_type') != 'application/json':
            self.response.set_status(400, 'Unrecognised Media Type')
            self.response.write('Unrecognised Media Type')
            return

        # initialise empty object
        obj = None

        try:
            obj = json.loads(self.request.body)
        except ValueError, e:
            self.response.set_status(400, 'Invalid JSON')
            self.response.write('Invalid JSON')
            return

        # if we are here, the JSON is valid and we can proceed with checks
        if 'room_id' not in obj or 'timestamp' not in obj:
            self.response.set_status(400, 'Invalid Request Parameters')
            self.response.write('Invalid Request Parameters')
            return
 
        # check if the time is properly typed
        user_time = obj.get('timestamp')
 
        if not isinstance(user_time, int):
            self.response.set_status(400, 'Timestamp must be a number')
            self.response.write('Timestamp must be a number')
            return

        # if the room_id is properly typed...
        room_id = obj.get('room_id')
        room = None

        if isinstance(room_id, int):

            # user isn't in a room, allocate user to a room
            if room_id == -1:


                while room == None:
                    # test the current room for whether it is full or not
                    room = rooms.get(current_room)

                    # room doesn't exist, we create new
                    if not room:

                        # assign a random excerpt
                        excerpt = models.Excerpt.get_random_Excerpt()

                        print(excerpt.passage)

                        room = {}
                        room['players'] = []
                        room['start_time'] = -1
                        room['text_id'] = excerpt.id
                        room['text'] = excerpt.passage
                        room['source'] = excerpt.source
                        room['room_id'] = current_room

                        rooms[current_room] = room

                    # check if room is full or start time has passed current time (TODO: fix/optimise)
                    if len(room['players']) == 5 or (room['start_time'] < current_time and room['start_time'] != -1):
                        # generate a random room ID, this will (very rarely) collide with a valid room or create a new room
                        current_room = random.randrange(sys.maxint)

                        # set the room to None
                        room = None
                    else:
                        userInRoom = False
                        # user is allowed to participate in the current room
                        player = {}

                        # if the user is in the current room then we tell them to buzz off
                        for player in room['players']:
                            if player['id'] == player_id:
                                userInRoom = True

                        if not userInRoom:
                            # user is allowed to participate in the current room
                            player = {}

                            player['id'] = player_id
                            player['name'] = user.nickname()
                            player['words_done'] = 0
                            players['updated_at'] = current_time

                            # add the player to the current room
                            room['players'].append(player)

                            # tell update the start_time to 15 seconds from now
                            if (len(room['players'])) >= 3:
                                room['start_time'] = current_time + 15


            # user is in a game, we do game stuff
            else:
                room = rooms.get(room_id)

                # room doesn't exist anymore, game over or invalid room?
                if not room:
                    self.response.set_status(404, 'Room Invalid')
                    self.response.write('Room Not Found!')
                    return

                player = None

                # check for matching player in room using ID
                for _player in room['players']:
                    if _player['id'] == player_id:
                        player = _player
                        break

                if not player:
                    self.response.set_status(403, 'Not In Room')
                    self.response.write('User Not In Room')
                    return

                words_done = obj.get('words_done')

                # we don't have words done in this request...
                if not words_done:
                    self.response.set_status(400, 'Words Done Not In Request')
                    self.response.write('Unable to find Words Done')
                    return

                if words_done < 0 or words_done > len(room['text']):
                    self.response.set_status(400, 'Invalid Words Done Do Not Cheat')
                    self.response.write('Words Done Is Not Valid')
                    return

                # game over, save status for ALL players
                # GAME OVER GAME OVER GAME OVER
                if room['start_time'] + 90 > current_time:
                    # remove the reference from the game
                    del rooms[room['room_id']]
                    
                    # create and persist a race (for you to handle Sid, we have)
                    # we need to create the race first to get the unique key
                    room['text_id']
                    room['start_time']
                    race = models.Race(excerpt_id=room['text_id'], start_time=room['start_time'], players=room['players'])
                    race.put()

                    # iterate over players in room -- the wpm is calculated here
                    # we can create the racerstats here this way
                    for _player in room['players']:
                        d_t = _player['updated_at'] - room['start_time']
                        wpm = float(_player['words_done']) / float(d_t) * 60
                        _player['id']
                        raceStats = models.RacerStats(race_id = race.key.id(), user_id = _player['id'], wpm = wpm)
                        raceStats.put()

                        ndb_player = models.Player.get_by_user_id(models.Player, _player['id'])
                        newWPM = ((ndb_player.wpm*ndb_player.games_played)+wpm)/(ndb_player.games_played+1)
                        player.wpm = newWPM
                        player.put()
                    # update player stats, wpm as a recalculated average
                    # :D

                    #SIDHARTThhhhHH!!!!

                    # kill the room and tell users they need to search for a new game
                    room = None
                    current_room = -1
                else:
                    # update the users :D
                    player['words_done'] = words_done
                    player['updated_at'] = current_time

                    # player finished game early
                    if words_done == len(room['text']):
                        room = None
                        current_room = -1
        else:
            self.response.set_status(400, 'Room_ID Must Be A Number')
            self.response.write('Room ID Not A Number??')
            return


        # build the response json
        res = {}
        res['player_id'] = player_id
        res['timestamp'] = current_time
        res['room'] = room

        self.response.write(json.dumps(res))


    def get(self):
        user = users.get_current_user()

        if user:
            nickname = user.user_id()
            logout_url = users.create_logout_url('/')
            greeting = 'Welcome, {}! (<a href="{}">sign out</a>)'.format(
                nickname, logout_url)
        else:
            login_url = users.create_login_url('/')
            greeting = '<a href="{}">Sign in</a>'.format(login_url)

        self.response.write(
            '<html><body>{}</body></html>'.format(greeting))

    def getRoomKey(self):
        race_key = race.put()


# [END play]

# [START app]
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/play', Play),
    ('/generate', Generate),
    ('/load', Load),
    ('/races/new', 'races.New'),
    ('/leaderboard', Leaderboard),
    ('/player', Player),
], debug=True)
# [END app]
