# PyAutoABSPlaylist
A quick script to set up AudioBookShelf playlists in a particular order based on feed order and tiering.

## A brief run down on what this script is doing.
1. Install the python environment (I would suggest a venv because I am using a branch of the published `audiobookshelf` python package)
2. Put your server info in the YAML config. (the path for the config file is hardcoded for now)
3. Set up the config file for the librar(y/ies) and playlist(s) in the YAML config.
  - Episodes that have not been started are always included. There are config options for in progress and finished episodes.
4. Input the feeds to be a part of the playlist.
  - Each item under feeds is expected to have feed_name, tier, sort, and count attributes.
5. Set up something (e.g. crontab) to run the script at the time interval that you want


## TODO
- [ ] Add argparse and pass a config file in
- [ ] Implement sorting functions so that sort_order will work
- [ ] Raise a better error if the config file has a podcast that was not found in the library
