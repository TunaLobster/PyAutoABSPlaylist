# PyAutoABSPlaylist
A quick script to set up AudioBookShelf playlists in a particular order based on feed order and tiering.

## Instructions/Documentation

1. Install the Python environment.
    - I would suggest using a venv because I am using a branch of the published `audiobookshelf` Python package.
   - If you use the bash wrapper to launch the script, it creates the venv for you.
2. Clone this repo.
3. Optional: Create a symlink of `/path/to/this/repo/pyautoabsplaylist.sh` somewhere in your `$PATH` (e.g., `~/bin/`).
4. Copy the `config.yaml.example` file to `config.yaml` and edit it:
   - Enter your Audiobookshelf server info.
   - Enter the librar(y/ies) and playlist(s).
      - Episodes that have not been started are always included.
      - There are config options for in progress and finished episodes.
   - Enter the feeds/podcasts to be included in the playlist(s).
      - Each item under feeds is expected to have feed_name, tier, sort, and count attributes.
5. Run the script.
   - Execute the bash wrapper script:
      - If it's in your `$PATH`: `pyautabsplaylist.sh`
      - If not: `/path/to/this/repo/pyautoabsplaylist.sh`
      or
   - Execeute the Python script: `python main.py`
6. Optional: Set up something (e.g., systemd unit, crontab) to run the script on a schedule.

## Usage

```
pyautoabsplaylist.sh [--config <path/to/config.yaml>] [--venv <name>] [--log] [--close-venv]
```

## Options

`--config <path>`    Path to a config file. If omitted, defaults to `config.yaml` in the current directory.
`--venv <name>`      Name for the virtual environment. If omitted, defaults to "myvenv".
`--log`              Show and follow the log file at ~/.local/share/pyautoabsplaylist/logs/playlist_auto.log
`--close-venv`       Manually deactivate the virtual environment.
`--help`             Show this help message and exit.

## Behavior

- Create and activate a Python virtual environment in (`~/mytools/<venv name>`).
- Install/update dependencies from `/path/to/this/repo/PyAutoABSPlaylist/requirements.txt`.
- Run a python script to create/update playlist(s) in Audiobookshelf based on configurations in `config.yaml`.
- Deactivate the Python virtual environment.

## TODO
- [x] Add argparse and pass a config file in
- [x] Implement sorting functions so that sort_order will work
- [ ] Raise a better error if the config file has a podcast that was not found in the library
