"""
Site base: https://pokemondb.net
"""

from typing import List
import requests
import re
from bs4 import BeautifulSoup
import pokebase as pb


def getImagesURLbyId(id: int) -> List[str]:
    print(f"> Pushando #{id} de pokemondb.net")

    pokemon = pb.pokemon(id)
    url = f"https://pokemondb.net/sprites/{pokemon.name}"

    response = requests.get(url)
    soup = BeautifulSoup(response.text)

    pattern = r"https://img.pokemondb.net/sprites/.*"
    imgs = soup.find_all("img", {"src": re.compile(pattern)})
    lazy_imgs = soup.find_all("span", {"data-src": re.compile(pattern)})

    links = []
    links += [img.get('src') for img in imgs]
    links += [img.get('data-src') for img in lazy_imgs]

    return links


if __name__ == "__main__":
    for id in range(1, 3):
        print(getImagesURLbyId(id))
