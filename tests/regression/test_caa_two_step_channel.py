"""The CAA two-step channel detector separates SMS/WhatsApp from email."""

from instagrapi_latest import Client

SMS_PAYLOAD = {"layout": [{"x": '(dkc "sms_challenge" "challenge_continue_button" 1'}]}
WHATSAPP_PAYLOAD = {"layout": [{"x": '(dkc "whatsapp_challenge" 1'}]}
EMAIL_PAYLOAD = {"layout": [{"x": '(dkc "email_challenge" "send_code" 1'}]}
BOTH_PAYLOAD = {"layout": [{"x": '(dkc "sms_challenge" 1 (dkc "email_challenge" 1'}]}


def test_detects_sms_only_payload():
    assert Client().caa_two_step_verification_channel(SMS_PAYLOAD) == "sms"


def test_detects_whatsapp_when_no_email():
    assert Client().caa_two_step_verification_channel(WHATSAPP_PAYLOAD) == "whatsapp"


def test_email_wins_when_both_markers_are_present():
    assert Client().caa_two_step_verification_channel(BOTH_PAYLOAD) == "email"


def test_returns_empty_when_no_marker():
    assert Client().caa_two_step_verification_channel({"x": "(dkc \"other\" 1)"}) == ""
