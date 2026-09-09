import json

CHALLENGE_API_PATH_PREFIXES = ("/challenge/", "/api/challenge/", "/api/v1/challenge/")


def challenge_path_segments(api_path: str) -> list:
    """Return the path segments that follow ``/challenge/`` in a challenge api_path.

    ``/challenge/12345/AbCdEf/`` -> ``["12345", "AbCdEf"]``; ``/challenge/`` -> ``[]``.
    Query strings are ignored. Paths that do not point at a challenge return ``[]``.
    """
    path = str(api_path or "").split("?", 1)[0]
    for prefix in CHALLENGE_API_PATH_PREFIXES:
        if path.startswith(prefix):
            return [segment for segment in path[len(prefix) :].split("/") if segment]
    return []


def is_opaque_native_challenge(challenge, api_path: str = "") -> bool:
    """Return whether a ``challenge_required`` payload is an opaque native checkpoint.

    Instagram sets ``challenge.native_flow=true`` on virtually every mobile API
    checkpoint, including the ordinary ``/challenge/{user_id}/{nonce}/`` flows that
    expose ``select_verify_method`` / ``verify_email`` steps and can be resolved with
    ``challenge_code_handler``. Only checkpoints whose path segments are encrypted
    tokens (non-numeric user id) and whose ``challenge_context`` is not JSON are
    opaque; those cannot be driven by the legacy resolver and need manual approval.
    """
    if not isinstance(challenge, dict) or not challenge.get("native_flow"):
        return False
    api_path = str(api_path or challenge.get("api_path") or "")
    if not api_path.startswith(CHALLENGE_API_PATH_PREFIXES):
        return False
    segments = challenge_path_segments(api_path)
    if segments and segments[0].isdigit():
        # Legacy numeric user_id/nonce path: resolvable through the step_name flow.
        return False
    context = challenge.get("challenge_context")
    if isinstance(context, str) and context.strip():
        try:
            json.loads(context)
        except ValueError:
            return True  # encrypted/opaque context
        return False  # JSON context carries step_name and is resolvable
    # No context: encrypted path segments are opaque, a bare /challenge/ is not
    # known to be opaque until it is requested.
    return bool(segments)


class ClientError(Exception):
    response = None
    code = None
    message = ""

    def __init__(self, *args, **kwargs):
        args = list(args)
        if len(args) > 0:
            self.message = str(args.pop(0))
        for key in list(kwargs.keys()):
            setattr(self, key, kwargs.pop(key))
        if not self.message:
            self.message = "{title} ({body})".format(
                title=getattr(self, "reason", "Unknown"),
                body=getattr(self, "error_type", vars(self)),
            )
        super().__init__(self.message, *args, **kwargs)
        if self.response:
            self.code = self.response.status_code


class ClientUnknownError(ClientError):
    pass


class WrongCursorError(ClientError):
    message = "You specified a non-existent cursor"


class ClientStatusFail(ClientError):
    pass


class ClientErrorWithTitle(ClientError):
    pass


class ResetPasswordError(ClientError):
    pass


class GenericRequestError(ClientError):
    """Sorry, there was a problem with your request"""


class ClientGraphqlError(ClientError):
    """Raised due to graphql issues"""


class ClientJSONDecodeError(ClientError):
    """Raised due to json decoding issues"""


class ClientConnectionError(ClientError):
    """Raised due to network connectivity-related issues"""


class ClientBadRequestError(ClientError):
    """Raised due to a HTTP 400 response"""


class ClientUnauthorizedError(ClientError):
    """Raised due to a HTTP 401 response"""


class ClientForbiddenError(ClientError):
    """Raised due to a HTTP 403 response"""


class ClientNotFoundError(ClientError):
    """Raised due to a HTTP 404 response"""


class ClientThrottledError(ClientError):
    """Raised due to a HTTP 429 response"""


class ClientRequestTimeout(ClientError):
    """Raised due to a HTTP 408 response"""


class ClientIncompleteReadError(ClientError):
    """Raised due to incomplete read HTTP response"""


class ClientLoginRequired(ClientError):
    """Instagram redirect to https://www.instagram.com/accounts/login/"""


class ReloginAttemptExceeded(ClientError):
    pass


class PrivateError(ClientError):
    """For Private API and last_json logic"""


class NotFoundError(PrivateError):
    reason = "Not found"


class FeedbackRequired(PrivateError):
    pass


class SignupSpamError(FeedbackRequired):
    """Raised when Instagram rejects the legacy signup flow as spam."""


class ChallengeError(PrivateError):
    pass


class ChallengeRedirection(ChallengeError):
    pass


class ChallengeRequired(ChallengeError):
    BLOKS_REDIRECT_ACTION = "com.bloks.www.ig.challenge.redirect.async"

    def __init__(self, *args, **kwargs):
        raw_message = kwargs.get("message")
        if args and raw_message == "challenge_required":
            kwargs["raw_message"] = raw_message
            kwargs.pop("message")
        elif raw_message == "challenge_required":
            kwargs["raw_message"] = raw_message
            kwargs["message"] = self._message_for_payload(kwargs)
        super().__init__(*args, **kwargs)

    @classmethod
    def _challenge_api_path(cls, data):
        challenge = data.get("challenge")
        if isinstance(challenge, dict):
            return str(challenge.get("api_path") or "")
        return str(data.get("api_path") or "")

    @classmethod
    def _message_for_payload(cls, data):
        api_path = cls._challenge_api_path(data)
        step_name = data.get("step_name")
        bloks_action = data.get("bloks_action")
        challenge = data.get("challenge")

        if api_path.startswith("/auth_platform/") or api_path.startswith("auth_platform/"):
            return (
                "Manual verification required via Instagram auth platform flow. "
                "This challenge is not supported automatically; open the official Instagram app or web flow "
                "on a trusted device, complete the checkpoint, then retry with the same saved client settings, "
                "device identifiers, and proxy/IP."
            )
        if bloks_action == cls.BLOKS_REDIRECT_ACTION or step_name == "STEP_NAME":
            return (
                "Manual verification required via Instagram Bloks redirect checkpoint. "
                "Confirm the login in the official Instagram app or web flow on a trusted device. "
                "If you keep the same client instance alive, call challenge_bloks_redirect_dismiss() after approval; "
                "otherwise retry with the same saved client settings, device identifiers, and proxy/IP."
            )
        if is_opaque_native_challenge(challenge, api_path):
            return (
                "Manual verification required via Instagram native challenge flow. "
                "This checkpoint is not handled by challenge_code_handler or change_password_handler; "
                "complete it in the official Instagram app or web flow on a trusted device. "
                "Retry with the same saved client settings, device identifiers, and proxy/IP."
            )
        if api_path.startswith(CHALLENGE_API_PATH_PREFIXES):
            return (
                "Instagram returned a legacy challenge flow. Configure challenge_code_handler or "
                "change_password_handler for supported email/SMS/password steps, or complete the checkpoint manually. "
                "Retry with the same saved client settings, device identifiers, and proxy/IP."
            )
        if step_name:
            return (
                f"Instagram requires additional verification at challenge step `{step_name}`. "
                "Configure challenge_code_handler or change_password_handler if this is a supported "
                "code/password step, or complete the checkpoint manually in the official Instagram app or web flow. "
                "Retry with the same saved client settings, device identifiers, and proxy/IP."
            )
        return (
            "Instagram requires additional verification for this account/session. "
            "Open the official Instagram app or web flow on a trusted device, complete the checkpoint there, "
            "then retry with the same saved client settings, device identifiers, and proxy/IP. "
            "Automatic challenge resolution is only available for supported code/password-reset flows; "
            "Bloks redirect checkpoints usually require manual approval."
        )


class AccountSuspended(ClientError):
    pass


class ChallengeSelfieCaptcha(ChallengeError):
    pass


class ChallengeUnknownStep(ChallengeError):
    pass


class SelectContactPointRecoveryForm(ChallengeError):
    pass


class RecaptchaChallengeForm(ChallengeError):
    pass


class SubmitPhoneNumberForm(ChallengeError):
    pass


class LegacyForceSetNewPasswordForm(ChallengeError):
    pass


class LoginRequired(PrivateError):
    """Instagram request relogin
    Example:
    {'message': 'login_required',
    'response': <Response [403]>,
    'error_title': "You've Been Logged Out",
    'error_body': 'Please log back in.',
    'logout_reason': 8,
    'status': 'fail'}
    """


class SentryBlock(PrivateError):
    pass


class RateLimitError(PrivateError):
    pass


class ProxyAddressIsBlocked(PrivateError):
    """Instagram has blocked your IP address, use a quality proxy provider (not free, not shared)"""


class BadPassword(PrivateError):
    pass


class BadCredentials(PrivateError):
    pass


class PleaseWaitFewMinutes(PrivateError):
    pass


class UnknownError(PrivateError):
    pass


class AccountEditError(PrivateError):
    pass


class AccountContactPointRequired(AccountEditError):
    pass


class TrackNotFound(NotFoundError):
    pass


class MediaError(PrivateError):
    pass


class MediaNotFound(NotFoundError, MediaError):
    pass


class StoryNotFound(NotFoundError, MediaError):
    pass


class UserError(PrivateError):
    pass


class UserNotFound(NotFoundError, UserError):
    pass


class CollectionError(PrivateError):
    pass


class CollectionNotFound(NotFoundError, CollectionError):
    pass


class DirectError(PrivateError):
    pass


class DirectThreadNotFound(NotFoundError, DirectError):
    pass


class DirectMessageNotFound(NotFoundError, DirectError):
    pass


class DirectMessageRequestsDisabled(DirectError):
    """Raised when recipient privacy settings reject a new Direct message request."""


class VideoTooLongException(PrivateError):
    pass


class VideoNotDownload(PrivateError):
    pass


class VideoNotUpload(PrivateError):
    pass


class VideoConfigureError(VideoNotUpload):
    pass


class VideoConfigureStoryError(VideoConfigureError):
    pass


class PhotoNotUpload(PrivateError):
    pass


class PhotoConfigureError(PhotoNotUpload):
    pass


class PhotoConfigureStoryError(PhotoConfigureError):
    pass


class IGTVNotUpload(PrivateError):
    pass


class IGTVConfigureError(IGTVNotUpload):
    pass


class ClipNotUpload(PrivateError):
    pass


class ClipConfigureError(ClipNotUpload):
    pass


class AlbumNotDownload(PrivateError):
    pass


class AlbumUnknownFormat(PrivateError):
    pass


class AlbumConfigureError(PrivateError):
    pass


class HashtagError(PrivateError):
    pass


class HashtagNotFound(NotFoundError, HashtagError):
    pass


class LocationError(PrivateError):
    pass


class LocationNotFound(NotFoundError, LocationError):
    pass


class TwoFactorRequired(PrivateError):
    pass


class HighlightNotFound(NotFoundError, PrivateError):
    pass


class NoteNotFound(NotFoundError):
    reason = "Not found"


class PrivateAccount(PrivateError):
    """This Account is Private"""


class InvalidTargetUser(PrivateError):
    """Invalid target user"""


class InvalidMediaId(PrivateError):
    """Invalid media_id"""


class MediaUnavailable(PrivateError):
    """Media is unavailable"""


class CommentUnavailable(PrivateError):
    """Comment is unavailable"""


class CommentNotFound(PrivateError):
    message = "Comment not found"


class CommentsDisabled(PrivateError):
    message = "Comments disabled by author"


class ValidationError(AssertionError):
    pass


class EmailInvalidError(ClientError):
    pass


class EmailNotAvailableError(ClientError):
    pass


class EmailVerificationSendError(ClientError):
    pass


class AgeEligibilityError(ClientError):
    pass


class CaptchaChallengeRequired(ClientError):
    """Captcha challenge required, and no solver is configured or available."""

    def __init__(
        self,
        message="Captcha challenge required, but no solver configured or available.",
        challenge_details=None,
        **kwargs,
    ):
        self.challenge_details = challenge_details if challenge_details else {}
        # Example of extracting common details:
        # self.site_key = self.challenge_details.get('site_key')
        # self.challenge_url = self.challenge_details.get('challenge_url') # URL where captcha is presented
        super().__init__(message, **kwargs)


class RelatedProfileRequired(ClientError):
    """Raised by user_related_profiles_gql when IG returns no related
    profiles. Used as a retry signal — the method raises it only if
    the caller has opted in by setting ``client.num_retry`` below 4;
    otherwise it returns an empty list."""

    pass
