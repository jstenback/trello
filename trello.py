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

        path = os.path.join(os.path.expanduser("~"), ".trello")

        with open(path, 'r') as f:
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

class Card:
    def __init__(self, session, data):
        self._session = session
        self._data = data
        self.name = self._data['name']
        self.id = self._data['id']
        self._labels = None
        self._label_ids = None
        self._members = None

    def __repr__(self):
        return "Card: " + json.dumps(self._data, indent = 4, sort_keys = True)

    @property
    def labels(self):
        if self._labels == None:
            self._labels = {}
            for l in self._data['labels']:
                label = Label(self._session, l)
                self._labels[label.name] = label

        return self._labels

    @property
    def label_ids(self):
        if self._label_ids == None:
            self._label_ids = {}
            for l in self._data['labels']:
                label = self.labels[l['name']]
                self._label_ids[label.id] = label

        return self._label_ids

    def addLabel(self, label):
        self._session.request('POST',
                              '/1/cards/{}/idLabels'.format(self.id),
                              {'value': label})

    def deleteLabel(self, label):
        self._session.request('DELETE',
                              '/1/cards/{}/idLabels/{}'.format(self.id, label),
                              {'value': label})

    @property
    def members(self):
        return self._data['idMembers']

    @members.setter
    def members(self, members):
        self._session.request('PUT',
                              '/1/cards/{}/idMembers'.format(self.id),
                              {'value': ','.join(members)})

    @property
    def desc(self):
        return self._data['desc']

    @desc.setter
    def desc(self, description):
        self._session.request('PUT',
                              '/1/cards/{}/desc'.format(self.id),
                              {'value': description})

    @property
    def shortUrl(self):
        return self._data['shortUrl']

    def addComment(self, comment):
        self._session.request('POST',
                              '/1/cards/{}/actions/comments'.format(self.id),
                              {'text': comment})

    def delete(self):
        self._session.request('DELETE', '/1/cards/{}'.format(self.id))

class List:
    def __init__(self, session, data):
        self._session = session
        self._data = data
        self.name = self._data['name']
        self.id = self._data['id']
        self._cards = None

    def __repr__(self):
        return "List: " + json.dumps(self._data, indent = 4, sort_keys = True)

    @property
    def cards(self):
        if self._cards == None:
            self._cards = {}
            for c in self._session.request('GET', '/1/lists/{}/cards' \
                                           .format(self.id)):
                card = Card(self._session, c)
                self._cards[card.name] = card

        return self._cards

    def createCard(self, name, descr, labels = "", members = ""):
        data = {
            'name': name,
            'desc': descr,
            'due': "null",
            'urlSource': "null",
            'idList': self.id,
            'idLabels': labels,
            'idMembers': members
        }

        return Card(self._session,
                    self._session.request('POST', '/1/cards', data))

class Label:
    def __init__(self, session, data):
        self._session = session
        self._data = data
        self.name = self._data['name']
        self.id = self._data['id']

    def __repr__(self):
        return "List: " + json.dumps(self._data, indent = 4, sort_keys = True)

class Member:
    def __init__(self, session, data):
        self._session = session
        self._data = data
        self.username = self._data['username']
        self.fullName = self._data['fullName']
        self.id = self._data['id']
        self._initials = None

    def __repr__(self):
        return "Member: " + json.dumps(self._data, indent = 4, sort_keys = True)

    @property
    def initials(self):
        if self._initials == None:
            self._initials = self._session.request('GET',
                                                   '/1/members/{}/initials' \
                                                   .format(self.id))['_value']

        return self._initials

class Board:
    def __init__(self, session, data):
        self._session = session
        self._data = data
        self.name = self._data['name']
        self.id = self._data['id']

        self._lists = None
        self._labels = None
        self._members = None

    def __repr__(self):
        return "Board: " + json.dumps(self._data, indent = 4, sort_keys = True)

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

    def delMember(self, id):
        self._session.request('DELETE', '/1/boards/{}/members/{}' \
                              .format(self.id, id),
                              {'idMember': id})

    def copyMembers(self, to_board):
        for member in self.members:
            to_board.addMember(self.members[member].username)
