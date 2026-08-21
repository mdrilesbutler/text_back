from __future__ import annotations

from xml.etree import ElementTree


def empty_response() -> str:
    """Return a valid, side-effect-free cXML response document."""
    return _serialize(ElementTree.Element("Response"))


def forwarded_call_response(business_name: str) -> str:
    """Tell a forwarded caller what happens next, then end the call politely."""
    response = ElementTree.Element("Response")
    say = ElementTree.SubElement(response, "Say")
    say.text = (
        f"Thanks for calling {business_name}. We couldn't answer, "
        "but we'll text you shortly. Goodbye."
    )
    ElementTree.SubElement(response, "Hangup")
    return _serialize(response)


def _serialize(root: ElementTree.Element) -> str:
    return ElementTree.tostring(
        root,
        encoding="unicode",
        short_empty_elements=True,
    )
