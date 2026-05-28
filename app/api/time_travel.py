"""
Time Travel and Places REST Endpoints for ChronoCraft Time Machine
"""

import logging
import re
import json
import httpx
from typing import Optional, List, Dict, Any, TypedDict
from urllib.parse import quote
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.llm import get_llm_provider, LLMConfig

logger = logging.getLogger(__name__)
router = APIRouter(tags=["TimeTravel"])

# ----------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------


class PlacesRequest(BaseModel):
    action: str
    input: Optional[str] = None
    place_id: Optional[str] = None
    description: Optional[str] = None


class TimeTravelRequest(BaseModel):
    action: str
    locationName: Optional[str] = None
    year: Optional[int] = None
    targetDate: Optional[str] = None
    eraName: Optional[str] = None
    forecastTopic: Optional[str] = None
    techLevel: Optional[str] = None
    societalChange: Optional[str] = None
    environmentalShift: Optional[str] = None
    timeHorizon: Optional[str] = None
    customCatalyst: Optional[str] = None
    currentTrends: Optional[str] = None
    historicalEventTypes: Optional[str] = None


# ----------------------------------------------------------------------
# Local Database & Offline Engine
# ----------------------------------------------------------------------


class LocalPlaceEntry(TypedDict):
    description: str
    lat: float
    lng: float
    keywords: list[str]


LOCAL_DATABASE: list[LocalPlaceEntry] = [
    {
        "description": "Library of Alexandria, Alexandria, Egypt",
        "lat": 31.200,
        "lng": 29.918,
        "keywords": ["alexandria", "egypt", "library", "pharos", "ptolemy", "ancient"],
    },
    {
        "description": "Runnymede, Surrey, England",
        "lat": 51.444,
        "lng": -0.565,
        "keywords": [
            "runnymede",
            "england",
            "magna",
            "carta",
            "king john",
            "london",
            "surrey",
        ],
    },
    {
        "description": "Timbuktu, Mali, West Africa",
        "lat": 16.775,
        "lng": -3.008,
        "keywords": [
            "timbuktu",
            "mali",
            "musa",
            "sankore",
            "africa",
            "madrasa",
            "gold",
        ],
    },
    {
        "description": "Cape Canaveral, Florida, USA",
        "lat": 28.392,
        "lng": -80.608,
        "keywords": [
            "cape",
            "canaveral",
            "florida",
            "space",
            "apollo",
            "nasa",
            "kennedy",
        ],
    },
    {
        "description": "Colosseum, Rome, Italy",
        "lat": 41.890,
        "lng": 12.492,
        "keywords": ["rome", "italy", "colosseum", "roman", "coliseum", "amphitheatre"],
    },
    {
        "description": "Parthenon, Athens, Greece",
        "lat": 37.971,
        "lng": 23.727,
        "keywords": ["athens", "greece", "parthenon", "acropolis", "greek", "temple"],
    },
    {
        "description": "Pyramids of Giza, Cairo, Egypt",
        "lat": 29.979,
        "lng": 31.134,
        "keywords": [
            "pyramids",
            "giza",
            "cairo",
            "egypt",
            "khufu",
            "sphinx",
            "pharaoh",
        ],
    },
    {
        "description": "Taj Mahal, Agra, India",
        "lat": 27.175,
        "lng": 78.042,
        "keywords": [
            "taj",
            "mahal",
            "agra",
            "india",
            "mughal",
            "shah jahan",
            "mausoleum",
        ],
    },
    {
        "description": "Machu Picchu, Cusco, Peru",
        "lat": -13.163,
        "lng": -72.545,
        "keywords": ["machu", "picchu", "cusco", "peru", "inca", "andes", "ancient"],
    },
    {
        "description": "Great Wall of China, Beijing, China",
        "lat": 40.431,
        "lng": 116.570,
        "keywords": ["great", "wall", "china", "beijing", "peking", "dynasty"],
    },
    {
        "description": "Stonehenge, Salisbury, England",
        "lat": 51.178,
        "lng": -1.826,
        "keywords": [
            "stonehenge",
            "salisbury",
            "england",
            "druid",
            "neolithic",
            "monument",
        ],
    },
    {
        "description": "Angkor Wat, Siem Reap, Cambodia",
        "lat": 13.412,
        "lng": 103.867,
        "keywords": ["angkor", "wat", "siem", "reap", "cambodia", "khmer", "temple"],
    },
    {
        "description": "Petra, Jordan",
        "lat": 30.328,
        "lng": 35.444,
        "keywords": ["petra", "jordan", "treasury", "nabataean", "rock", "canyon"],
    },
    {
        "description": "Chichen Itza, Yucatan, Mexico",
        "lat": 20.684,
        "lng": -88.567,
        "keywords": ["chichen", "itza", "mexico", "yucatan", "mayan", "pyramid"],
    },
    {
        "description": "Kyoto, Honshu, Japan",
        "lat": 35.011,
        "lng": 135.768,
        "keywords": ["kyoto", "japan", "temple", "shogun", "heian", "emperor"],
    },
    {
        "description": "Constantinople, Istanbul, Turkey",
        "lat": 41.008,
        "lng": 28.978,
        "keywords": [
            "constantinople",
            "istanbul",
            "turkey",
            "byzantine",
            "hagia",
            "sophia",
            "roman",
        ],
    },
    {
        "description": "Eiffel Tower, Paris, France",
        "lat": 48.858,
        "lng": 2.294,
        "keywords": ["paris", "france", "eiffel", "tower", "louvre", "seine"],
    },
    {
        "description": "Babylon, Hillah, Iraq",
        "lat": 32.542,
        "lng": 44.424,
        "keywords": [
            "babylon",
            "iraq",
            "hanging",
            "gardens",
            "euphrates",
            "mesopotamia",
            "hammurabi",
        ],
    },
    {
        "description": "Tenochtitlan, Mexico City, Mexico",
        "lat": 19.432,
        "lng": -99.133,
        "keywords": ["tenochtitlan", "mexico", "aztec", "texcoco", "lake", "moctezuma"],
    },
    {
        "description": "Pompeii, Naples, Italy",
        "lat": 40.751,
        "lng": 14.487,
        "keywords": ["pompeii", "naples", "italy", "vesuvius", "roman", "eruption"],
    },
    {
        "description": "Scone Palace, Perthshire, Scotland",
        "lat": 56.417,
        "lng": -3.433,
        "keywords": [
            "scone",
            "scotland",
            "perthshire",
            "stone",
            "destiny",
            "coronation",
            "macbeth",
        ],
    },
    {
        "description": "London, England, UK",
        "lat": 51.507,
        "lng": -0.127,
        "keywords": [
            "london",
            "england",
            "uk",
            "british",
            "thames",
            "parliament",
            "big ben",
        ],
    },
    {
        "description": "Washington D.C., USA",
        "lat": 38.907,
        "lng": -77.036,
        "keywords": ["washington", "dc", "usa", "america", "capitol", "white house"],
    },
    {
        "description": "Jerusalem, Israel/Palestine",
        "lat": 31.768,
        "lng": 35.213,
        "keywords": ["jerusalem", "holy", "temple", "zion", "dome", "western"],
    },
    {
        "description": "Persepolis, Shiraz, Iran",
        "lat": 29.935,
        "lng": 52.889,
        "keywords": [
            "persepolis",
            "shiraz",
            "iran",
            "persian",
            "cyrus",
            "darius",
            "achaemenid",
        ],
    },
    {
        "description": "Teotihuacan, Valley of Mexico, Mexico",
        "lat": 19.692,
        "lng": -98.843,
        "keywords": [
            "teotihuacan",
            "mexico",
            "aztec",
            "sun",
            "moon",
            "pyramid",
            "pre-columbian",
        ],
    },
    {
        "description": "Knossos Palace, Crete, Greece",
        "lat": 35.298,
        "lng": 25.163,
        "keywords": [
            "knossos",
            "crete",
            "greece",
            "minonan",
            "labyrinth",
            "minotaur",
            "bronze",
        ],
    },
    {
        "description": "Tokyo, Kanto, Japan",
        "lat": 35.676,
        "lng": 139.650,
        "keywords": ["tokyo", "edo", "japan", "kanto", "shibuya", "shinjuku"],
    },
    {
        "description": "Athens, Attica, Greece",
        "lat": 37.983,
        "lng": 23.727,
        "keywords": ["athens", "acropolis", "parthenon", "greece", "classical"],
    },
    {
        "description": "Baghdad, Iraq",
        "lat": 33.315,
        "lng": 44.366,
        "keywords": [
            "baghdad",
            "iraq",
            "caliphate",
            "house",
            "wisdom",
            "tigris",
            "mesopotamia",
        ],
    },
    {
        "description": "Xi'an, Shaanxi, China",
        "lat": 34.341,
        "lng": 108.939,
        "keywords": ["xian", "china", "terracotta", "warriors", "chang", "silk road"],
    },
    {
        "description": "Carthage, Tunis, Tunisia",
        "lat": 36.852,
        "lng": 10.323,
        "keywords": [
            "carthage",
            "karthago",
            "tunis",
            "tunisia",
            "punic",
            "hannibal",
            "roman",
        ],
    },
    {
        "description": "Palace of Versailles, Versailles, France",
        "lat": 48.804,
        "lng": 2.120,
        "keywords": ["versailles", "france", "louis", "palace", "sun king"],
    },
    {
        "description": "Delhi, India",
        "lat": 28.613,
        "lng": 77.209,
        "keywords": [
            "delhi",
            "new delhi",
            "india",
            "red fort",
            "qutub minar",
            "mughal",
        ],
    },
    {
        "description": "Beijing, China",
        "lat": 39.904,
        "lng": 116.407,
        "keywords": [
            "beijing",
            "peking",
            "china",
            "forbidden city",
            "tiananmen",
            "ming",
        ],
    },
    {
        "description": "Berlin, Germany",
        "lat": 52.520,
        "lng": 13.405,
        "keywords": ["berlin", "germany", "brandenburg", "wall", "reichstag"],
    },
    {
        "description": "Moscow, Russia",
        "lat": 55.755,
        "lng": 37.617,
        "keywords": ["moscow", "russia", "kremlin", "red square", "st basil", "soviet"],
    },
    {
        "description": "Sydney, New South Wales, Australia",
        "lat": -33.868,
        "lng": 151.209,
        "keywords": ["sydney", "australia", "opera house", "harbour", "nsw"],
    },
    {
        "description": "Palenque, Chiapas, Mexico",
        "lat": 17.484,
        "lng": -91.995,
        "keywords": ["palenque", "chiapas", "mexico", "maya", "jungle", "pakal"],
    },
    {
        "description": "New York, New York, USA",
        "lat": 40.7128,
        "lng": -74.0060,
        "keywords": [
            "new york",
            "nyc",
            "manhattan",
            "empire state",
            "liberty",
            "brooklyn",
        ],
    },
    {
        "description": "San Francisco, California, USA",
        "lat": 37.7749,
        "lng": -122.4194,
        "keywords": [
            "san francisco",
            "sf",
            "california",
            "golden gate",
            "silicon valley",
        ],
    },
    {
        "description": "Chicago, Illinois, USA",
        "lat": 41.8781,
        "lng": -87.6298,
        "keywords": ["chicago", "illinois", "midwest", "windy city", "willis"],
    },
    {
        "description": "Los Angeles, California, USA",
        "lat": 34.0522,
        "lng": -118.2437,
        "keywords": ["los angeles", "la", "hollywood", "california", "beverly"],
    },
    {
        "description": "Venice, Veneto, Italy",
        "lat": 45.4408,
        "lng": 12.3155,
        "keywords": ["venice", "venezia", "italy", "canals", "gondola", "st mark"],
    },
    {
        "description": "Florence, Tuscany, Italy",
        "lat": 43.7696,
        "lng": 11.2558,
        "keywords": [
            "florence",
            "firenze",
            "italy",
            "tuscany",
            "renaissance",
            "medici",
        ],
    },
    {
        "description": "Pisa, Tuscany, Italy",
        "lat": 43.7228,
        "lng": 10.4017,
        "keywords": ["pisa", "italy", "leaning", "tower", "galileo"],
    },
    {
        "description": "Seville, Andalusia, Spain",
        "lat": 37.3891,
        "lng": -5.9845,
        "keywords": [
            "seville",
            "sevilla",
            "spain",
            "andalusia",
            "cathedral",
            "alcazar",
        ],
    },
    {
        "description": "Madrid, Community of Madrid, Spain",
        "lat": 40.4168,
        "lng": -3.7038,
        "keywords": ["madrid", "spain", "royal palace", "prado"],
    },
    {
        "description": "Barcelona, Catalonia, Spain",
        "lat": 41.3851,
        "lng": 2.1734,
        "keywords": ["barcelona", "spain", "catalonia", "gaudi", "sagrada", "rambla"],
    },
    {
        "description": "Rio de Janeiro, Southeast Brazil",
        "lat": -22.9068,
        "lng": -43.1729,
        "keywords": ["rio", "brazil", "copacabana", "christ", "redeemer", "carnival"],
    },
    {
        "description": "Cairo, Greater Cairo, Egypt",
        "lat": 30.0444,
        "lng": 31.2357,
        "keywords": ["cairo", "egypt", "nile", "tahrir", "khalili"],
    },
    {
        "description": "Seoul, Capital Region, South Korea",
        "lat": 37.5665,
        "lng": 126.9780,
        "keywords": ["seoul", "korea", "joseon", "gangnam", "palace"],
    },
    {
        "description": "Singapore, Southeast Asia",
        "lat": 1.3521,
        "lng": 103.8198,
        "keywords": ["singapore", "asia", "merlion", "changi", "marina"],
    },
    {
        "description": "Mumbai, Maharashtra, India",
        "lat": 19.0760,
        "lng": 72.8777,
        "keywords": ["mumbai", "bombay", "india", "bollywood", "gateway"],
    },
    {
        "description": "Toronto, Ontario, Canada",
        "lat": 43.6532,
        "lng": -79.3832,
        "keywords": ["toronto", "ontario", "canada", "cn tower", "ontario"],
    },
    {
        "description": "Vancouver, British Columbia, Canada",
        "lat": 49.2827,
        "lng": -123.1207,
        "keywords": ["vancouver", "canada", "bc", "pacific"],
    },
    {
        "description": "Cape Town, Western Cape, South Africa",
        "lat": -33.9249,
        "lng": 18.4241,
        "keywords": ["cape town", "africa", "table mountain", "good hope"],
    },
]

LOCAL_PRESETS_SENSORY = {
    "alexandria": {
        "sensoryTitle": "The Scriptorium Alexandria",
        "sensoryDescription": "The dry aroma of papyrus rolls, linen covers, and burning olive-oil lamps fills the grand central hall of Alexandria. Quiet murmuring of Greek, Egyptian, and Hebrew scholars echoes off towering sandstone columns. Scribes lean over low cedar tables, dipping reed pens in iron-gall ink under high arched skywells.",
        "keyFigures": [
            {
                "name": "Ptolemy I Soter",
                "role": "Sovereign of Egypt",
                "bio": "General of Alexander the Great turned Pharaoh, who inaugurated the Library to assemble all global intellectual scrolls.",
            },
            {
                "name": "Demetrius of Phalerum",
                "role": "Chief Scriptorium Organizer",
                "bio": "Athenian scholar who oversaw the rapid cataloging system of multiple thousands of incoming Mediterranean texts.",
            },
        ],
        "virtualEvents": [
            {
                "title": "Arrival of the Athenian Classics",
                "context": "A maritime trading vessel docks, presenting rare philosophical manuscripts confiscated under royal decree for instant scribal copy.",
                "reference": "Alexandria Customs Scroll V1",
            },
            {
                "title": "Geometric Demonstration",
                "context": "Early mathematicians gather in the gardens to map shadow vectors, calculating the Earth circumference using simple gnomon rods.",
                "reference": "Eratosthenes' Meridian Notes",
            },
        ],
        "ambientToneRate": {
            "description": "Murmuring voices in Greek, scraping reeds, and rustling papyrus scrolls",
            "frequency": "432 Hz",
        },
    },
    "feudal": {
        "sensoryTitle": "Baron Constitutional Convening",
        "sensoryDescription": "The scent of rich river silt and damp marsh air floats over Runnymede. High-ranking barons clad in heavy chainmail stand vigilant on wet meadow soils. Brightly colored pennants snap in the stiff wind while squires murmur inside parchment-wrapped tents, their breath fogging in the cool June breeze.",
        "keyFigures": [
            {
                "name": "Archbishop Stephen Langton",
                "role": "Primate of England",
                "bio": "The intellectual mediator who drafted the foundational liberties layout incorporated directly into the Magna Carta.",
            },
            {
                "name": "King John Lackland",
                "role": "Plantagenet Sovereign",
                "bio": "Reluctantly sealed the legendary charter under intense military and political coercion, limiting unchecked monarchical decrees.",
            },
        ],
        "virtualEvents": [
            {
                "title": "Sovereign Oath of the Seal",
                "context": "The King is presented with the draft articles, attaching the royal Great Wax Seal under direct baron witness.",
                "reference": "British Library Manuscripts",
            },
            {
                "title": "Communal Armistice Feasting",
                "context": "Barons and royal guards share bread and spiced wine, establishing a temporary legal ceasefire across the Thames valley.",
                "reference": "Matthew Paris Chronicles",
            },
        ],
        "ambientToneRate": {
            "description": "Muffled plate armor clattering, blowing reeds, and heavy rain on canvas",
            "frequency": "228 Hz",
        },
    },
    "musa": {
        "sensoryTitle": "The Golden Caravan of Mali",
        "sensoryDescription": "Warm Sahara sand breezes stir fine red dust in the desert sunset. Spices like cinnamon, musk, and dried ginger mingle with the scent of campfire wood in Mali. Scholarly assemblies gather outside mud-brick mosques, comparing astrological quadrants while gold traders weigh glittering dust on heavy brass scales.",
        "keyFigures": [
            {
                "name": "Mansa Musa I",
                "role": "Emperor of Mali Empire",
                "bio": "Renowned sovereign who channeled absolute control over Saharan gold trails and became the patron of Timbuktu's golden intellectual age.",
            },
            {
                "name": "Abu Bakr II",
                "role": "Navigator King",
                "bio": "Musa's voyager brother who abdicated the throne to launch a grand exploratory fleet of 2,000 canoes across the Atlantic Ocean.",
            },
        ],
        "virtualEvents": [
            {
                "title": "Commissioning of the Great Mosque",
                "context": "Mansa Musa recruits Andalusian royal architect Abu Ishaq al-Sahili to erect the monumental mud-brick Djinguereber spiritual beacon.",
                "reference": "Timbuktu Scriptorium Leaf #88",
            },
            {
                "title": "The Salt Caravan Entrance",
                "context": "Over five thousand camels loaded with deep Saharan block salt arrive to trade ounce-for-ounce for pure sovereign gold bullion.",
                "reference": "Al-Umari's Travel Chronicles",
            },
        ],
        "ambientToneRate": {
            "description": "Rhythmic camel bells, soft desert whistles, and ancient drum beats",
            "frequency": "188 Hz",
        },
    },
    "apollo": {
        "sensoryTitle": "Cape Canaveral Lunar Warp",
        "sensoryDescription": "The sharp synthetic scent of aviation fuel, hot copper, solar panels, and ozone hangs thick in the Florida seaside air. High-frequency electrical hums from mission control mainframes resonate across steel launch gantries. Outside, the steady ocean surf beats against sandy beaches under a bright lunar sky.",
        "keyFigures": [
            {
                "name": "Neil Armstrong",
                "role": "Mission Commander",
                "bio": "Experienced naval test pilot who calmly piloted the Eagle lunar lander to the basalt surface of the Sea of Tranquility.",
            },
            {
                "name": "Katherine Johnson",
                "role": "Flight Dynamics Mathematician",
                "bio": "Calculated crucial trajectory paths checking the automated computers manually to ensure safe atmospheric return.",
            },
        ],
        "virtualEvents": [
            {
                "title": "Saturn V Launch Ignition Sequence",
                "context": "The five massive F-1 rocket engines ignite, releasing millions of pounds of thrust, shaking the Florida coastline.",
                "reference": "NASA Flight logs",
            },
            {
                "title": "The Lunar Telemetry Transmit",
                "context": "A crackly FM transmission is received back at tracking dishes, recording the first human footstep on another celestial sphere.",
                "reference": "Smithsonian Air & Space Catalog",
            },
        ],
        "ambientToneRate": {
            "description": "High-voltage electrical hums, mechanical cooling turbine fans, and coastal ocean tides",
            "frequency": "60 Hz",
        },
    },
}


def hash_code(s: str) -> int:
    h = 0
    for char in s:
        h = (h << 5) - h + ord(char)
        h = h & 0xFFFFFFFF
    if h >= 0x80000000:
        h -= 0x100000000
    return h


def selected_lat_jitter(year: int, idx: int) -> float:
    base_lat = 41.890
    offset = ((year * idx) % 100) / 1000.0
    return round(base_lat + offset, 4)


def selected_lng_jitter(year: int, idx: int) -> float:
    base_lng = 12.492
    offset = ((year * idx * 7) % 100) / 1000.0
    return round(base_lng + offset, 4)


def get_offline_pins_fallback(location_name: str, year: int) -> List[Dict[str, Any]]:
    normalized = location_name.lower()

    if "alexandria" in normalized or "egypt" in normalized:
        return [
            {
                "title": "Inauguration of the Pharos Lighthouse",
                "year": "-280",
                "latitude": 31.213,
                "longitude": 29.885,
                "description": "A monumental three-tier marble beacon measuring over 100 meters is completed on the island of Pharos. Utilizing giant polished mirrors by day and blazing fires by night, it steers Mediterranean merchant fleets safely into Egypt's harbors.",
                "keyFigures": [
                    "Sostratus of Cnidus (Lead Engineer)",
                    "Ptolemy II Philadelphus (Sovereign)",
                ],
                "dateFormatted": "C. 280 B.C.",
                "sources": [
                    {
                        "name": "Strabo's Geographic Recital",
                        "url": "https://www.britannica.com/topic/Pharos-of-Alexandria",
                    },
                    {
                        "name": "Ancient Maritime Port Chronicles",
                        "url": "https://www.worldhistory.org/Pharos_of_Alexandria/",
                    },
                ],
                "causes": "The rapid expansion of Mediterranean trade and the tricky, reef-laden coastline of Alexandria demanded a highly visible marine guiding beacon to avoid maritime disasters and secure Ptolemy's royal shipping lanes.",
                "consequences": "It stood as one of the Seven Wonders of the Ancient World for over fifteen centuries, successfully boosting trade of grains and materials throughout the Nile delta, and establishing lighthouse engineering parameters modeled across Europe.",
                "location": "Island of Pharos, Alexandria, Egypt",
            },
            {
                "title": "Translation of the Septuagint",
                "year": "-250",
                "latitude": 31.201,
                "longitude": 29.916,
                "description": "Under royal Ptolemaic patronage, seventy Hebrew scholars are summoned to the Pharos island. They perform the historic labor of translating the Hebrew Torah into Classical Greek, bridging Mediterranean theological divides for centuries.",
                "keyFigures": [
                    "Eleazar of Jerusalem (Priest)",
                    "Ptolemy II Philadelphus (Sovereign)",
                ],
                "dateFormatted": "C. 250 B.C.",
                "sources": [
                    {
                        "name": "Letter of Aristeas to Philocrates",
                        "url": "https://www.britannica.com/topic/Septuagint",
                    },
                    {
                        "name": "Alexandrian Judaic Archives",
                        "url": "https://www.worldhistory.org/Septuagint/",
                    },
                ],
                "causes": "A sizeable Greek-speaking Jewish diaspora inside Hellenistic Alexandria needed accessible theological texts in their colloquial tongue, alongside Ptolemy II Philadelphus's ambition to catalog all world knowledge in Greek.",
                "consequences": "This translation allowed Greek-speaking thinkers and early Christians to study Jewish scriptures, laying down theological pathways that shaped Hellenistic philosophy and Western theological discourse.",
                "location": "Pharos Scriptorium, Alexandria, Egypt",
            },
            {
                "title": "Eratosthenes' Shadow Calculation",
                "year": "-240",
                "latitude": 31.198,
                "longitude": 29.925,
                "description": "Reviewing ancient papyrus records in the Library, chief librarian Eratosthenes notices midday sun rays reach the bottom of Syene wells. By measuring Syene's solar angle versus Alexandria's, he computes the Earth's circumference with incredible precision.",
                "keyFigures": ["Eratosthenes of Cyrene (Chief Librarian)"],
                "dateFormatted": "C. 240 B.C.",
                "sources": [
                    {
                        "name": "On the Measurement of the Earth",
                        "url": "https://www.britannica.com/biography/Eratosthenes",
                    },
                    {
                        "name": "Greek Scriptorium Geometric Folio",
                        "url": "https://www.worldhistory.org/Eratosthenes/",
                    },
                ],
                "causes": "Eratosthenes wanted to map the known world scientifically, spurred by discrepancies in traditional cartographic logs and his unique geographical data retrieved from papyri in the Library of Alexandria.",
                "consequences": "He calculated the Earth's circumference to within a meager 1% of modern satellite measurements, pioneered scientific geography, and designed early grids of latitude and longitude.",
                "location": "The Great Library / Museum of Alexandria, Egypt",
            },
        ]

    if "runnymede" in normalized or "england" in normalized or "london" in normalized:
        return [
            {
                "title": "Gathering of the Army of God",
                "year": "1215",
                "latitude": 51.507,
                "longitude": -0.127,
                "description": "Disaffected barons assemble a formidable feudal force, renaming themselves 'The Army of God and Holy Church.' They capture London, forcing King John to agree to terms eventually presented at Runnymede.",
                "keyFigures": [
                    "Robert Fitzwalter (Baron General)",
                    "King John Lackland",
                ],
                "dateFormatted": "May 17, 1215 A.D.",
                "sources": [
                    {
                        "name": "Chronica Majora of Matthew Paris",
                        "url": "https://www.bl.uk/magna-carta",
                    },
                    {
                        "name": "medieval London Registry",
                        "url": "https://www.archives.gov/exhibits/featured-documents/magna-carta",
                    },
                ],
                "causes": "Baron dissatisfaction with King John's heavy-handed feudal exactions and failures to respect traditional baronial rights.",
                "consequences": "Forces the King's hand to begin direct negotiation, leading to the peace talks and eventual signing at Runnymede.",
                "location": "London, England",
            },
            {
                "title": "The Great Council of Westminster",
                "year": "1225",
                "latitude": 51.499,
                "longitude": -0.124,
                "description": "King Henry III reissues a scaled-down, refined Magna Carta in exchange for a new national tax on moveable properties. This establishes the historic precedent of 'grievance redressal before supply' in English law.",
                "keyFigures": [
                    "King Henry III of England",
                    "William Marshall (The Protector)",
                ],
                "dateFormatted": "February 11, 1225 A.D.",
                "sources": [
                    {
                        "name": "Westminster Abbey Scriptorium Archive",
                        "url": "https://www.bl.uk/magna-carta",
                    },
                    {
                        "name": "Statutes of the Realm Vol 1",
                        "url": "https://www.archives.gov/exhibits/featured-documents/magna-carta",
                    },
                ],
                "causes": "The Crown required significant funds to defend overseas Gascony lands, prompting them to reissue the charter as a goodwill gesture in return for tax approvals.",
                "consequences": "Locks the Great Charter permanently into English statutory law, establishing the precedent that public tax requires legal consent and concessions.",
                "location": "Westminster, London, England",
            },
            {
                "title": "Assembly of Simon de Montfort's Parliament",
                "year": "1265",
                "latitude": 51.503,
                "longitude": -0.129,
                "description": "For the first time in history, knight representatives of shires and burgesses of boroughs are summoned to Westminster. This radically expands the council, creating the conceptual blueprint for the modern House of Commons.",
                "keyFigures": [
                    "Simon de Montfort (Earl of Leicester)",
                    "Baron Council Representatives",
                ],
                "dateFormatted": "January 20, 1265 A.D.",
                "sources": [
                    {
                        "name": "Parliamentary Rolls of Henry III",
                        "url": "https://www.parliament.uk/about/living-heritage/evolutionofparliament/originsofparliament/birthofparliament/",
                    }
                ],
                "causes": "Simon de Montfort needed to broaden his political base during the Second Barons' War, seeking support from knights and commoners against the royalist factions.",
                "consequences": "Pioneered representation of commoners in Parliament, laying the foundation for bicameral legislative bodies globally.",
                "location": "Westminster, London, England",
            },
        ]

    if "mali" in normalized or "timbuktu" in normalized or "bamako" in normalized:
        return [
            {
                "title": "The Scriptorium Assembly of Sankore",
                "year": "1327",
                "latitude": 16.775,
                "longitude": -3.008,
                "description": "Commissioned under wealthy imperial funds, Timbuktu builds the Sankore University Madrasa. Over twenty thousand students study astrolabes, Islamic law, and Arabic literature.",
                "keyFigures": [
                    "Mansa Musa I (Emperor)",
                    "Abu Ishaq al-Sahili (Architect)",
                ],
                "dateFormatted": "C. 1327 A.D.",
                "sources": [
                    {
                        "name": "Chronicles of the Sudan (Tarikh al-Sudan)",
                        "url": "https://whc.unesco.org/en/list/119/",
                    },
                    {
                        "name": "Sankore Manuscript Collection",
                        "url": "https://www.loc.gov/exhibits/islamic/byz-tim.html",
                    },
                ],
                "causes": "Mansa Musa's historic Hajj inspired him to construct grand architectural and educational institutions in West Africa.",
                "consequences": "Establishes Timbuktu as a preeminent intellectual center in Africa, preserving thousands of manuscripts for centuries.",
                "location": "Sankore, Timbuktu, Mali",
            },
            {
                "title": "The Influx of Andalusian Scholars",
                "year": "1330",
                "latitude": 16.772,
                "longitude": -3.012,
                "description": "Mansa Musa recruits prominent scholars, physicians, and poets from Granada, Andalus. They translate countless medical and mathematical folios into West African dialects.",
                "keyFigures": ["Abu Ishaq al-Sahili (Granadan Poet)", "Mansa Musa I"],
                "dateFormatted": "C. 1330 A.D.",
                "sources": [
                    {
                        "name": "Ibn Battuta's Travelog",
                        "url": "https://www.nationalgeographic.org/encyclopedia/mansa-musa/",
                    }
                ],
                "causes": "Mansa Musa offered massive gold endowments to attract Andalusian intellectual elites to relocate and build institutions in Mali.",
                "consequences": "Bridges West African and Mediterranean academic traditions, leading to unique architectural and scientific synthesis.",
                "location": "Timbuktu, Mali",
            },
            {
                "title": "Ibn Battuta's Malian Visit",
                "year": "1352",
                "latitude": 12.639,
                "longitude": -8.002,
                "description": "The renowned Moroccan wanderer Ibn Battuta crosses the Sahara to visit the wealthy empire. He documents Malian judicial safety systems, absolute community cleanliness, and brilliant gold court pageantry.",
                "keyFigures": ["Ibn Battuta (Traveler)", "Mansa Souleyman (Emperor)"],
                "dateFormatted": "April 1352 A.D.",
                "sources": [
                    {
                        "name": "A Gift to those who Contemplate the Wonders of Cities",
                        "url": "https://orias.berkeley.edu/resources-teachers/travels-ibn-battuta",
                    }
                ],
                "causes": "Ibn Battuta's relentless travel curiosity drove him to explore the southern Islamic empires across the Sahara.",
                "consequences": "Produces the most comprehensive first-hand historical records of the Mali Empire's governance, safety, and trade patterns.",
                "location": "Bamako/Niani, Mali Empire",
            },
        ]

    epoch = (
        "Ancient Era"
        if year < 500
        else (
            "Medieval Era"
            if year < 1500
            else "Modern Era" if year < 1950 else "Contemporary Era"
        )
    )

    return [
        {
            "title": f"{epoch} Civic Expansion of {location_name}",
            "year": str(year),
            "latitude": selected_lat_jitter(year, 1),
            "longitude": selected_lng_jitter(year, 1),
            "description": f"At coordinates near {location_name}, this year witnessed a key expansion of regional architecture. Local craftsmen established central structures and codified regional trade rules.",
            "keyFigures": [f"Governor/Sovereign of {location_name}"],
            "dateFormatted": f"{abs(year)} B.C." if year < 0 else f"C. {year} A.D.",
            "sources": [
                {
                    "name": f"{location_name} Local Archives",
                    "url": "https://www.worldhistory.org/",
                },
                {
                    "name": f"Chronology of the {epoch}",
                    "url": "https://whc.unesco.org/",
                },
            ],
            "causes": "Socio-political stabilization and expansion of local trade routes in the region.",
            "consequences": "Establishes a permanent coordinate trade hub, paving the way for larger municipal growth.",
            "location": location_name,
        },
        {
            "title": "Cultural Interchange & Market Consecration",
            "year": str(year + 5),
            "latitude": selected_lat_jitter(year, 2),
            "longitude": selected_lng_jitter(year, 2),
            "description": f"A grand merchant and guild meeting is convened in the center of {location_name}. Exotic maritime and land goods are traded, laying down long-term community barter routes.",
            "keyFigures": ["Chief Guildmaster", "Scribes"],
            "dateFormatted": (
                f"{abs(year + 5)} B.C." if year < 0 else f"C. {year + 5} A.D."
            ),
            "sources": [
                {
                    "name": "International Trade Epigraphs",
                    "url": "https://www.britannica.com/",
                }
            ],
            "causes": "Expanding regional agricultural yields demanding external mercantile channels.",
            "consequences": "Drives cultural exchanges and imports of foreign tools, accelerating local technological transitions.",
            "location": location_name,
        },
        {
            "title": "The Great Celestial Alignment",
            "year": str(year - 3),
            "latitude": selected_lat_jitter(year, 3),
            "longitude": selected_lng_jitter(year, 3),
            "description": f"Local astrologers log a rare planetary conjunction above the horizon of {location_name}. The observations are carved on physical stone pillars, establishing local agricultural calendars.",
            "keyFigures": ["Principal Scribe Astronomer"],
            "dateFormatted": (
                f"{abs(year - 3)} B.C." if year < 0 else f"C. {year - 3} A.D."
            ),
            "sources": [
                {
                    "name": "Ancient Astronomic Astronomical Catalog",
                    "url": "https://history.nasa.gov/",
                }
            ],
            "causes": "Cyclical orbits of Jupiter and Saturn coinciding during a clear celestial season.",
            "consequences": "Improves farming yields by scheduling seed plantings according to stellar coordinates.",
            "location": location_name,
        },
    ]


def get_offline_sensory_fallback(
    location_name: str, era_name: str, target_date: str
) -> Dict[str, Any]:
    norm_loc = location_name.lower()

    if "alexandria" in norm_loc:
        return LOCAL_PRESETS_SENSORY["alexandria"]
    if "runnymede" in norm_loc or "england" in norm_loc:
        return LOCAL_PRESETS_SENSORY["feudal"]
    if "mali" in norm_loc or "timbuktu" in norm_loc:
        return LOCAL_PRESETS_SENSORY["musa"]
    if "canaveral" in norm_loc or "apollo" in norm_loc or "space" in norm_loc:
        return LOCAL_PRESETS_SENSORY["apollo"]

    descriptions = [
        f"The sharp aroma of burning cedar wood, sweet pine resin, and local herbs floats over {location_name} during the {era_name}. Ancient dirt pathways and custom chiseled stone buildings accommodate small assemblies of travelers wrapped in native woven robes. Scribes and local administrators write on tablets while the sound of copper hammers echoes from smithies.",
        f"A damp mist covers the active cobblestone yards of {location_name} in this period of {era_name}. Wool-clad merchants and leather guilds organize heavy oak carts carrying grains, dried fish, and salt. Deep bells ring out from a nearby chapel/mosque tower, their frequency drifting across thatched roofs where chimney smoke curls slowly into the sky.",
        f"Warm tropical air sweeps over {location_name} during the vibrant {era_name}. The spicy, earthy scent of active market stalls selling foreign materials matches the rhythm of traditional acoustic flutes. High in their wooden and stone ramparts, regional lookouts stand guard under waving flags of standard local dynasties.",
    ]

    random_idx = abs(hash_code(location_name)) % len(descriptions)

    return {
        "sensoryTitle": f"The Atmosphere of {location_name}",
        "sensoryDescription": f"{descriptions[random_idx]} (Simulated high-fidelity fallback at {target_date})",
        "keyFigures": [
            {
                "name": f"Chancellor of {location_name}",
                "role": "Chief Jurist",
                "bio": "Oversaw the local administrative and judicial records, integrating custom regional ordinances with wider empire charters.",
            },
            {
                "name": "Master Craftsman",
                "role": "Chief Architect",
                "bio": "Renowned local mason who designed the central arched water fountains and public libraries in this historic zone.",
            },
        ],
        "virtualEvents": [
            {
                "title": "Codifying the Guild Rules",
                "context": "Local merchant masters hold an assembly in the commons to freeze standard price thresholds.",
                "reference": f"{location_name} Scriptorium Record Leaf #12",
            },
            {
                "title": "The Sovereign Inspection Feast",
                "context": "High noble entourages arrive on horseback, inspecting local harvest and commissioning monumental civic architecture.",
                "reference": f"Imperial Annals Year {target_date}",
            },
        ],
        "ambientToneRate": {
            "description": "Atmospheric breeze, clinking bronze tools, and soft murmuring crowds",
            "frequency": "417 Hz",
        },
    }


def get_offline_forecast_fallback(
    location_name: str,
    era_name: str,
    target_date: str,
    forecast_topic: str,
    tech_level: str,
    societal_change: str,
    environmental_shift: str,
    time_horizon: str,
    custom_catalyst: Optional[str] = None,
    current_trends: Optional[str] = None,
    historical_event_types: Optional[str] = None,
) -> Dict[str, Any]:
    offset = (
        200
        if "Centenary" in time_horizon
        else 500 if "Far Future" in time_horizon else 100
    )
    base_year = 2026
    fut_year_1 = base_year + offset
    fut_year_2 = base_year + offset + 150

    tech_desc = (
        "high-density quantum computing grids, ambient electromagnetic propulsion, and transhuman molecular meshes"
        if tech_level == "Extreme"
        else (
            "automated robotic supply fleets, modular solar tiles, and holographic learning capsules"
            if tech_level == "High"
            else "reconstructed physical mechanical wheels, analog gears, and low-frequency electrical relay structures"
        )
    )

    society_desc = (
        "fully decentralized autonomous public guilds, consensus carbon agreements, and post-scarcity micro-states"
        if societal_change == "Radical"
        else (
            "regional communal parliaments, shared transport pools, and open-source civic libraries"
            if societal_change == "High"
            else "standard traditional representative councils and private family-owned trading blocks"
        )
    )

    climate_desc = (
        "flooded historic delta basins, climate-shielding atmospheric air domes, and reclaimed vertical mangrove wetlands"
        if environmental_shift in ["Extreme", "Severe"]
        else (
            "elevated coastal concrete breakwaters and automated rain catchment reservoirs"
            if environmental_shift == "Moderate"
            else "balanced organic farming meadows, stable river systems, and clean temperate air"
        )
    )

    catalyst_summary = (
        f" Fueled by the speculatively active catalyst of {custom_catalyst}, the trajectory is radically redirected towards novel system solutions."
        if custom_catalyst
        else ""
    )
    trends_text = (
        f" Undergoing contemporaneous present-day trends of {current_trends}, are projected to converge into potential futures."
        if current_trends
        else ""
    )

    base_result = {
        "historicalTrendSummary": f"The original institutional blueprints of {location_name} set in the {era_name} around {target_date} ripple direct into {time_horizon}. With {societal_change} societal pace toward {society_desc}, {tech_level} technology, and trends like {current_trends or 'sustainable transitions'}, the community potentially reinterprets ancestral laws into modern automated governance grids.{catalyst_summary}{trends_text}",
        "milestones": [
            {
                "year": f"{fut_year_1} AD",
                "title": f"Formalization of the {location_name} Unified Guilds",
                "description": f"Under the influence of {tech_level} technics, citizens establish decentralized smart guilds managing {forecast_topic} inside local regions.",
                "probability": 88 if tech_level == "Extreme" else 65,
                "outcomeType": "High-Probability Extrapolation",
            },
            {
                "year": f"{fut_year_2} AD",
                "title": "The Great Environmental Consensus Summit",
                "description": f"Adapting to {environmental_shift} climatic reality, automated biospheres are constructed in {location_name}, featuring deep carbon capturing systems.",
                "probability": (
                    74 if environmental_shift in ["Extreme", "Severe"] else 52
                ),
                "outcomeType": "Conditional Plausibility",
            },
        ],
        "projections": [
            {
                "milestoneYear": f"{fut_year_1 + 30} AD",
                "scenarioTitle": f"The {location_name} Biosphere Charter",
                "scenarioDetails": f"Implementing {tech_desc}, the city installs local sovereign control systems. Citizens participate via direct cryptographic voting, resolving conflicts through regional biospheric consensus.",
                "futureImpact": "Overall community resource transparency increases by over 60%, fully stabilizing the local eco-system.",
                "confidenceRating": "Plausible Scenario",
            },
            {
                "milestoneYear": f"{fut_year_2 + 40} AD",
                "scenarioTitle": "Resonance Convergence Project",
                "scenarioDetails": f"Under {climate_desc} conditions, local architectural styles shift completely to floating modular platforms. Public meetings take place in open geodesic amphitheaters.",
                "futureImpact": "Societal and industrial transition parameters settle into a stable, carbon-negative equilibrium.",
                "confidenceRating": "Wildcard Scenario Branch",
            },
        ],
    }

    metric_name = "Socio-Ecological Stability Metric"
    if "Information" in forecast_topic:
        metric_name = "Cognitive Infrastructure Integration"
    elif "Socio-Political" in forecast_topic:
        metric_name = "Decentralized Governance Index"
    elif "Biotechnics" in forecast_topic:
        metric_name = "Biospheric Symbiosis Index"

    multiplier = (
        1.35
        if tech_level == "Extreme"
        else 1.15 if tech_level == "High" else 0.8 if tech_level == "Low" else 1.0
    )
    environment_factor = (
        0.75
        if environmental_shift in ["Extreme", "Severe"]
        else 1.3 if environmental_shift in ["Eco-Techno", "Eco-Symbiosis"] else 1.0
    )

    base_val = 52
    trend_points = [
        {
            "yearOffset": 25,
            "low": int(max(10, base_val * 0.9 * multiplier * environment_factor)),
            "median": int(max(15, base_val * 1.05 * multiplier * environment_factor)),
            "high": int(min(100, base_val * 1.15 * multiplier * environment_factor)),
        },
        {
            "yearOffset": 50,
            "low": int(
                max(10, base_val * 0.8 * multiplier * multiplier * environment_factor)
            ),
            "median": int(
                max(20, base_val * 1.15 * multiplier * multiplier * environment_factor)
            ),
            "high": int(
                min(100, base_val * 1.35 * multiplier * multiplier * environment_factor)
            ),
        },
        {
            "yearOffset": 100,
            "low": int(max(5, base_val * 0.6 * (multiplier**3) * environment_factor)),
            "median": int(
                max(25, base_val * 1.3 * (multiplier**2) * environment_factor)
            ),
            "high": int(
                min(100, base_val * 1.65 * (multiplier**2) * environment_factor)
            ),
        },
        {
            "yearOffset": 250,
            "low": int(max(2, base_val * 0.4 * (multiplier**4) * environment_factor)),
            "median": int(
                max(30, base_val * 1.55 * (multiplier**3) * environment_factor)
            ),
            "high": int(
                min(100, base_val * 1.95 * (multiplier**3) * environment_factor)
            ),
        },
    ]

    for p in trend_points:
        if p["median"] > p["high"]:
            p["high"] = min(100, p["median"] + 10)
        if p["low"] > p["median"]:
            p["low"] = max(0, p["median"] - 10)

    return {
        **base_result,
        "trendPoints": trend_points,
        "confidenceIntervalInfo": {
            "metricName": metric_name,
            "explanation": f"Historical trend analysis extrapolates a long-term trajectory for user-selected parameters. Under {tech_level} technology and {environmental_shift} environmental conditions, the margin of variance (shaded interval) ranges from ±7% near-term to over ±25% over a 250-year speculative horizon.",
        },
    }


# ----------------------------------------------------------------------
# Helper Utilities
# ----------------------------------------------------------------------


def sanitize_json_string(raw: str) -> str:
    cleaned = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()
    return cleaned


# ----------------------------------------------------------------------
# FastAPI Route Handlers
# ----------------------------------------------------------------------


@router.post("/places")
async def handle_places(req: PlacesRequest):
    action = req.action

    if not action:
        raise HTTPException(status_code=400, detail="Missing action specifier")

    has_map_key = (
        bool(settings.google_maps_platform_key)
        and settings.google_maps_platform_key != "YOUR_API_KEY"
    )

    if action == "autocomplete":
        if not req.input or req.input.strip() == "":
            return {"predictions": []}

        query_lower = req.input.lower().strip()
        local_matches = [
            item
            for item in LOCAL_DATABASE
            if query_lower in item["description"].lower()
            or any(
                w in keyword
                for w in query_lower.split()
                for keyword in item["keywords"]
            )
        ]

        local_predictions = [
            {
                "description": match["description"],
                "place_id": f"local_place_{idx}_{re.sub(r'[^a-zA-Z0-9]', '_', match['description'])}",
                "isRealGoogle": False,
            }
            for idx, match in enumerate(local_matches[:5])
        ]

        if local_predictions:
            return {"predictions": local_predictions}

        if has_map_key:
            try:
                url = f"https://maps.googleapis.com/maps/api/place/autocomplete/json?input={quote(req.input)}&key={settings.google_maps_platform_key}"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.get(url)
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("status") in ["OK", "ZERO_RESULTS"]:
                            predictions = [
                                {
                                    "description": p["description"],
                                    "place_id": p["place_id"],
                                    "isRealGoogle": True,
                                }
                                for p in data.get("predictions", [])
                            ]
                            return {"predictions": predictions}
            except Exception as e:
                logger.error(f"Google Places API autocomplete error: {e}")

        # Fallback to Gemini
        try:
            gemini = get_llm_provider("gemini")
            config = LLMConfig(
                model="gemini-3.5-flash", response_mime_type="application/json"
            )
            prompt = (
                f"You are a geographic autocomplete search engine.\n"
                f'For the search input text: "{req.input}", return a list of exactly 5 real matching historical landmarks, ancient cities, or capitals in the world.\n'
                f"Provide a clear, human-readable full description/name for each (including city/country).\n"
                f"Return ONLY a valid JSON object matching this schema:\n"
                f"{{\n"
                f'  "predictions": [\n'
                f"    {{\n"
                f'      "description": "Short full name, e.g. Colosseum, Rome, Italy",\n'
                f'      "place_id": "gemini_place_colosseum_rome"\n'
                f"    }}\n"
                f"  ]\n"
                f"}}"
            )
            resp = await gemini.generate(prompt=prompt, config=config)
            cleaned = sanitize_json_string(resp.text)
            parsed = json.loads(cleaned)
            predictions = parsed.get("predictions", [])
            for p in predictions:
                p["isRealGoogle"] = False
            return {"predictions": predictions}
        except Exception as err:
            logger.warning(
                f"Gemini autocomplete failed or is rate-limited: {err}. Using local DB fallbacks."
            )
            fallback_list = (
                local_predictions
                if local_predictions
                else [
                    {
                        "description": m["description"],
                        "place_id": f"local_place_{i}_fallback",
                        "isRealGoogle": False,
                    }
                    for i, m in enumerate(LOCAL_DATABASE[:5])
                ]
            )
            return {"predictions": fallback_list}

    elif action == "details":
        place_id = req.place_id
        if not place_id:
            raise HTTPException(status_code=400, detail="Missing place_id")

        if place_id.startswith("local_place_"):
            desc = req.description or ""
            matched = next(
                (
                    item
                    for item in LOCAL_DATABASE
                    if item["description"].lower() == desc.lower()
                ),
                None,
            ) or next(
                (
                    item
                    for item in LOCAL_DATABASE
                    if desc.lower() in item["description"].lower()
                    or item["description"].lower() in desc.lower()
                ),
                None,
            )
            if matched:
                return {"lat": matched["lat"], "lng": matched["lng"]}

        if (
            has_map_key
            and not place_id.startswith("gemini_place_")
            and not place_id.startswith("local_place_")
        ):
            try:
                url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=geometry&key={settings.google_maps_platform_key}"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.get(url)
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("status") == "OK":
                            loc = (
                                data.get("result", {})
                                .get("geometry", {})
                                .get("location", {})
                            )
                            lat = loc.get("lat")
                            lng = loc.get("lng")
                            if lat is not None and lng is not None:
                                return {"lat": lat, "lng": lng}
            except Exception as e:
                logger.error(f"Google Places Details error: {e}")

        # Local lookup by description
        target_search = (req.description or place_id or "").lower().strip()
        matched_local = next(
            (
                item
                for item in LOCAL_DATABASE
                if target_search in item["description"].lower()
                or item["description"].lower() in target_search
            ),
            None,
        )
        if matched_local:
            return {"lat": matched_local["lat"], "lng": matched_local["lng"]}

        # Gemini lookup
        try:
            gemini = get_llm_provider("gemini")
            config = LLMConfig(
                model="gemini-3.5-flash", response_mime_type="application/json"
            )
            prompt = (
                f"You are a precise geographic coordinate lookup service.\n"
                f'For the place: "{req.description or place_id}", find its precise coordinate latitude and longitude.\n'
                f"Return ONLY a valid JSON object matching this schema:\n"
                f"{{\n"
                f'  "lat": number,\n'
                f'  "lng": number\n'
                f"}}"
            )
            resp = await gemini.generate(prompt=prompt, config=config)
            cleaned = sanitize_json_string(resp.text)
            parsed = json.loads(cleaned)
            return {"lat": float(parsed["lat"]), "lng": float(parsed["lng"])}
        except Exception as err:
            logger.warning(
                f"Gemini details coordinates resolution failed: {err}. Resolving via local DB approximation."
            )
            words = [w for w in re.split(r"[^a-zA-Z0-9]", target_search) if len(w) > 2]
            matched = next(
                (
                    item
                    for item in LOCAL_DATABASE
                    if any(
                        w in item["description"].lower() or w in item["keywords"]
                        for w in words
                    )
                ),
                LOCAL_DATABASE[0],
            )
            return {"lat": matched["lat"], "lng": matched["lng"]}

    raise HTTPException(status_code=400, detail="Unknown action")


@router.post("/time-travel")
async def handle_time_travel(req: TimeTravelRequest):
    action = req.action

    if not action:
        raise HTTPException(status_code=400, detail="Missing action specifier")

    if action == "suggest-pins":
        loc_name = req.locationName or ""
        year = req.year or 1215

        try:
            gemini = get_llm_provider("gemini")
            config = LLMConfig(
                model="gemini-3.5-flash", response_mime_type="application/json"
            )
            prompt = (
                f'You are a premier world historian AI. The user is exploring "{loc_name}" near the year {year}.\n'
                f"Find or simulate exactly 3 significant localized historical events that took place in this region or within this epoch.\n"
                f"For each event, specify:\n"
                f"1. Title\n"
                f'2. Precise year (e.g. "-44" for 44 BC, or "1492" for 1492 AD)\n'
                f"3. Approximate latitude and longitude within the same geographic region (e.g., if Europe, stay in Europe coordinates)\n"
                f"4. A highly detailed, engaging and accessible description of the event\n"
                f"5. A list of key historical figures involved (as strings)\n"
                f'6. A formatted date string (e.g. "March 15, 44 BC" or "October 12, 1492")\n'
                f'7. Links or names of exactly 2 key historical sources or academic media archives (e.g., "British Museum Archive", "Herodotus\' Histories", "The Smithsonian Chronology")\n'
                f"8. Causes: A detailed, engaging paragraph outlining the historical causes that led to this event\n"
                f"9. Consequences: A detailed, engaging paragraph describing the immediate and long-term consequences of this event\n"
                f'10. Location: A written description of the exact geographic location or context (e.g. "Sinaia, Prahova Valley, Romania" or "Bruchion District of Alexandria, Egypt")\n\n'
                f"Return ONLY a valid JSON array of objects matching this schema template:\n"
                f"[\n"
                f"  {{\n"
                f'    "title": "string",\n'
                f'    "year": "string",\n'
                f'    "latitude": number,\n'
                f'    "longitude": number,\n'
                f'    "description": "string",\n'
                f'    "keyFigures": ["string", "string"],\n'
                f'    "dateFormatted": "string",\n'
                f'    "sources": [\n'
                f'      {{ "name": "string", "url": "string" }},\n'
                f'      {{ "name": "string", "url": "string" }}\n'
                f"    ],\n"
                f'    "causes": "string",\n'
                f'    "consequences": "string",\n'
                f'    "location": "string"\n'
                f"  }}\n"
                f"]"
            )
            resp = await gemini.generate(prompt=prompt, config=config)
            cleaned = sanitize_json_string(resp.text)
            return JSONResponse(json.loads(cleaned))
        except Exception as err:
            logger.warning(
                f"Gemini suggest-pins failed: {err}. Using offline pins fallback."
            )
            return get_offline_pins_fallback(loc_name, year)

    elif action == "time-travel":
        loc_name = req.locationName or ""
        target_date = req.targetDate or "Present"
        era_name = req.eraName or ""

        try:
            gemini = get_llm_provider("gemini")
            config = LLMConfig(
                model="gemini-3.5-flash", response_mime_type="application/json"
            )
            prompt = (
                f"You are an immersive, highly engaging historical virtual reality algorithms simulator.\n"
                f"We are warping the user into a specific anchor:\n"
                f"- Location: {loc_name}\n"
                f"- Era: {era_name}\n"
                f"- Target Date: {target_date}\n\n"
                f"You must construct simulated sensory insight logs for this specific location-era coordinates:\n"
                f"1. sensoryTitle: A poetic, cinematic title summarizing the spirit of this era here.\n"
                f"2. sensoryDescription: A highly atmospheric narrative (4-5 lines) detailing the visual layout, smells, crowds, dress, and local architectural landscape. Make it feel highly immersive and accessible.\n"
                f"3. keyFigures: A list of 2-3 prominent historical individuals present or influential in this exact region & era. For each figure, provide their name, role/title, and a 1-sentence historical significance impact.\n"
                f"4. virtualEvents: exactly 2 distinct historical local occurrences, with a title, localized dynamic context, and a short reference resource index.\n"
                f'5. ambientToneRate: An interesting calculated ambient audio/tonal resonance parameter name (e.g. "Distant Iron Clanging & Market Chants") with a calculated frequency value like "432Hz".\n\n'
                f"Return ONLY a valid JSON object matching this schema template:\n"
                f"{{\n"
                f'  "sensoryTitle": "string",\n'
                f'  "sensoryDescription": "string",\n'
                f'  "keyFigures": [\n'
                f'    {{ "name": "string", "role": "string", "bio": "string" }}\n'
                f"  ],\n"
                f'  "virtualEvents": [\n'
                f'    {{ "title": "string", "context": "string", "reference": "string" }}\n'
                f"  ],\n"
                f'  "ambientToneRate": {{ "description": "string", "frequency": "string" }}\n'
                f"}}"
            )
            resp = await gemini.generate(prompt=prompt, config=config)
            cleaned = sanitize_json_string(resp.text)
            return JSONResponse(json.loads(cleaned))
        except Exception as err:
            logger.warning(
                f"Gemini time-travel failed: {err}. Using offline sensory fallback."
            )
            return get_offline_sensory_fallback(loc_name, era_name, target_date)

    elif action == "forecast":
        try:
            gemini = get_llm_provider("gemini")
            config = LLMConfig(
                model="gemini-3.5-flash", response_mime_type="application/json"
            )
            prompt = (
                f"You are a visionary Foresight AI Algorithm specializing in pluralistic, non-deterministic temporal mapping.\n"
                f"Extrapolate a plausible future state of society based on these historical anchor coordinates, event types, and present trends:\n"
                f'- Location: {req.locationName or "Unknown"}\n'
                f'- Base Historical Era Anchor: {req.eraName or "Unknown"} ({req.targetDate or "Unknown"})\n'
                f'- Analytical Historical Event Types To Synthesize: {req.historicalEventTypes or "War, Power, Religion, Commerce and Technics"}\n'
                f'- Forecasting Focus Sector: {req.forecastTopic or "Urban Architecture & Ecology"}\n'
                f'- Observed Present/Current Trends: {req.currentTrends or "Decentralization, AI integration, transition to clean energy"}\n\n'
                f"We are simulating a future trajectory customized by specific user-selected parameters:\n"
                f'- Technological Advancements Intensity: {req.techLevel or "Moderate"}\n'
                f'- Societal & Cultural Changes Pace: {req.societalChange or "Moderate Evolution"}\n'
                f'- Environmental & Climate Shifts Severity: {req.environmentalShift or "Stable"}\n'
                f'- Speculative Time Horizon Focus: {req.timeHorizon or "Immediate Centenary (100-300 yrs)"}\n'
                f'{(f"- Custom Speculative Driver/Catalyst: {req.customCatalyst}" if req.customCatalyst else "")}\n\n'
                f'CRITICAL REQUIREMENT: These forecasts must be structured and presented as "potential outcomes or plausible speculative branches" rather than definitive, absolute predictions of the future. Avoid deterministic language (e.g., use "could emerge", "hypothetically exhibits", "suggests a possible path" instead of "will", "shunts into", "shall", or "must").\n\n'
                f"Incorporate the observed present trends and selected parameters directly into the simulated future scenarios. For example:\n"
                f"- If Tech Intensity is Extreme, include far-future technics (quantum mesh networks, transhuman molecular interfaces).\n"
                f"- If Societal Change is Radical, emphasize decentralized, post-scarcity, or unusual local governance.\n"
                f"- If Environmental Shift is extreme or climate-burdened, forecast flooded landscape ruins, green dome habitats, or terraformed environments.\n"
                f"- Ensure the extrapolated years in the milestones reflect the chosen Speculative Time Horizon.\n\n"
                f"Generate:\n"
                f'1. A base trend cycle summary: A highly intelligent, professional analysis of how the historical patterns combine with currently observed trends, chosen event types, and user parameters to ripple forward into a SPECULATIVE FUTURE BRANCH (2-3 sentences). Frame this explicitly as a "hypothetical scenario trajectory".\n'
                f"2. exactly 2 speculative milestones (incorporating the speculatively selected parameters, with future year labels, an outcome type categorization, a detailed analytical description, and a realistic probability of occurrence under these specific assumptions).\n"
                f'3. exactly 2 futuristic projection scenarios containing a milestoneYear, a scenarioTitle, scenarioDetails implementing the parameters, a confidenceRating of the trajectory\'s volatility (e.g., "Highly Volatile", "Plausible Continuity", "Wildcard Shift"), and a futureImpact statement highlighting the societal effect index under those conditions.\n'
                f"4. exactly 4 trend points (trendPoints) from yearOffset = 25, 50, 100, to 250 years in the future. Construct a key indicator rating from 0 to 100 that fits the Sector Node Focus. For each offset, provide:\n"
                f"   - yearOffset: number\n"
                f"   - low: number (a cautious estimate, lower confidence bound)\n"
                f"   - median: number (the trend median path projection)\n"
                f"   - high: number (the high variance optimistic or extreme output bound)\n"
                f"   - Ensure (low < median < high) holds true. Make the difference between low and high (the confidence interval) widen over time (e.g. narrow gap at 25 yrs, but wide gap at 250 yrs to highlight speculative uncertainty).\n"
                f'5. confidenceIntervalInfo containing a metricName (the indicator title being projected, e.g. "Biospheric Symbiosis Index", "Decentralized Autonomy Index", "Cognitive Mesh Integration Index") and a short explanation string highlighting why the predictive variance spreads.\n\n'
                f"Return ONLY a valid JSON object matching this schema structural template:\n"
                f"{{\n"
                f'  "historicalTrendSummary": "string",\n'
                f'  "milestones": [\n'
                f'    {{ "year": "string", "title": "string", "description": "string", "probability": number, "outcomeType": "string" }}\n'
                f"  ],\n"
                f'  "projections": [\n'
                f'    {{ "milestoneYear": "string", "scenarioTitle": "string", "scenarioDetails": "string", "futureImpact": "string", "confidenceRating": "string" }}\n'
                f"  ],\n"
                f'  "trendPoints": [\n'
                f'    {{ "yearOffset": number, "low": number, "median": number, "high": number }}\n'
                f"  ],\n"
                f'  "confidenceIntervalInfo": {{\n'
                f'    "metricName": "string",\n'
                f'    "explanation": "string"\n'
                f"  }}\n"
                f"}}"
            )
            resp = await gemini.generate(prompt=prompt, config=config)
            cleaned = sanitize_json_string(resp.text)
            return JSONResponse(json.loads(cleaned))
        except Exception as err:
            logger.warning(
                f"Gemini forecast failed: {err}. Using offline forecast fallback."
            )
            return get_offline_forecast_fallback(
                req.locationName or "",
                req.eraName or "",
                req.targetDate or "Present",
                req.forecastTopic or "Urban Architecture & Ecology",
                req.techLevel or "Moderate",
                req.societalChange or "Moderate Evolution",
                req.environmentalShift or "Stable",
                req.timeHorizon or "Immediate Centenary (100-300 yrs)",
                req.customCatalyst,
                req.currentTrends,
                req.historicalEventTypes,
            )

    raise HTTPException(status_code=400, detail="Unknown action")
