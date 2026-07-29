import datetime
import re
import ssl
from pathlib import Path
from time import time

import yaml

from auth import log_in_with_official_client
from download_audio import download_audio_list
from download_friends import download_all_friends
from download_photo import download_all_albums
from download_topics import download_topic_list
from download_wall import download_wall


def actualize_index():
    users = []
    groups = []

    for wall_f in Path("./wall").iterdir():
        m = re.match("wall(-?\\d+).json", str(wall_f.name))
        if m is not None:
            owner_id = int(m.group(1))
            if owner_id > 0:
                obj = {
                    "id": owner_id,
                    "wall": True
                }
                users.append(obj)
                if Path(f"./friends/friends{owner_id}.json").exists():
                    obj["friends"] = True
            else:
                obj = {
                    "id": -owner_id,
                    "wall": True
                }
                groups.append(obj)
            if Path(f"./album/album{owner_id}/albums{owner_id}.json").exists():
                obj["albums"] = True
            if Path(f"./audio/audio{owner_id}/audio{owner_id}.json").exists():
                obj["audios"] = True
            if Path(f"./boards/board{-owner_id}").exists():
                obj["topics"] = True

    yaml.dump({"users": users, "groups": groups}, open("downloaded.yaml", "w"), sort_keys=False, allow_unicode=True)

def compute_diff(index, downloaded):
    downloaded_users = {u["id"]: u for u in downloaded["users"]}
    downloaded_groups = {g["id"]: g for g in downloaded["groups"]}

    def update_diff(diff, profile, downloaded_profiles, key, custom_add_key=None):
        def add_key():
            if custom_add_key is None:
                diff.add(key)
            else:
                custom_add_key()
        if key in profile and profile[key]:
            if profile["id"] not in downloaded_profiles:
                add_key()
            else:
                downloaded_profile = downloaded_profiles[profile["id"]]
                if key not in downloaded_profile or not downloaded_profile[key]:
                    add_key()

    users_diff = {}
    for user in index["users"]:
        diff = set()
        if user["id"] not in downloaded_users:
            diff.add("wall")
        update_diff(diff, user, downloaded_users, "albums")
        update_diff(diff, user, downloaded_users, "audios")
        update_diff(diff, user, downloaded_users, "friends")
        update_diff(diff, user, downloaded_users, "friends_of_friends")
        update_diff(diff, user, downloaded_users, "with_likes", lambda: diff.update(["with_likes", "wall", "albums"]))
        if len(diff) > 0:
            users_diff[user["id"]] = diff

    groups_diff = {}
    for group in index["groups"]:
        diff = set()
        if group["id"] not in downloaded_groups:
            diff.add("wall")
        update_diff(diff, group, downloaded_groups, "albums")
        update_diff(diff, group, downloaded_groups, "audios")
        update_diff(diff, group, downloaded_groups, "topics")
        update_diff(diff, group, downloaded_groups, "with_likes", lambda: diff.update(["with_likes", "wall", "albums", "topics"]))
        if len(diff) > 0:
            groups_diff[group["id"]] = diff

    return tuple([users_diff, groups_diff])

def main():
    directory = Path(".")
    with open(directory / "index.yaml", "r") as f:
        index = yaml.safe_load(f)
    with open(directory / "downloaded.yaml", "r") as f:
        downloaded = yaml.safe_load(f)

    downloaded_user_dict = {u["id"]: u for u in downloaded["users"]}
    downloaded_group_dict = {g["id"]: g for g in downloaded["groups"]}

    user_diff, group_diff = compute_diff(index, downloaded)

    user_dict = {u["id"]: u for u in index["users"]}
    for user_id, diff in user_diff.items():
        print(f"For user {user_id} ({user_dict[user_id]["name"]}): {" ".join(diff)}")

    group_dict = {g["id"]: g for g in index["groups"]}
    for group_id, diff in group_diff.items():
        print(f"For group {group_id} ({group_dict[group_id]["name"]}) need: {" ".join(diff)}")

    if len(user_diff) == 0 and len(group_diff) == 0:
        print("No diff")
        return

    input("Confirm?")

    ssl._create_default_https_context = ssl._create_unverified_context
    session = log_in_with_official_client()

    def update_downloaded_yaml(owner_id, profile_dict, new_key):
        if owner_id > 0:
            profiles = downloaded["users"]
        else:
            profiles = downloaded["groups"]
        owner_id = abs(owner_id)
        if owner_id not in profile_dict:
            profile_dict[owner_id] = {"id": owner_id}
        profile_dict[owner_id][new_key] = True
        profile_dict[owner_id]["updated"] = datetime.datetime.now().isoformat()
        updated = False
        for i in range(0, len(profiles)):
            if profiles[i]["id"] == owner_id:
                profiles[i] = profile_dict[owner_id]
                updated = True
        if not updated:
            profiles.append(profile_dict[owner_id])

        with open(directory / "downloaded.yaml", "w") as f:
            yaml.dump(downloaded, f)

    for user_id, diff in user_diff.items():
        with_likes = "with_likes" in diff
        if "wall" in diff:
            download_wall(directory, user_id, session, with_likes)
            update_downloaded_yaml(user_id, downloaded_user_dict, "wall")
        if "albums" in diff:
            download_all_albums(directory, user_id, session, with_likes)
            update_downloaded_yaml(user_id, downloaded_user_dict, "albums")
        if "audios" in diff:
            download_audio_list(directory, user_id, session)
            update_downloaded_yaml(user_id, downloaded_user_dict, "audios")
        if "friends" in diff or "friends_of_friends" in diff:
            download_all_friends(directory, user_id, session, "friends_of_friends" in diff)
            update_downloaded_yaml(user_id, downloaded_user_dict, "friends")
            if "friends_of_friends" in diff:
                update_downloaded_yaml(user_id, downloaded_user_dict, "friends_of_friends")

    for group_id, diff in group_diff.items():
        with_likes = "with_likes" in diff
        if "wall" in diff:
            download_wall(directory, -group_id, session, with_likes)
            update_downloaded_yaml(-group_id, downloaded_group_dict, "wall")
        if "albums" in diff:
            download_all_albums(directory, -group_id, session, with_likes)
            update_downloaded_yaml(-group_id, downloaded_group_dict, "albums")
        if "audios" in diff:
            download_audio_list(directory, -group_id, session)
            update_downloaded_yaml(-group_id, downloaded_group_dict, "audios")
        if "topics" in diff:
            download_topic_list(directory, group_id, session)
            update_downloaded_yaml(-group_id, downloaded_group_dict, "topics")


if __name__ == '__main__':
    main()
