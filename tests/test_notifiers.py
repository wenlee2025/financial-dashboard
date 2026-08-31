from unittest.mock import patch, MagicMock
from src.notifiers.dispatcher import NotificationDispatcher
from src.notifiers.telegram import TelegramNotifier
from src.notifiers.discord import DiscordNotifier
from src.notifiers.line import LineNotifier
from src.notifiers.slack import SlackNotifier
from src.notifiers.smtp_email import SMTPEmailNotifier

def test_notifier_configurations():
    tg = TelegramNotifier("fake_token", "fake_chat_id")
    assert tg.is_configured

    tg_empty = TelegramNotifier(None, None)
    assert not tg_empty.is_configured

    dc = DiscordNotifier("https://discord.com/api/webhooks/test")
    assert dc.is_configured

    dc_empty = DiscordNotifier(None)
    assert not dc_empty.is_configured

    line = LineNotifier("fake_token", "fake_user")
    assert line.is_configured

    slack = SlackNotifier("https://hooks.slack.com/services/test")
    assert slack.is_configured

    smtp = SMTPEmailNotifier({
        "server": "smtp.example.com",
        "port": 587,
        "user": "user@example.com",
        "password": "pwd",
        "to": ["to@example.com"]
    })
    assert smtp.is_configured

def test_dispatcher_mock_broadcast():
    dispatcher = NotificationDispatcher(
        telegram_token="token",
        telegram_chat_id="chat_id",
        discord_webhook="https://discord.com/webhook",
        line_token="line_token",
        line_user_id="line_user",
        slack_webhook="https://slack.com/webhook",
        smtp_config={"server": "smtp.test", "user": "u", "password": "p", "to": ["to@test"]}
    )

    with patch.object(dispatcher.telegram, "send_message", return_value=True), \
         patch.object(dispatcher.discord, "send_message", return_value=True), \
         patch.object(dispatcher.line, "send_message", return_value=True), \
         patch.object(dispatcher.slack, "send_message", return_value=True), \
         patch.object(dispatcher.email, "send_email", return_value=True):

        results = dispatcher.dispatch_all("summary text", "<html>html</html>", "subject")
        assert results["telegram"] is True
        assert results["discord"] is True
        assert results["line"] is True
        assert results["slack"] is True
        assert results["email"] is True
