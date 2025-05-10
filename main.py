import argparse
import asyncio
import os
import random
import sys
from collections import defaultdict
from datetime import datetime
from itertools import cycle, islice

import yaml
from audiobookshelf import ABSClient  # Client for interacting with the Audiobookshelf server
from tree_tools import dict_extract  # A helper to recursively extract keys from nested dicts

# Use CLoader if available for faster YAML parsing
try:
    from yaml import CLoader as yaml_loader
except ImportError:
    from yaml import Loader as yaml_loader

# Path to the script directory
script_dir = os.path.dirname(__file__)

# Round-robin helper generator
def roundrobin(*iterables):
    """Visit input iterables in a cycle until each is exhausted."""
    pending = len(iterables)
    nexts = cycle(iter(it).__next__ for it in iterables)
    while pending:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            pending -= 1
            nexts = cycle(islice(nexts, pending))

# Helper functions to extract specific configuration elements
def get_config_library_playlists(config, library_name):
    for x in config["libraries"]:
        if x["library_name"] == library_name:
            return [y["playlist_name"] for y in x["playlists"]]
    return []


def get_config_library_playlist_config(config, library_name, playlist_name):
    for x in config["libraries"]:
        if x["library_name"] == library_name:
            for y in x["playlists"]:
                if y["playlist_name"] == playlist_name:
                    return y


def get_config_library_playlist_podcasts(config, library_name, playlist_name):
    for x in config["libraries"]:
        if x["library_name"] == library_name:
            for y in x["playlists"]:
                if y["playlist_name"] == playlist_name:
                    return [z["feed_name"] for z in y["feeds"]]
    return []


def get_feed_config(config, library_name, playlist_name, podcast_title):
    for x in config["libraries"]:
        if x["library_name"] == library_name:
            for y in x["playlists"]:
                if y["playlist_name"] == playlist_name:
                    for z in y["feeds"]:
                        if z["feed_name"] == podcast_title:
                            return z


# Determine if an episode should be included in the playlist based on user progress
async def should_include_item(abs_client, playlist_config, library_item_id, episode_id):
    item_info = await abs_client.get_library_item(
        library_item_id, expanded=True, include=["progress"], episode=episode_id
    )
    if playlist_config["include_in_progress"] and item_info["userMediaProgress"] is None:
        return True
    if item_info["userMediaProgress"]["isFinished"]:
        if playlist_config["include_finished"]:
            return True
    if (
        playlist_config["include_in_progress"]
        and 0.0 < item_info["userMediaProgress"]["progress"] < 1.0
        and not item_info["userMediaProgress"]["isFinished"]
    ):
        return True


# Normalize playlist or podcast names for comparison
def normalize_name(name):
    return name.strip().lower()


# Main async function to manage playlist creation/updating
async def auto_playlists(config):
    # Initialize Audiobookshelf client
    ABS_URL = config["server"]["address"]
    ABS_USER = config["server"]["user"]
    ABS_PASSWORD = config["server"]["password"]

    abs_client = ABSClient(ABS_URL)
    await abs_client.authorize(ABS_USER, ABS_PASSWORD)

    # Get libraries and user playlists from server
    libs = await abs_client.get_libraries()
    abs_user_playlists_raw = await abs_client.get_user_playlists()
    abs_user_playlists_by_name = {
        normalize_name(p["name"]): p for p in abs_user_playlists_raw
    }

    # Get all feed names and library names from config
    config_podcasts = list(dict_extract("feed_name", config))
    config_libraries = list(dict_extract("library_name", config))

    # Loop through each library on the server
    for lib in libs:
        if lib["name"] not in config_libraries:
            print("Library", lib["name"], "is not in the config...skipping")
            continue

        # Get all items in the library
        lib_items = await abs_client.get_library_items(lib["id"], limit=0)
        library_podcasts = []
        for library_item in lib_items["results"]:
            library_item_title = library_item["media"]["metadata"]["title"]
            if library_item_title in config_podcasts:
                library_podcasts.append((library_item_title, library_item["id"]))

        if len(library_podcasts) == 0:
            print("No matching podcasts between config and library items")
            continue

        # Collect episodes for each podcast
        podcast_episode_lists = []
        for podcast_title, library_item_id in library_podcasts:
            podcast_episodes = await abs_client.get_library_item(library_item_id)
            podcast_episode_lists.append((podcast_title, library_item_id, podcast_episodes["media"]["episodes"]))

        library_playlists = []

        # Process each configured playlist
        for playlist_name in get_config_library_playlists(config, lib["name"]):
            tiers = defaultdict(list)

            # Organize episodes per feed config
            for podcast_title, library_item_id, podcast_episodes in podcast_episode_lists:
                if podcast_title not in get_config_library_playlist_podcasts(config, lib["name"], playlist_name):
                    continue
                feed_config = get_feed_config(config, lib["name"], playlist_name, podcast_title)
                if feed_config is None:
                    print("Error finding feed config", lib["name"], playlist_name, podcast_title)
                    continue
                sort_style = feed_config["sort"]
                prepared_podcast_episode_list = podcast_episodes

                # Sort episodes per feed sort order
                if sort_style == "oldest":
                    prepared_podcast_episode_list = sorted(podcast_episodes, key=lambda x: x["publishedAt"])
                elif sort_style == "newest":
                    prepared_podcast_episode_list = sorted(
                        podcast_episodes, key=lambda x: x["publishedAt"], reverse=True
                    )

                # Filter episodes based on progress
                playlist_config = get_config_library_playlist_config(config, lib["name"], playlist_name)
                temp = []
                for item in prepared_podcast_episode_list:
                    r = await should_include_item(abs_client, playlist_config, item["libraryItemId"], item["id"])
                    if r and item not in temp:
                        temp.append(item)
                if len(temp) == 0:
                    continue
                prepared_podcast_episode_list = temp

                # Truncate episode list to count limit
                if feed_config["count"] != 0:
                    podcast_episode_slice = feed_config["count"]
                    if len(prepared_podcast_episode_list) < feed_config["count"]:
                        podcast_episode_slice = len(prepared_podcast_episode_list)
                    prepared_podcast_episode_list = prepared_podcast_episode_list[:podcast_episode_slice]

                # Save episodes to their tier
                playlist_episode_list = [
                    (episode["libraryItemId"], episode["id"])
                    for episode in prepared_podcast_episode_list
                ]
                tiers[feed_config["tier"]].append(playlist_episode_list)

            # Determine episode sort order strategy for the final playlist
            playlist_config = get_config_library_playlist_config(config, lib["name"], playlist_name)
            sort_order = playlist_config.get("sort_order") or []
            valid_sort_keys = {"tier", "roundrobin", "shuffle"}
            if not any(key in sort_order for key in valid_sort_keys):
                sort_order = ["shuffle"]
            ordered = []

            if sort_order == ["shuffle"] or (set(sort_order) == {"shuffle"}):
                flat = [ep for tier in tiers.values() for sublist in tier for ep in sublist]
                random.shuffle(flat)
                ordered.extend(flat)
            elif "tier" in sort_order:
                tier_keys = sorted(tiers.keys())
                for t in tier_keys:
                    podcasts_in_tier = [sublist for sublist in tiers[t] if sublist]
                    if "shuffle" in sort_order and "roundrobin" not in sort_order:
                        flat = [ep for podcast in podcasts_in_tier for ep in podcast]
                        random.shuffle(flat)
                        ordered.extend(flat)
                    elif "roundrobin" in sort_order:
                        if "shuffle" in sort_order:
                            for podcast in podcasts_in_tier:
                                random.shuffle(podcast)
                        ordered.extend(roundrobin(*podcasts_in_tier))
                    else:
                        for podcast in podcasts_in_tier:
                            ordered.extend(podcast)
            elif "roundrobin" in sort_order:
                flat_lists = [sublist for tier in tiers.values() for sublist in tier if sublist]
                if "shuffle" in sort_order:
                    for sublist in flat_lists:
                        random.shuffle(sublist)
                ordered.extend(roundrobin(*flat_lists))
            else:
                for tier in tiers.values():
                    for sublist in tier:
                        ordered.extend(sublist)

            # Create ABSClient.PlaylistItem objects for submission
            ordered_playlist_items = [ABSClient.PlaylistItem(lid, eid) for lid, eid in ordered]
            library_playlists.append((lib["id"], playlist_name, ordered_playlist_items))

        # Apply playlist updates to Audiobookshelf
        for playlist in library_playlists:
            normalized_name = normalize_name(playlist[1])
            if normalized_name in abs_user_playlists_by_name:
                print("modifying existing playlist", playlist[1])
                existing_playlist = abs_user_playlists_by_name[normalized_name]
                existing_playlist_transform = [
                    (item["episode"]["libraryItemId"], item["episodeId"])
                    for item in existing_playlist["items"]
                ]
                new_playlist_set = set(playlist[2])
                existing_playlist_set = set(ABSClient.PlaylistItem(lid, eid) for lid, eid in existing_playlist_transform)

                # Determine changes
                items_to_add = list(new_playlist_set - existing_playlist_set)
                if items_to_add:
                    await abs_client.playlist_batch_add(existing_playlist["id"], items=items_to_add)
                items_to_remove = list(existing_playlist_set - new_playlist_set)
                if items_to_remove:
                    await abs_client.playlist_batch_remove(existing_playlist["id"], items=items_to_remove)

                # Update metadata and items
                await abs_client.update_playlist(
                    existing_playlist["id"],
                    playlist[1],
                    description=f"Last update: {datetime.now():%c}",
                    items=playlist[2],
                )
            else:
                print("creating new playlist", playlist[1])
                await abs_client.create_playlist(playlist[0], playlist[1], items=playlist[2])


# Entry point for script
def main():
    parser = argparse.ArgumentParser(description="Audiobookshelf auto-playlist script.")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to YAML config file",
        default="config.yaml"
    )
    args = parser.parse_args()

    config_path = args.config
    if not os.path.isfile(config_path):
        print(f"Error: config file not found at: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.load(f, Loader=yaml_loader)

    asyncio.run(auto_playlists(config))


if __name__ == "__main__":
    main()
