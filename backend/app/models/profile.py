import json
from dataclasses import dataclass, field

from browserforge.fingerprints import Fingerprint, ScreenFingerprint, NavigatorFingerprint, VideoCard


class ExtendedFingerprint(Fingerprint):
    @classmethod
    def from_json(cls, json_str: str) -> "ExtendedFingerprint":
        data = json.loads(json_str)

        screen = ScreenFingerprint(**data.get("screen", {}))
        navigator = NavigatorFingerprint(**data.get("navigator", {}))
        video_card_data = data.get("videoCard")
        video_card = VideoCard(**video_card_data) if video_card_data else None

        return cls(
            screen=screen,
            navigator=navigator,
            headers=data.get("headers", {}),
            videoCodecs=data.get("videoCodecs", {}),
            audioCodecs=data.get("audioCodecs", {}),
            pluginsData=data.get("pluginsData", {}),
            battery=data.get("battery"),
            videoCard=video_card,
            multimediaDevices=data.get("multimediaDevices", []),
            fonts=data.get("fonts", []),
            mockWebRTC=data.get("mockWebRTC"),
            slim=data.get("slim")
        )


@dataclass
class Proxy:
    server: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None

    @staticmethod
    def from_json(json_str: str | None) -> "Proxy | None":
        if not json_str:
            return None
        return Proxy(**json.loads(json_str))

    def to_json(self) -> str:
        return json.dumps(self.__dict__)

@dataclass
class Profile:
    fingerprint: ExtendedFingerprint
    proxy: Proxy | None = None
    page_urls: list[str] = field(default_factory=list)

    @staticmethod
    def from_json(name: str, fingerprint_json: str, proxy_json: str | None, page_urls_json: str) -> "Profile":
        fingerprint = ExtendedFingerprint.from_json(fingerprint_json)
        proxy = Proxy.from_json(proxy_json)
        page_urls = json.loads(page_urls_json)
        return Profile(fingerprint=fingerprint, proxy=proxy, page_urls=page_urls)

    def to_json(self) -> tuple[str, str | None, str]:
        # Use the dumps method if available
        if hasattr(self.fingerprint, 'dumps'):
            fingerprint_json = self.fingerprint.dumps()
        else:
            fingerprint_json = str(self.fingerprint)
        proxy_json = self.proxy.to_json() if self.proxy else None
        page_urls_json = json.dumps(self.page_urls)
        return fingerprint_json, proxy_json, page_urls_json
