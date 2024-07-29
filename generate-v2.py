from bs4 import BeautifulSoup, Tag
import requests
import re
from dataclasses import dataclass
from functools import cached_property
from podgen import Episode, Media, Podcast


@dataclass
class TelephoneTape():
    json: dict

    @property
    def mp3_url(self) -> str:
        return self.json["mp3"]

    @cached_property
    def title(self) -> str:
        try:
            description_text = self.json["description"].replace("\n", " ")
        except:
            return self.json["track_title"]

        return re.sub('<[^<]+?>', '', description_text)

    @cached_property
    def podcast_media(self) -> Media:
        try:
            return Media.create_from_server_response(self.mp3_url)
        except Exception as e:
            print(f"Failed to generate Media object for {self.title}: {e}")
            return None


    @cached_property
    def image(self) -> str:
        return self.json["poster"] or None

    @cached_property
    def id(self) -> int:
        return int(self.json["id"])

    @cached_property
    def podcast_episode(self) -> Episode:
        ep = Episode()

        ep.title = self.title
        ep.media = self.podcast_media
        ep.image = self.image
        ep.position = self.id

        return ep

@dataclass
class TelephonePlaylist():
    name: str
    url: str

    @cached_property
    def __json(self) -> dict:
        resp = requests.get(self.url)

        if not resp.ok:
            raise Exception(f"Non 2XX status code {resp.status_code} requesting {url}")

        return dict(resp.json())

    @cached_property
    def tapes(self) -> list[TelephoneTape]:
        return [TelephoneTape(json) for json in self.__json["tracks"]]

    # TODO one day, generate with proper season markers etc (would need to be new library)

@dataclass
class TelephonePodcast():
    name: str
    url: str
    filename: str

    @cached_property
    def __playlist_urls(self) -> dict[str, str]:
        resp = requests.get(self.url)
        if not resp.ok:
            raise Exception(f"Non 2XX status code {resp.status_code} requesting {url}")

        page = BeautifulSoup(resp.text, "html.parser")

        player_tags = page.find_all(lambda tag: tag.has_attr("data-url-playlist"))

        playlists = {}

        for tag in player_tags:
            playlist_url = tag["data-url-playlist"]

            subtitle_tag = tag.find("div", {"class": "srp_subtitle"})
            if subtitle_tag is None:
                raise Exception(f"No playlist title for {playlist_url}")

            if subtitle_tag.text == "New Releases":
                continue

            playlists[subtitle_tag.text] = playlist_url

        return playlists

    @cached_property
    def playlists(self) -> list[TelephonePlaylist]:
        return [TelephonePlaylist(name, url) for name, url in self.__playlist_urls.items()]

    @cached_property
    def podcast_episodes(self) -> list[TelephoneTape]:
        tapes = []
        for playlist in self.playlists:
            tapes += [tape for tape in playlist.tapes]

        return [tape.podcast_episode for tape in sorted(tapes, key=lambda tape: tape.id)]

    @cached_property
    def podcast(self) -> Podcast:
        podcast = Podcast()

        podcast.name = self.name
        podcast.description = 'Evan Doorbell\'s Phone Tapes are a well known "documentary" of how the phone system used to be like in the 1970s. Evan has recorded many hours of "phone tapes" of the old phone network.'
        podcast.website = self.url
        podcast.explicit = False
        podcast.image = "https://github.com/tsujamin/evan-doorbell-podcast/blob/main/logo-3.png?raw=true&dummy=.png"
        podcast.withhold_from_itunes = True

        for episode in self.podcast_episodes:
            podcast.add_episode(episode)

        return podcast


def generate_playlists():
    podcasts: list[TelephonePodcast] = [
        TelephonePodcast("Evan Doorbell's Phone Tapes (Group 1)", "https://evan-doorbell.com/group-1-playlist/", "podcast-group1.xml"),
        TelephonePodcast("Evan Doorbell's Phone Tapes (Production Tapes)", "https://evan-doorbell.com/production-tapes/", "production-tapes.xml")
    ]

    for podcast in podcasts:
        podcast.podcast.rss_file(podcast.filename)

if __name__ == "__main__":
    generate_playlists()

