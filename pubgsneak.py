import click
import configparser
import cv2
import json
import os
import pytesseract
import requests
import re
import time


class pubgPlayer:

	def __init__(self, player, pubg_season, api_key):
		
		self.player_name = player
		self.pubg_season = pubg_season
		
		self.api_key = api_key

		self.headers = {
			"Authorization": "Bearer " + self.api_key,
			"accept": "application/vnd.api+json"}

	def game_modes(self):
		#return ['solo-fpp', 'duo-fpp', 'squad-fpp', 'solo', 'duo', 'squad']
		return ['solo-fpp', 'duo-fpp', 'squad-fpp']

	def format_game_mode(self, game_mode):
		game_mode_map = {
			'^solo$': 'TPP Solo', '^duo$': 'TPP Duo', '^squad$': 'TPP Squad',
			'^solo-fpp$': 'Solo', '^duo-fpp$': 'Duo', '^squad-fpp$': 'Squad'
		}

		for k, v in game_mode_map.items():
			game_mode = re.sub(k, v, game_mode)

		return game_mode
	
	def _http_get(self, api_resource):
		with requests.get(api_resource, headers=self.headers) as r:
			if r.status_code == 200:
				return r.json()
			else:
				return False

	def player_name_to_accountid(self):
		d = self._http_get(f'https://api.pubg.com/shards/steam/players?filter[playerNames]={self.player_name}')
		if d:
			if 'data' in d:
				self.player_id = d['data'][0]['id']
				return True

	def get_season_stats(self):
		d = self._http_get(f'https://api.pubg.com/shards/steam/players/{self.player_id}/seasons/{self.pubg_season}')
		if d:
			self.season_stats = d['data']['attributes']['gameModeStats']
			return True

	def has_games_played_in_season(self):
		for game_mode in self.game_modes():
			if self.season_stats[game_mode]['roundsPlayed'] > 0:
				return True

	def has_games_played_in_game_mode(self, game_mode):
		if self.season_stats[game_mode]['roundsPlayed'] > 0:
			return True

	def rounds_played(self, game_mode):
		return self.season_stats[game_mode]['roundsPlayed']

	def kill_death_ratio(self, game_mode):
			return round(self.season_stats[game_mode]['kills'] / self.season_stats[game_mode]['losses'], 2)

	def head_shot_ratio(self, game_mode):
		try:
			return round(self.season_stats[game_mode]['headshotKills'] / self.season_stats[game_mode]['kills'] * 100, 1)
		except:
			return 0

	def win_ratio(self, game_mode):
		return round(self.season_stats[game_mode]['wins'] / self.season_stats[game_mode]['roundsPlayed'] * 100, 1)

	def average_damage(self, game_mode):
		return int(self.season_stats[game_mode]['damageDealt'] / self.season_stats[game_mode]['roundsPlayed'])

	def round_most_kills(self, game_mode):
		return self.season_stats[game_mode]['roundMostKills']

	def rank_points(self, game_mode):
		return int(self.season_stats[game_mode]['rankPoints'])


def sneak_player(pubg_player):
	
	p = pubgPlayer(pubg_player, pubg_season, pubg_api_key)
	
	if p.player_name_to_accountid() and p.get_season_stats():
		for game_mode in p.game_modes():
			
			if p.has_games_played_in_game_mode(game_mode):
				r_game_mode = p.format_game_mode(game_mode)

				rank = p.rank_points(game_mode)
				games = p.rounds_played(game_mode)
				kd = p.kill_death_ratio(game_mode)
				avgdmg = p.average_damage(game_mode)
				headshot = f'{p.head_shot_ratio(game_mode)}%'
				mostkills = p.round_most_kills(game_mode)
				win = f'{p.win_ratio(game_mode)}%'
				
				if p.has_games_played_in_season():
					print(f'\t[{rank} {r_game_mode}] with {kd} KD @ {avgdmg} DMG in {games} games. {headshot} HS / {win} WIN / Most Kills: {mostkills}')

def main():
	processed_files = [f for f in os.listdir(pubg_screenshots) if os.path.isfile(os.path.join(pubg_screenshots, f))]

	while True:
		screenshots = [f for f in os.listdir(pubg_screenshots) if os.path.isfile(os.path.join(pubg_screenshots, f))]
		
		for file in screenshots:

			if file in processed_files:
				continue

			image = cv2.imread(os.path.join(pubg_screenshots, file))
			image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

			# 1920x1080
			playerbox_pos = [[913, 49, 18, 115], [951, 49, 18, 115], [988, 49, 18, 115], [1025, 49, 18, 115]]

			players = []
			
			for playerbox in playerbox_pos:
				y, x, h, w = playerbox
				image_playerbox = image_gray[y:y+h, x:x+w]
				image_playerbox_resized = cv2.resize(image_playerbox, None, fx=7, fy=5, interpolation=cv2.INTER_CUBIC)

				playerbox_string = pytesseract.image_to_string(image_playerbox_resized, config='--psm 6 --oem 3')

				for player in playerbox_string.split():
					if re.match('^[a-zA-Z0-9_]{4,25}$', player) is not None:
						players.append(player)

			if click.confirm(f'Sneak {file} - Team size: {len(players)} - {players}?', default=True):
				for player in players:
					if player not in ignored_players:
						print(f'\n>> {player}')
						sneak_player(player)
						time.sleep(1)
			
			processed_files.append(file)
			print('\n--- END OF SNEAK ---\n')

		time.sleep(5)


if __name__ == '__main__':
	cf = configparser.ConfigParser()
	cf.read('config.ini')

	pytesseract.pytesseract.tesseract_cmd = cf.get('paths', 'tesseractbin')
	pubg_screenshots = cf.get('paths', 'pubg_screenshots')

	pubg_api_key = cf.get('api', 'pubg_api_key')
	pubg_season = cf.get('api', 'pubg_season')
	
	ignored_players = cf.get('general', 'ignored_players').split()
	
	main()
