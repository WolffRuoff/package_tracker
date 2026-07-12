"""Tests for base carrier infrastructure: _identify_bot_service and _get_page_content."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

from scraper.carriers.base import _identify_bot_service
from scraper.carriers.usps import USPSProvider


@pytest.fixture
def provider():
    return USPSProvider()


class TestIdentifyBotService:
    """Unit tests for the bot-protection detection helper."""

    # DataDome
    def test_datadome_url(self):
        assert _identify_bot_service("https://geo.datadome.co/captcha", "", {}) == "DataDome"

    def test_datadome_captcha_delivery_url(self):
        assert _identify_bot_service("https://captcha-delivery.com/x", "", {}) == "DataDome"

    def test_datadome_response_header(self):
        assert _identify_bot_service("https://example.com", "", {"x-dd-b": "bot"}) == "DataDome"

    def test_datadome_in_html(self):
        assert _identify_bot_service("https://example.com", "<script>datadome</script>", {}) == "DataDome"

    # Akamai — only the interstitial's own markers count as a block. Generic
    # CDN presence (x-akamai-* headers, akam.net, mPulse RUM) is normal
    # traffic for huge sites like UPS/USPS and must NOT be flagged, since
    # that's what previously mislabeled ordinary UPS responses as blocked.
    def test_akamai_abck_cookie_in_html(self):
        assert _identify_bot_service("https://example.com", "document.cookie has _abck=abc123", {}) == "Akamai Bot Manager"

    def test_akamai_bmsc_cookie_in_html(self):
        assert _identify_bot_service("https://example.com", "ak_bmsc=xyz; path=/", {}) == "Akamai Bot Manager"

    def test_akamai_bm_verify_in_html(self):
        assert _identify_bot_service("https://example.com", "token bm-verify required", {}) == "Akamai Bot Manager"

    def test_akamai_sec_verify_endpoint_in_html(self):
        assert _identify_bot_service("https://example.com", 'fetch("/_sec/verify?provider=interstitial")', {}) == "Akamai Bot Manager"

    def test_akamai_ghost_server_header(self):
        assert _identify_bot_service("https://example.com", "", {"server": "AkamaiGHost"}) == "Akamai Bot Manager"

    def test_akamai_cdn_headers_alone_not_flagged(self):
        """Regression: normal Akamai CDN pass-through (origin's own server header,
        RUM/analytics artifacts) must not be mistaken for an active block."""
        headers = {
            "server": "Apache",
            "x-akamai-transformed": "9l 2430 0 pmb=mNONE, 1mRUM, 2",
            "server-timing": 'cdn-cache; desc=MISS, edge; dur=2123, origin; dur=15, ak_p; desc="123";dur=1',
        }
        assert _identify_bot_service("https://www.ups.com/track", "", headers) == "unknown"

    def test_akamai_mpulse_domain_not_flagged(self):
        assert _identify_bot_service("https://example.com", 'src="https://c.go-mpulse.net/api/config.json"', {}) == "unknown"

    def test_akamai_generic_header_key_not_flagged(self):
        assert _identify_bot_service("https://example.com", "", {"x-akamai-request-id": "abc123"}) == "unknown"

    # Kasada
    def test_kasada_kpsdk(self):
        assert _identify_bot_service("https://example.com", "var _kpsdk = {};", {}) == "Kasada"

    def test_kasada_kpsdk_variant(self):
        assert _identify_bot_service("https://example.com", "kpsdk challenge data", {}) == "Kasada"

    def test_kasada_ips_js(self):
        assert _identify_bot_service("https://example.com", 'src="/ips.js"', {}) == "Kasada"

    # Cloudflare
    def test_cloudflare_url(self):
        assert _identify_bot_service("https://cloudflare.com/path", "", {}) == "Cloudflare"

    def test_cloudflare_server_header(self):
        assert _identify_bot_service("https://example.com", "", {"server": "cloudflare"}) == "Cloudflare"

    def test_cloudflare_just_a_moment_html(self):
        assert _identify_bot_service("https://example.com", "Just a moment...", {}) == "Cloudflare"

    def test_cloudflare_cf_bm_html(self):
        assert _identify_bot_service("https://example.com", "__cf_bm cookie value", {}) == "Cloudflare"

    # Imperva / Incapsula
    def test_imperva_url(self):
        assert _identify_bot_service("https://imperva.com/block", "", {}) == "Imperva/Incapsula"

    def test_incapsula_html(self):
        assert _identify_bot_service("https://example.com", "incapsula resource blocked", {}) == "Imperva/Incapsula"

    def test_incapsula_resource_tag(self):
        assert _identify_bot_service("https://example.com", "_Incapsula_Resource", {}) == "Imperva/Incapsula"

    # PerimeterX
    def test_perimeterx_html(self):
        assert _identify_bot_service("https://example.com", "perimeterx challenge", {}) == "PerimeterX"

    def test_perimeterx_pxdk(self):
        assert _identify_bot_service("https://example.com", "var _pxdk = {};", {}) == "PerimeterX"

    # Unknown / no match
    def test_unknown_clean_page(self):
        assert _identify_bot_service("https://example.com", "<html><body>Hello</body></html>", {}) == "unknown"

    def test_unknown_empty_inputs(self):
        assert _identify_bot_service("", "", {}) == "unknown"

    def test_case_insensitive_html_matching(self):
        assert _identify_bot_service("https://example.com", "DataDome Script", {}) == "DataDome"

    def test_case_insensitive_url_matching(self):
        assert _identify_bot_service("https://CLOUDFLARE.COM/path", "", {}) == "Cloudflare"


class TestGetPageContent:
    """Tests for CarrierProvider._get_page_content error logging and behaviour."""

    @pytest.mark.asyncio
    async def test_returns_page_html_on_success(self, provider, mock_browser):
        browser, mock_page = mock_browser
        mock_page.content.return_value = "<html>tracking info</html>"

        result = await provider._get_page_content(browser, "https://example.com", ".selector")

        assert result == "<html>tracking info</html>"

    @pytest.mark.asyncio
    async def test_registers_response_listener(self, provider, mock_browser):
        browser, mock_page = mock_browser

        await provider._get_page_content(browser, "https://example.com", ".selector")

        mock_page.on.assert_called_once()
        assert mock_page.on.call_args[0][0] == "response"

    @pytest.mark.asyncio
    async def test_closes_context_on_success(self, provider, mock_browser):
        browser, mock_page = mock_browser
        mock_context = browser.new_context.return_value

        await provider._get_page_content(browser, "https://example.com", ".selector")

        mock_context.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_closes_context_on_failure(self, provider, mock_browser):
        browser, mock_page = mock_browser
        mock_context = browser.new_context.return_value
        mock_page.wait_for_selector.side_effect = Exception("timeout")

        with pytest.raises(Exception):
            await provider._get_page_content(browser, "https://example.com", ".selector")

        mock_context.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout_reraises_exception(self, provider, mock_browser):
        browser, mock_page = mock_browser
        mock_page.wait_for_selector.side_effect = Exception("Timeout exceeded")

        with pytest.raises(Exception, match="Timeout exceeded"):
            await provider._get_page_content(browser, "https://example.com", ".selector")

    @pytest.mark.asyncio
    async def test_timeout_logs_page_load_failed(self, provider, mock_browser, caplog):
        browser, mock_page = mock_browser
        mock_page.wait_for_selector.side_effect = Exception("timeout")
        mock_page.content.return_value = "<html>normal page</html>"

        with caplog.at_level(logging.ERROR, logger="scraper.carriers.base"):
            with pytest.raises(Exception):
                await provider._get_page_content(browser, "https://example.com", ".selector")

        assert "Page load failed" in caplog.text

    @pytest.mark.asyncio
    async def test_timeout_logs_kasada_bot_service(self, provider, mock_browser, caplog):
        browser, mock_page = mock_browser
        mock_page.wait_for_selector.side_effect = Exception("timeout")
        mock_page.url = "https://tools.usps.com/go/TrackConfirmAction?tLabels=123"
        mock_page.content.return_value = "<html><script>var _kpsdk = {};</script></html>"

        with caplog.at_level(logging.ERROR, logger="scraper.carriers.base"):
            with pytest.raises(Exception):
                await provider._get_page_content(browser, "https://tools.usps.com/go/TrackConfirmAction?tLabels=123", ".track-statusbar")

        assert "bot_service=Kasada" in caplog.text

    @pytest.mark.asyncio
    async def test_timeout_logs_datadome_redirect(self, provider, mock_browser, caplog):
        browser, mock_page = mock_browser
        mock_page.wait_for_selector.side_effect = Exception("timeout")
        mock_page.url = "https://geo.datadome.co/captcha?initialUrl=https://tools.usps.com"
        mock_page.title.return_value = "Access Denied"
        mock_page.content.return_value = "<html>datadome blocked</html>"

        with caplog.at_level(logging.ERROR, logger="scraper.carriers.base"):
            with pytest.raises(Exception):
                await provider._get_page_content(browser, "https://tools.usps.com", ".selector")

        assert "geo.datadome.co" in caplog.text
        assert "DataDome" in caplog.text

    @pytest.mark.asyncio
    async def test_timeout_logs_selector_and_url(self, provider, mock_browser, caplog):
        browser, mock_page = mock_browser
        mock_page.wait_for_selector.side_effect = Exception("timeout")
        mock_page.content.return_value = ""

        with caplog.at_level(logging.ERROR, logger="scraper.carriers.base"):
            with pytest.raises(Exception):
                await provider._get_page_content(browser, "https://example.com/track", ".my-selector")

        assert "https://example.com/track" in caplog.text
        assert ".my-selector" in caplog.text

    @pytest.mark.asyncio
    async def test_response_listener_receives_headers_on_failure(self, provider, mock_browser, caplog):
        """Verify response headers collected by the listener appear in the error log."""
        browser, mock_page = mock_browser
        mock_page.content.return_value = ""

        # Capture the registered callback so we can invoke it ourselves
        captured_callback = None

        def capture_on(event, callback):
            nonlocal captured_callback
            if event == "response":
                captured_callback = callback

        mock_page.on.side_effect = capture_on

        # Intercept goto to fire the response callback (simulating the browser firing
        # a response event) before the subsequent wait_for_selector raises.
        fake_response = AsyncMock()
        fake_response.all_headers = AsyncMock(return_value={"x-dd-b": "bot", "server": "nginx"})
        original_goto = mock_page.goto

        async def goto_then_fire_response(*args, **kwargs):
            result = await original_goto(*args, **kwargs)
            if captured_callback:
                await captured_callback(fake_response)
            return result

        mock_page.goto = goto_then_fire_response
        mock_page.wait_for_selector.side_effect = Exception("timeout")

        with caplog.at_level(logging.ERROR, logger="scraper.carriers.base"):
            with pytest.raises(Exception):
                await provider._get_page_content(browser, "https://example.com", ".selector")

        assert "x-dd-b" in caplog.text
        assert "DataDome" in caplog.text
