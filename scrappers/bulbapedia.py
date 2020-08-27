import os
import requests
import bs4
from multiprocessing import Pool
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from hashlib import md5

BASE_PATH = os.path.join(os.getcwd(), 'data')


def map_pokemons(start=1, end=151, all=False):
    """
    Builds a dictionary with Pokémon and their Pokedéx numbers according to Bulbapedia.
    Pokedéx number is padded with zeroes. By default, grabs 1st generation of Pokémon (1-151).
    Might break if the Bulbapedia page structure changes.

    Parameters:
        start (int): first Pokémon number. Default: 1
        end (int): last Pokémon number (inclusive). Default: 151
        all (bool): whether to grab all Pokémon. Overrides start/end. Default: False
    """
    print("Building Pokédex...")
    pokedex = {}
    pokedex_url = "https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_by_National_Pok%C3%A9dex_number"
    req = requests.get(pokedex_url)
    soup = bs4.BeautifulSoup(req.text, features="lxml")
    gens = soup.select("#mw-content-text > table")
    for gen in gens[1:-1]:  # exclude useless wiki tables
        rows = gen.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            cols = [item.text.strip() for item in cols]
            try:
                if cols[1]:
                    # dict format: pokedex['001']: 'Bulbasaur'
                    pokedex[cols[1].strip('#')] = cols[2]
            except IndexError:
                continue
    if len(pokedex) > end and not all:
        pokedex_trimmed = {}
        for pokemon in pokedex:
            try:
                if int(pokemon) < start:
                    pass
                else:
                    pokedex_trimmed[pokemon] = pokedex[pokemon]
                if int(pokemon) == end:
                    break
            except ValueError:
                pass
        print("Pokédex built. Got", len(pokedex_trimmed), "Pokémon.")
        return pokedex_trimmed
    print("Full Pokédex built. Got", len(pokedex), "Pokémon.")
    return pokedex


def scrape_image(url: str, pokenumber: str):
    """
    Get a single image and save it in a directory defined by the Pokedéx number.
    Image is saved to BASE_PATH + pokenumber directory.

    Parameters:
        url (str): url to the image to be downloaded.
        pokenumber (str): pre-formatted pokemon number.
    """
    session = requests.Session()
    # prevent timeout
    retry = Retry(connect=5, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    img_req = session.get(url)
    if img_req.status_code == 200:
        img = img_req.content
        path = os.path.join(BASE_PATH, pokenumber)
        os.makedirs(path, exist_ok=True)
        filename = os.path.join(path, url.split("/")[-1])
        with open(filename, 'wb') as f:
            f.write(img)


def scrape_pokemon(pokemon: list):
    """
    Finds all images of a Pokémon in Bulbapedia and calls scrape_image() to fetch and save them.
    Expects a single argument 'pokemon' as ["number", "name"], which is generated by map_pokemons().
    """
    try:
        pokenumber = pokemon[0]
        pokename = pokemon[1]
    except IndexError as e:
        print("Error: index out of range. Pass pokemon as [\"number\", \"name\"]")
    url = "https://archives.bulbagarden.net/w/api.php"
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:" + pokename,
        "cmlimit": "max",  # default 500
        "cmtype": "file",
        "format": "json",
        "cmcontinue": ""  # scrape all pages if more than cmlimit
    }
    pages = []
    print("Fetching URLs for", pokename)
    while True:  # dangerous but no do-while in Python
        resp = requests.get(url, params)
        resp = resp.json()
        pages += [image["title"].strip("File:").replace(" ", "_").encode("utf-8") for image in resp["query"]["categorymembers"]]
        if "continue" in resp:
            params["cmcontinue"] = resp["continue"]["cmcontinue"]
            continue
        else:
            break
    # direct image paths use md5 for folders. See: https://www.mediawiki.org/wiki/Manual:$wgHashedUploadDirectory
    links = ["https://archives.bulbagarden.net/media/upload/" + md5(image).hexdigest()[0] + "/" + md5(image).hexdigest()[0:2] + "/" + image.decode('utf-8') for image in pages]
    print("Got", len(links), "images for",
          pokename + ".", "Downloading images...")
    # I think a larger pool size increases chance of connection reset. not sure.
    with Pool(os.cpu_count() - 1) as p:
        p.starmap(
            scrape_image,
            zip(links, [pokenumber for i in range(len(links))])
        )
    print("Finished downloading images for", pokename + ".")


pokedex = map_pokemons()
# can maybe call this with multiprocessing.Pool as well? Not sure if it'd perform any better.
for dex, pokemon in pokedex.items():
    scrape_pokemon([dex, pokemon])
