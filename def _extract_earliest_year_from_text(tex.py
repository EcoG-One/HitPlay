import re


def _extract_earliest_year_from_text(text):
    if not text:
        return ""
    years = re.findall(r"\b(19[0-9]{2}|20[0-9]{2})\b", str(text))
    return min(years) if years else ""


print(
    _extract_earliest_year_from_text(
        "'{{Start date|1978|01|27|df=y}}<ref>{{cite magazine|title=Releases — Listings|magazine=[[Music Week]]|date=28 January 1978|page=39|issn=0265-1548|quote=Singles notified by major manufacturers for week ending 27th January 1978.}}</ref>\n'"
    )
)
