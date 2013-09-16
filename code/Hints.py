# Copyright (C) 2012-2013 Itay Brandes

'''The hints module of the project.'''

import random

import utils
tr = utils.qt.tr

### FUNCTIONS ###
def get_hint():
	"hints for the project"
	hints = [
				tr('Did you know? iQuality can downloads clips from Youtube.'),
				tr('Did you know? iQuality supports foreign languages songs.'),	
				tr('Did you know? iQuality can add tracks to iTunes playlists.'),
				tr('Did you know? iQuality searches can show you random tracks.'),
				tr('Did you know? iQuality can append lyrics to songs.'),
				tr('Did you know? iQuality downloads album arts for you.'),
				tr('Did you know? iQuality can download the top charts songs.'),
				tr('Did you know? iQuality can handle Youtube playlists.'),
				tr('Did you know? iQuality can trim silence from the audio edges.'),
				tr('Did you know? You can buy music with iQuality.')
				]
				
	i = random.randint(0, len(hints)-1)
	return hints[i]