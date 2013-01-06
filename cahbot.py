__author__ = 'Sebastian Ullrich'

import random
import os
from itertools import chain
from time import sleep

from config import CHATROOM_PRESENCE
from errbot.botplugin import BotPlugin
from errbot.utils import get_sender_username, get_jid_from_message
from errbot import botcmd

def good_cards(idxs, high):
	return (len(set(idxs)) == len(idxs)) and all([0 <= i < high for i in idxs])

class Player(object):
	def __init__(self, name, game):
		self.name = name
		self.game = game
		self.idxs = None
		self.hand = self.game.wcards[:Game.NUM_CARDS]
		del self.game.wcards[:Game.NUM_CARDS]

	def play(self, idxs):
		if self.idxs is not None:
			raise ValueError("You've already played your cards.")
		if not good_cards(idxs, len(self.hand)) or len(idxs) != self.game.num_gaps:
			raise ValueError("All you had to do was choose {0} damn cards, CJ.".format(self.game.num_gaps))

		self.idxs = idxs
		self.game.played_hands.append(self)

	def answer(self):
		text = (self.game.bcard + " ").split(Game.GAP)
		cards = [self.hand[i] for i in self.idxs]
		return "".join([x + y for x, y in zip(text, cards + [""])])

class Game(object):
	NUM_CARDS = 10
	GAP = '__________'

	def read_cards(filename):
		path = os.path.dirname(__file__)
		return open(os.path.join(path, filename)).read().partition('cards=')[2].split('<>')

	bcards = read_cards('bcards.txt')
	wcards = [s.rstrip('.') for s in read_cards('wcards.txt')]

	def __init__(self, gm):
		self.gm = gm
		self.bcard = random.choice(Game.bcards)
		self.num_gaps = max(1, self.bcard.count(Game.GAP))
		self.wcards = Game.wcards
		random.shuffle(self.wcards)
		self.players = {}
		self.played_hands = []

	def join(self, player):
		if player == self.gm or player in self.players:
			raise ValueError("Looks like you've already joined.")

		self.players[player] = Player(player, self)

	def play(self, player, idxs):
		if player == self.gm or player not in self.players:
			raise ValueError("You may not.")

		self.players[player].play(idxs)

class CAHBot(BotPlugin):
	""" Play a Good Game of Cards (TM) """

	def __init__(self):
		super(CAHBot, self).__init__()
		self.game = None

	@botcmd
	def cah_start(self, mess, args):
		""" Start a new round """
		self.game = Game(gm = mess.getFrom())
		self.send(str(self.game.gm), "Use '!cah vote <submission indices in ascending order of funniness>' when your patience is gone.")
		return """{0} draws a black card...

{1}

Use '!cah join' to join in!""".format(self.game.gm.getResource(), self.game.bcard)

	@botcmd
	def cah_join(self, mess, args):
		""" Join a game """
		def send(s):
			self.send(str(mess.getFrom()), s)

		if self.game is None:
			return send("No active game found.")

		try:
			self.game.join(mess.getFrom())
		except ValueError as e:
			return send(e.message)

		send("Here you go:\n" +\
				"\n".join(["{0} {1}".format(i, card) for i, card in enumerate(self.game.players[mess.getFrom()].hand)]) + "\n" +\
				"Use '!cah play <indices>' to play your card(s)")

	@botcmd(split_args_with=' ')
	def cah_play(self, mess, args):
		""" Play some card(s) """
		if self.game is None:
			return "No active game found."

		try:
			self.game.play(mess.getFrom(), map(int, args))
		except ValueError as e:
			return e.message

		nth = len(self.game.played_hands) - 1
		self.send(str(self.game.gm), "Submission {0} of {1}:\n{2}".format(nth, len(self.game.players), self.game.played_hands[nth].answer()))

	@botcmd(split_args_with=' ')
	def cah_vote(self, mess, args):
		def announce(s):
			self.send(CHATROOM_PRESENCE[0], s, message_type='groupchat')

		args = map(int, args)
		if not good_cards(args, len(self.game.played_hands)) or len(args) < 1:
			return "Try again."

		for i in args[:-1]:
			announce("{0}. place goes to...\n{1}: {2}".format(len(args) - i, self.game.played_hands[args[i]].name.getResource(), self.game.played_hands[args[i]].answer()))
			sleep(2)

		announce("And the winner is...")
		sleep(4)
		announce("{0}: {1}".format(self.game.played_hands[args[-1]].name.getResource(), self.game.played_hands[args[-1]].answer()))

		self.game = None
