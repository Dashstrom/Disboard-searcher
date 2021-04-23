import requests

from datetime import datetime
from typing import Generator, NamedTuple, List, Optional
from bs4 import BeautifulSoup
from time import time, sleep
from discord.utils import snowflake_time
from random import random


URL = "https://disboard.org"
BUMP_FMT = "%Y-%m-%d %H:%M:%S (%Z)"


class Guild(NamedTuple):
    id: int
    name: str
    image: str
    url: str
    description: str
    link: str
    tags: List[str]
    category: str
    flag: str
    online: int
    timestamp: int
    bump: int

    @property
    def created_at(self) -> int:
        return snowflake_time(self.id).timestamp()

    def __hash__(self) -> int:
        return self.id


def _get_servers_page(keyword: str, page: int) -> List[Guild]:
    r = requests.get(f"{URL}/fr/search",
                     params={"keyword": keyword, "page": str(page)})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    list_servers = soup.findAll("div", {
        "class": "column is-one-third-desktop is-half-tablet"})

    guilds: List[Guild] = []
    for server in list_servers:
        icon = server.find("div", {"class": "server-icon"})
        desc = server.find("div", {"class": "server-description"})
        invite = server.find("div", {"class": "server-join"})
        tags = server.find("ul", {"class": "tags"})
        category = server.find("a", {"class": "server-category category"})
        count_online = server.find("span", {"class": "server-online"})
        flag = server.find("span", {"class": "flag-icon"})
        bump_div = server.find("div", {"class": "server-bumped-at"})
        if bump_div:
            bump_date = datetime.strptime(bump_div["title"], BUMP_FMT)
            bump = int(bump_date.timestamp())
        else:
            bump = -1
        guild = Guild(
            id=int(invite.a["data-id"]),
            name=icon.img["alt"].replace(" ", ""),
            image=icon.img["src"],
            url=f"{URL}{icon.a['href']}",
            description=desc.text.strip() if desc else "",
            link=f"{URL}{invite.a['href']}",
            tags=[tag["title"] for tag in tags.findAll("a")],
            category=category.text.strip() if category else "",
            online=int(count_online.text),
            timestamp=int(time()),
            flag=flag["class"] if flag else "",
            bump=bump,
        )
        guilds.append(guild)
    return guilds


def fetch_servers(
    keyword: str, limit: Optional[int] = None
) -> Generator[Guild, None, None]:
    page_index = 1
    count = 0
    last = None
    while True:
        guilds_on_page = _get_servers_page(keyword, page_index)
        for guild in guilds_on_page:
            yield guild
            count += 1
            if last == guilds_on_page or limit and count >= limit:
                return
        if len(guilds_on_page) < 24:
            break
        page_index += 1
        sleep(random() * 3 + 6)
        last = guilds_on_page


if __name__ == "__main__":
    import argparse
    import csv

    def positive_int(string):
        ivalue = int(string)
        if ivalue <= 0:
            raise argparse.ArgumentTypeError(
                f"{ivalue} is an invalid positive int value")
        return ivalue

    parser = argparse.ArgumentParser()
    parser.add_argument("keyword", help="keyword for search")
    parser.add_argument("output", help="output csv")
    parser.add_argument("-l", "--limit", type=positive_int,
                        help="guilds limit")
    args = parser.parse_args()

    print("Fetch guilds...")
    guilds = fetch_servers(args.keyword, limit=args.limit)
    with open(args.output, "w", encoding="utf8") as file:
        writer = csv.writer(file)
        for guild in guilds:
            print(f"Writing guild {guild.name!r} ({guild.id})")
            writer.writerow(guild)
    print("Done")
