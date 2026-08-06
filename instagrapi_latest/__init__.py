import logging
from copy import deepcopy
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from instagrapi_latest.mixins.account import AccountMixin
from instagrapi_latest.mixins.album import DownloadAlbumMixin, UploadAlbumMixin
from instagrapi_latest.mixins.auth import LoginMixin
from instagrapi_latest.mixins.bloks import BloksMixin
from instagrapi_latest.mixins.challenge import ChallengeResolveMixin
from instagrapi_latest.mixins.clip import ClipMixin, DownloadClipMixin, UploadClipMixin
from instagrapi_latest.mixins.collection import CollectionMixin
from instagrapi_latest.mixins.comment import CommentMixin
from instagrapi_latest.mixins.crossposting import CrossPostingMixin
from instagrapi_latest.mixins.direct import DirectMixin
from instagrapi_latest.mixins.explore import ExploreMixin
from instagrapi_latest.mixins.fbsearch import FbSearchMixin
from instagrapi_latest.mixins.fundraiser import FundraiserMixin
from instagrapi_latest.mixins.graphql import PrivateGraphQLRequestMixin
from instagrapi_latest.mixins.hashtag import HashtagMixin
from instagrapi_latest.mixins.highlight import HighlightMixin
from instagrapi_latest.mixins.igtv import DownloadIGTVMixin, UploadIGTVMixin
from instagrapi_latest.mixins.insights import InsightsMixin
from instagrapi_latest.mixins.location import LocationMixin
from instagrapi_latest.mixins.media import MediaMixin
from instagrapi_latest.mixins.multiple_accounts import MultipleAccountsMixin
from instagrapi_latest.mixins.note import NoteMixin
from instagrapi_latest.mixins.notification import NotificationMixin
from instagrapi_latest.mixins.password import PasswordMixin
from instagrapi_latest.mixins.photo import DownloadPhotoMixin, UploadPhotoMixin
from instagrapi_latest.mixins.private import PrivateRequestMixin
from instagrapi_latest.mixins.public import (
    ProfilePublicMixin,
    PublicRequestMixin,
    TopSearchesPublicMixin,
)
from instagrapi_latest.mixins.quicksnap import QuickSnapMixin
from instagrapi_latest.mixins.realtime import RealtimeMixin
from instagrapi_latest.mixins.share import ShareMixin
from instagrapi_latest.mixins.signup import SignUpMixin
from instagrapi_latest.mixins.story import StoryMixin
from instagrapi_latest.mixins.timeline import ReelsMixin
from instagrapi_latest.mixins.totp import TOTPMixin
from instagrapi_latest.mixins.track import TrackMixin
from instagrapi_latest.mixins.user import UserMixin
from instagrapi_latest.mixins.video import DownloadVideoMixin, UploadVideoMixin

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Used as fallback logger if another is not provided.
DEFAULT_LOGGER = logging.getLogger("instagrapi")


class Client(
    PublicRequestMixin,
    ChallengeResolveMixin,
    PrivateRequestMixin,
    PrivateGraphQLRequestMixin,
    CrossPostingMixin,
    TopSearchesPublicMixin,
    ProfilePublicMixin,
    LoginMixin,
    ShareMixin,
    TrackMixin,
    FbSearchMixin,
    HighlightMixin,
    DownloadPhotoMixin,
    UploadPhotoMixin,
    DownloadVideoMixin,
    UploadVideoMixin,
    DownloadAlbumMixin,
    NotificationMixin,
    UploadAlbumMixin,
    DownloadIGTVMixin,
    UploadIGTVMixin,
    MediaMixin,
    UserMixin,
    InsightsMixin,
    CollectionMixin,
    AccountMixin,
    DirectMixin,
    LocationMixin,
    HashtagMixin,
    CommentMixin,
    StoryMixin,
    PasswordMixin,
    SignUpMixin,
    ClipMixin,
    DownloadClipMixin,
    UploadClipMixin,
    ReelsMixin,
    ExploreMixin,
    BloksMixin,
    TOTPMixin,
    MultipleAccountsMixin,
    NoteMixin,
    QuickSnapMixin,
    FundraiserMixin,
    RealtimeMixin,
):
    proxy = None

    def __init__(
        self,
        settings: Optional[dict] = None,
        proxy: Optional[str] = None,
        delay_range: Optional[list] = None,
        logger=DEFAULT_LOGGER,
        override_app_version: bool = False,
        **kwargs,
    ):
        self.tls_verify = kwargs.pop("tls_verify", True)
        self.request_timeout = kwargs.pop("request_timeout", 1)
        self.public_request_retries_count = kwargs.pop("public_request_retries_count", 3)
        self.public_request_retries_timeout = kwargs.pop("public_request_retries_timeout", 2)
        self.session_retry_total = kwargs.pop("session_retry_total", 3)
        self.session_retry_backoff_factor = kwargs.pop("session_retry_backoff_factor", 2)
        self.session_retry_statuses = list(kwargs.pop("session_retry_statuses", [429, 500, 502, 503, 504]))
        self.timezone_offset = kwargs.pop("timezone_offset", -14400)
        self.timezone_name = kwargs.pop("timezone_name", "")
        self.push_disabled = kwargs.pop("push_disabled", True)

        super().__init__(**kwargs)

        self.settings = deepcopy(settings or {})
        self.override_app_version = override_app_version
        self.logger = logger
        self.delay_range = delay_range

        self.set_proxy(proxy)

        self.init()

    def set_proxy(self, dsn: Optional[str]):
        if dsn:
            assert isinstance(dsn, str), f'Proxy must been string (URL), but now "{dsn}" ({type(dsn)})'
            self.proxy = dsn
            proxy_href = "{scheme}{href}".format(
                scheme="http://" if not urlparse(self.proxy).scheme else "",
                href=self.proxy,
            )
            proxies = {
                "http": proxy_href,
                "https": proxy_href,
            }
            self.public.proxies = self.private.proxies = proxies
            if hasattr(self, "graphql"):
                self.graphql.proxies = proxies
            return True
        self.public.proxies = self.private.proxies = {}
        if hasattr(self, "graphql"):
            self.graphql.proxies = {}
        return False
