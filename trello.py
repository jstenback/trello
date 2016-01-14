#!/usr/bin/env python

import json
import urllib
from http.client import HTTPSConnection, HTTPException
import os

class TrelloSession:
    def __init__(self):
        self._httpconn = HTTPSConnection('api.trello.com')
        #self._httpconn.set_debuglevel(1)

        self._boards = None

        with open(os.path.expanduser("~/.trello"), 'r') as f:
            self._config = json.load(f)

        self._key = self._config['key']
        self._token = self._config['token']

    @property
    def boards(self):
        if self._boards is None:
            self._boards = {}
            for b in self.request('GET', '/1/member/me/boards'):
                board = Board(self, b)
                self._boards[board.name] = board

        return self._boards

    def request(self, action, path, post_data = {}):
        data = post_data.copy()
        data['key'] = self._key
        data['token'] = self._token

        path += '?' + urllib.parse.urlencode(data)

        self._httpconn.request(action, path, None, {})
        response = self._httpconn.getresponse()

        if response.status != 200:
            raise Exception("Error {}: {}" \
                            .format(response.status, response.reason))

        return json.loads(response.read().decode('utf-8'))

class List:
    def __init__(self, session, data):
        self._session = session
        self._data = data
        self.name = self._data['name']
        self.id = self._data['id']

    def createCard(self, name, descr, labels = ""):
        data = {
            'name': name,
            'desc': descr,
            'due': "null",
            'urlSource': "null",
            'idList': self.id,
            'idLabels': labels
        }

        return self._session.request('POST', '/1/cards', data)

class Label:
    def __init__(self, session, data):
        self._session = session
        self._data = data
        self.name = self._data['name']
        self.id = self._data['id']

class Member:
    def __init__(self, session, data):
        self._session = session
        self._data = data
        self.username = self._data['username']
        self.fullName = self._data['fullName']
        self.id = self._data['id']

class Board:
    def __init__(self, session, data):
        self._session = session
        self._data = data
        self.name = self._data['name']
        self.id = self._data['id']

        self._lists = None
        self._labels = None
        self._members = None

    @property
    def lists(self):
        if self._lists == None:
            lists = self._session.request('GET', '/1/boards/{}/lists' \
                                          .format(self.id))

            self._lists = {}

            for list in lists:
                self._lists[list['name']] = List(self._session, list)

        return self._lists

    @property
    def labels(self):
        if self._labels == None:
            labels = self._session.request('GET', '/1/boards/{}/labels' \
                                           .format(self.id))

            self._labels = {}

            for label in labels:
                self._labels[label['name']] = Label(self._session, label)

        return self._labels

    @property
    def members(self):
        if self._members == None:
            members = self._session.request('GET', '/1/boards/{}/members' \
                                            .format(self.id))

            self._members = {}

            for member in members:
                self._members[member['username']] = Member(self._session,
                                                           member)

        return self._members

    def addMember(self, name, member_type = 'normal'):
        self._session.request('PUT', '/1/boards/{}/members/{}' \
                              .format(self.id, name),
                              {'idMember': name,
                               'type': member_type})

    def copyMembers(self, to_board):
        for member in self.members:
            to_board.addMember(self.members[member].username)
