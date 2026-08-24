"""xplainable branding for the FastMCP OAuth consent/callback pages.

FastMCP's auth pages (consent screen, callback status) are rendered by
``fastmcp.server.auth.oauth_proxy`` via a shared ``create_page`` helper
with hard-coded generic styling. There is no supported theming hook, so
``apply_consent_branding()`` wraps that module's ``create_page`` to
append a brand stylesheet — later rules in the same <style> tag win at
equal specificity, so this overrides the defaults without touching the
page structure. The patch is scoped to ``oauth_proxy``'s namespace only;
other ``fastmcp.utilities.ui`` consumers are unaffected.

Brand colours are taken from the xplainable logo (www.xplainable.io/icon.svg):
pink #E14067 and blue #0080EA.
"""

import functools

XPLAINABLE_ICON_URL = "https://www.xplainable.io/icon.svg"

BRAND_STYLES = """
    /* xplainable brand overrides */
    body {
        background: #0e1420;
        color: #e5e7eb;
    }

    .container {
        background: #151d2e;
        border: 1px solid #26324a;
        box-shadow: 0 12px 32px -8px rgba(0, 0, 0, 0.55);
    }

    .logo {
        width: 72px;
    }

    h1 {
        color: #f3f4f6;
    }

    .info-box {
        background: rgba(0, 128, 234, 0.08);
        border: 1px solid rgba(0, 128, 234, 0.35);
        color: #d1d5db;
    }

    .info-box p, .info-box strong {
        color: #e5e7eb;
    }

    .info-box a, .server-name-link {
        color: #4da3ff;
    }

    .redirect-section {
        background: rgba(225, 64, 103, 0.08);
        border: 1px solid rgba(225, 64, 103, 0.35);
    }

    .redirect-section .label {
        color: #f3f4f6;
    }

    .redirect-section .value {
        color: #ff8fab;
    }

    details summary {
        color: #9ca3af;
    }

    .detail-box {
        background: #10182a;
        border: 1px solid #26324a;
    }

    .detail-label {
        color: #9ca3af;
    }

    .detail-value {
        color: #e5e7eb;
    }

    .btn-approve, .btn-primary {
        background: #0080EA;
    }

    .btn-approve:hover, .btn-primary:hover {
        background: #0068c0;
    }

    .btn-deny, .btn-secondary {
        background: transparent;
        border: 1px solid #4b5563;
        color: #d1d5db;
    }

    .btn-deny:hover, .btn-secondary:hover {
        background: #1f2937;
    }

    .help-link, .help-link-container {
        color: #9ca3af;
    }
"""


def apply_consent_branding() -> None:
    """Wrap oauth_proxy.create_page so auth pages carry xplainable styling."""
    from fastmcp.server.auth import oauth_proxy

    original = oauth_proxy.create_page
    if getattr(original, "_xplainable_branded", False):
        return

    @functools.wraps(original)
    def branded_create_page(content, *args, additional_styles: str = "", **kwargs):
        return original(
            content,
            *args,
            additional_styles=additional_styles + BRAND_STYLES,
            **kwargs,
        )

    branded_create_page._xplainable_branded = True
    oauth_proxy.create_page = branded_create_page
