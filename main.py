import asyncio
import os
from collections import defaultdict
from datetime import datetime
from itertools import cycle, islice

import yaml
from audiobookshelf import ABSClient

from tree_tools import dict_extract

try:
    from yaml import CLoader as yaml_loader
except ImportError:
    from yaml import Loader as yaml_loader

script_dir = os.path.dirname(__file__)


def roundrobin(*iterables):
    "Visit input iterables in a cycle until each is exhausted."
    # roundrobin('ABC', 'D', 'EF') → A D E B F C
    # Algorithm credited to George Sakkis
    iterators = map(iter, iterables)
    for num_active in range(len(iterables), 0, -1):
        iterators = cycle(islice(iterators, num_active))
        yield from map(next, iterators)


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
    # Returns the full structure down of the feed config options
    for x in config["libraries"]:
        if x["library_name"] == library_name:
            for y in x["playlists"]:
                if y["playlist_name"] == playlist_name:
                    for z in y["feeds"]:
                        if z["feed_name"] == podcast_title:
                            return z


# TODO: Add a cache here to maybe reduce server pings
async def should_include_item(abs_client, playlist_config, library_item_id, episode_id):
    # print("moo", library_item_id, episode_id)
    item_info = await abs_client.get_library_item(
        library_item_id, expanded=True, include=["progress"], episode=episode_id
    )
    # print()
    # print(item_info)
    # print()
    # TODO: Add filter for only considering episodes downloaded to the server
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


async def auto_playlists():
    # get the yaml config that the user would like to set up the playlists with
    config = yaml.load(open(os.path.join(script_dir, "config.yaml")), Loader=yaml_loader)

    ABS_URL = config["server"]["address"]
    ABS_USER = config["server"]["user"]
    ABS_PASSWORD = config["server"]["password"]

    # open connection to the abs server
    abs_client = ABSClient(ABS_URL)
    await abs_client.authorize(ABS_USER, ABS_PASSWORD)

    # TODO: Add check if the user is currently playing something, don't modify the playlist as it disrupts continuous playing of the playlist
    r = await abs_client.get_sessions_page(abs_client.user["id"])

    libs = await abs_client.get_libraries()
    abs_user_playlists = await abs_client.get_user_playlists()
    abs_user_playlists_names = tuple(p["name"] for p in abs_user_playlists)

    # get a list of all of the podcasts in the config file
    config_podcasts = list(dict_extract("feed_name", config))
    config_libraries = list(dict_extract("library_name", config))

    for lib in libs:
        # check if the current lib is specified in the config
        if lib["name"] not in config_libraries:
            # this library is not in the config
            print("Library", lib["name"], "is not in the config...skipping")
            continue

        # get the podcasts the user has available on the server
        # TODO: Paginate and concat the results together
        lib_items = await abs_client.get_library_items(lib["id"], limit=0)
        library_podcasts = []
        for library_item in lib_items["results"]:
            # check the title of the library_item and also get the id of the item
            library_item_title = library_item["media"]["metadata"]["title"]
            if library_item_title in config_podcasts:
                library_podcasts.append((library_item_title, library_item["id"]))

        if len(library_podcasts) == 0:
            # no matching podcasts between config and library
            print("No matching podcasts between config and library items")
            continue

        podcast_episode_lists = []
        for podcast_title, library_item_id in library_podcasts:
            # grab the list of episodes per podcast of interest
            podcast_episodes = await abs_client.get_library_item(library_item_id)
            # TODO: Turn this tuple thing into a dataclass object
            podcast_episode_lists.append((podcast_title, library_item_id, podcast_episodes["media"]["episodes"]))

        # create list of playlists to create/update in the library
        library_playlists = []
        for playlist_name in get_config_library_playlists(config, lib["name"]):
            tiers = defaultdict(list)
            # sort each podcast episode list as requested in config
            for (
                podcast_title,
                library_item_id,
                podcast_episodes,
            ) in podcast_episode_lists:
                if podcast_title not in get_config_library_playlist_podcasts(config, lib["name"], playlist_name):
                    continue
                # sort each podcast feed as requested
                feed_config = get_feed_config(config, lib["name"], playlist_name, podcast_title)
                if feed_config is None:
                    print(
                        "something went wrong when trying to find a feed config",
                        lib["name"],
                        playlist_name,
                        podcast_title,
                    )
                    continue
                sort_style = feed_config["sort"]
                prepared_podcast_episode_list = podcast_episodes
                if sort_style == "oldest":
                    prepared_podcast_episode_list = sorted(podcast_episodes, key=lambda x: x["publishedAt"])
                elif sort_style == "newest":
                    prepared_podcast_episode_list = sorted(
                        podcast_episodes, key=lambda x: x["publishedAt"], reverse=True
                    )
                else:
                    pass

                # filter episode list with should_include_item
                playlist_config = get_config_library_playlist_config(config, lib["name"], playlist_name)
                temp = []
                for item in prepared_podcast_episode_list:
                    r = await should_include_item(abs_client, playlist_config, item["libraryItemId"], item["id"])
                    if r and item not in temp:
                        temp.append(item)
                prepared_podcast_episode_list = temp

                # limit the number of episodes if requested
                if feed_config["count"] != 0:
                    podcast_episode_slice = feed_config["count"]
                    if len(prepared_podcast_episode_list) < feed_config["count"]:
                        podcast_episode_slice = len(prepared_podcast_episode_list)
                    prepared_podcast_episode_list = prepared_podcast_episode_list[:podcast_episode_slice]

                # filter to just the information that the playlist api endpoints need
                playlist_episode_list = [
                    ABSClient.PlaylistItem(episode["libraryItemId"], episode["id"])
                    for episode in prepared_podcast_episode_list
                ]
                tiers[feed_config["tier"]].append(playlist_episode_list)

            ordered = []
            # Round robin build up each tier from individual feeds
            for tier in sorted(tiers.keys()):
                ordered.extend(roundrobin(*tiers[tier]))

            # add the playlist to the stack to be pushed to the server
            library_playlists.append((lib["id"], playlist_name, ordered))

        for playlist in library_playlists:
            if playlist[1] in abs_user_playlists_names:
                print("modifying existing playlist", playlist[1])
                existing_playlist = abs_user_playlists[abs_user_playlists_names.index(playlist[1])]
                playlist_config = get_config_library_playlist_config(config, lib["name"], playlist[1])
                existing_playlist_transform = []
                # change the existing items into objects that can be use with the playlist api endpoints
                for item in existing_playlist["items"]:
                    existing_playlist_transform.append(
                        ABSClient.PlaylistItem(item["episode"]["libraryItemId"], item["episodeId"])
                    )

                # Add items not in existing playlist
                items_to_add = list(set(playlist[2]) - set(existing_playlist_transform))
                if len(items_to_add) > 0:
                    await abs_client.playlist_batch_add(existing_playlist["id"], items=items_to_add)
                # Remove items not in updated playlist
                items_to_remove = list(set(existing_playlist_transform) - set(playlist[2]))
                if len(items_to_remove) > 0:
                    await abs_client.playlist_batch_remove(existing_playlist["id"], items=items_to_remove)

                # Update the order of the playlist
                await abs_client.update_playlist(
                    existing_playlist["id"],
                    playlist[1],
                    description=f"Last update: {datetime.now():%c}",
                    items=playlist[2],
                )
            else:
                # playlist does not exist so it will need to be created anew
                print("creating new playlist", playlist[1])
                await abs_client.create_playlist(playlist[0], playlist[1], items=playlist[2])


def main():
    asyncio.run(auto_playlists())


if __name__ == "__main__":
    main()
