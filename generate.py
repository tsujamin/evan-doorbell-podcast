from typing import List
from bs4 import BeautifulSoup, Tag
from podgen import Episode, Media, Podcast
import requests
import pytz
import datetime

BASE_URL = "http://www.evan-doorbell.com/production"
ARCHIVE_ORG_MIRROR = "https://archive.org/download/evan-doorbell"

def get_playlist() -> BeautifulSoup:
    """
    Return a BS4 of the platlist page
    """
    resp = requests.get(f"{BASE_URL}/group1.htm")

    if not resp.ok:
        raise Exception(f"non 200 error code downloading playlist page {resp.status}")

    return BeautifulSoup(resp.text, "html.parser")


def episode_from_tr(row: Tag) -> Episode:
    """Parse out the title and mp3 columns (0, 2) to create an episode"""
    tds = row.find_all("td")

    title = tds[0].text.replace("\t", "").replace("\n", "").strip()
    file_name = tds[2].find("a")['href'] # filename.mp3

    print(f"building episode \"{title}\"")
    try:
        url = f"{ARCHIVE_ORG_MIRROR}/{file_name}"
        media = Media.create_from_server_response(url)
    except:
        print("retrying from evan-doorbell.com")
        url = f"{BASE_URL}/{file_name}"
        media = Media.create_from_server_response(url)

    ep = Episode()
    ep.title = title
    ep.media = media

    return ep

def generate_episodes() -> List[Episode]:
    episodes: List[Episode] = []
    playlist_table = get_playlist().find(id="table21")

    for row in playlist_table.find_all("tr")[1:]:
        episodes.append(episode_from_tr(row))

    # Set episode order
    ep_count = len(episodes)
    publish = datetime.datetime.now(tz=pytz.utc)

    for idx in range(ep_count):
        # episodes[idx].position = idx + 1
        episodes[idx].title = F"#{idx+1}: " + episodes[idx].title
        episodes[idx].publication_date = publish - datetime.timedelta(hours=ep_count - idx)

    return episodes


def generate_podcast() -> Podcast:
    episodes = generate_episodes()

    podcast = Podcast()

    podcast.name = "Evan Doorbell's Phone Tapes (Group 1)"
    podcast.description = 'Evan Doorbell\'s Phone Tapes are a well known "documentary" of how the phone system used to be like in the 1970s. Evan has recorded many hours of "phone tapes" of the old phone network.'
    podcast.website = "http://www.evan-doorbell.com"
    podcast.explicit = False
    podcast.image = "https://github.com/tsujamin/evan-doorbell-podcast/blob/main/logo-3.png?raw=true&dummy=.png"
    podcast.withhold_from_itunes = True
    podcast.complete = True

    for episode in episodes:
        podcast.add_episode(episode)

    podcast.apply_episode_order()
    return podcast

with open("podcast.xml", "w") as f:
    podcast = generate_podcast()

    f.write(podcast.rss_str())

