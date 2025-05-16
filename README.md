# PyAutoABSPlaylist
A quick script to set up AudioBookShelf playlists in a particular order based on feed order and tiering.

## Instructions/Documentation

1. Install the Python environment.
   - I would suggest using a venv because I am using a branch of the published `audiobookshelf` Python package.
   - If you use the bash wrapper to launch the script, it creates the venv for you.
2. Clone this repo.
3. Switch to the repo directory: `cd /path/to/this/repo`
4. Copy the `config.yaml.example` file to `config.yaml` and edit it:
   - Enter your Audiobookshelf server info.
   - Enter the librar(y/ies) and playlist(s).
      - Episodes that have not been started are always included.
      - There are config options for in progress and finished episodes.
   - Enter the feeds/podcasts to be included in the playlist(s).
      - Each item under feeds is expected to have feed_name, tier, sort, and count attributes.
5. Create a venv: `python -m venv ~/mytools/myvenv`
6. Activate the venv: `~/mytools/myvenv/bin/activate`
7. Install dependencies: `~/mytools/myvenv/bin/pip install --upgrade -r /path/tp/this/repo/requirements.txt"`
8. Execeute the Python script: `python main.py`
9. Remember to deactivate the venv: `deactivate`

**Optional**: Use the Bash wrapper, which handles the venv for you, instead of calling the python script directly.

5. Create a symlink of `/path/to/this/repo/pyautoabsplaylist.sh` somewhere in your `$PATH` (e.g., `~/bin/pyautoabsplaylist.sh`).
6. Execute the bash wrapper script: `pyautabsplaylist.sh`

**Optional**: Set up something (e.g., systemd unit, crontab) to run the script on a schedule, so that listened-to epispodes are removed from and newly downloaded episodes are added to the playlist

## Usage: Python script

```
python main.py [--config </path/to/config]

--config <path>    Path to a config file. If omitted, defaults to `config.yaml` in the current directory.
```

## Usage: Bash wrapper

```
pyautoabsplaylist.sh [--config </path/to/config.yaml>] [--venv <name>] [--log] [--close-venv]

--config <path>    Path to a config file. If omitted, defaults to `config.yaml` in the current directory.
--venv <name>      Name for the virtual environment. If omitted, defaults to "myvenv".
--log              Show and follow the log file at ~/.local/share/pyautoabsplaylist/logs/playlist_auto.log
--close-venv       Manually deactivate the virtual environment.
--help             Show this help message and exit.
```

## Behavior

- Create and activate a Python virtual environment in (`~/mytools/<venv name>`).
- Install/update dependencies from `/path/to/this/repo/PyAutoABSPlaylist/requirements.txt`.
- Run a python script to create/update playlist(s) in Audiobookshelf based on configurations in `config.yaml`.
- Deactivate the Python virtual environment.

## To Do
- [x] Add argparse and pass a config file in
- [x] Implement sorting functions so that sort_order will work
- [ ] Raise a better error if the config file has a podcast that was not found in the library
