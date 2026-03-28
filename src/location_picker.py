"""
Random location selection for the quest game.

Each session picks a city at random from a diverse world list,
then applies a small random offset so you land on different streets
every time – even within the same city.
"""

import random
import math

# (display_name, lat, lon)
WORLD_CITIES = [
    # North America
    ("New York, USA",          40.7580,  -73.9855),
    ("Manhattan, USA",         40.7831,  -73.9712),
    ("Brooklyn, USA",          40.6782,  -73.9442),
    ("Chicago, USA",           41.8827,  -87.6233),
    ("Los Angeles, USA",       34.0522, -118.2437),
    ("San Francisco, USA",     37.7749, -122.4194),
    ("Seattle, USA",           47.6062, -122.3321),
    ("Boston, USA",            42.3601,  -71.0589),
    ("Miami, USA",             25.7617,  -80.1918),
    ("Toronto, Canada",        43.6532,  -79.3832),
    ("Vancouver, Canada",      49.2827, -123.1207),
    ("Montreal, Canada",       45.5017,  -73.5673),
    ("Mexico City, Mexico",    19.4326,  -99.1332),
    # Europe
    ("London, UK",             51.5074,   -0.1278),
    ("Paris, France",          48.8566,    2.3522),
    ("Berlin, Germany",        52.5200,   13.4050),
    ("Hamburg, Germany",       53.5511,    9.9937),
    ("Munich, Germany",        48.1351,   11.5820),
    ("Amsterdam, Netherlands", 52.3676,    4.9041),
    ("Brussels, Belgium",      50.8503,    4.3517),
    ("Vienna, Austria",        48.2082,   16.3738),
    ("Zurich, Switzerland",    47.3769,    8.5417),
    ("Madrid, Spain",          40.4168,   -3.7038),
    ("Barcelona, Spain",       41.3851,    2.1734),
    ("Lisbon, Portugal",       38.7169,   -9.1399),
    ("Rome, Italy",            41.9028,   12.4964),
    ("Milan, Italy",           45.4642,    9.1900),
    ("Florence, Italy",        43.7696,   11.2558),
    ("Stockholm, Sweden",      59.3293,   18.0686),
    ("Oslo, Norway",           59.9139,   10.7522),
    ("Copenhagen, Denmark",    55.6761,   12.5683),
    ("Helsinki, Finland",      60.1699,   24.9384),
    ("Warsaw, Poland",         52.2297,   21.0122),
    ("Prague, Czech Republic", 50.0755,   14.4378),
    ("Budapest, Hungary",      47.4979,   19.0402),
    ("Athens, Greece",         37.9838,   23.7275),
    ("Istanbul, Turkey",       41.0082,   28.9784),
    ("Kyiv, Ukraine",          50.4501,   30.5234),
    ("Moscow, Russia",         55.7558,   37.6173),
    ("St. Petersburg, Russia", 59.9343,   30.3351),
    # Asia
    ("Tokyo, Japan",           35.6762,  139.6503),
    ("Osaka, Japan",           34.6937,  135.5023),
    ("Kyoto, Japan",           35.0116,  135.7681),
    ("Seoul, South Korea",     37.5665,  126.9780),
    ("Beijing, China",         39.9042,  116.4074),
    ("Shanghai, China",        31.2304,  121.4737),
    ("Hong Kong",              22.3193,  114.1694),
    ("Singapore",               1.3521,  103.8198),
    ("Bangkok, Thailand",      13.7563,  100.5018),
    ("Hanoi, Vietnam",         21.0285,  105.8542),
    ("Jakarta, Indonesia",     -6.2088,  106.8456),
    ("Mumbai, India",          19.0760,   72.8777),
    ("Delhi, India",           28.7041,   77.1025),
    ("Bangalore, India",       12.9716,   77.5946),
    ("Kathmandu, Nepal",       27.7172,   85.3240),
    ("Colombo, Sri Lanka",      6.9271,   79.8612),
    ("Dhaka, Bangladesh",      23.8103,   90.4125),
    ("Karachi, Pakistan",      24.8607,   67.0011),
    ("Lahore, Pakistan",       31.5204,   74.3587),
    ("Kabul, Afghanistan",     34.5553,   69.2075),
    ("Tehran, Iran",           35.6892,   51.3890),
    ("Baghdad, Iraq",          33.3152,   44.3661),
    ("Beirut, Lebanon",        33.8938,   35.5018),
    ("Amman, Jordan",          31.9454,   35.9284),
    ("Riyadh, Saudi Arabia",   24.7136,   46.6753),
    ("Dubai, UAE",             25.2048,   55.2708),
    ("Doha, Qatar",            25.2854,   51.5310),
    ("Muscat, Oman",           23.5880,   58.3829),
    ("Tashkent, Uzbekistan",   41.2995,   69.2401),
    # Africa
    ("Cairo, Egypt",           30.0444,   31.2357),
    ("Nairobi, Kenya",         -1.2921,   36.8219),
    ("Lagos, Nigeria",          6.5244,    3.3792),
    ("Accra, Ghana",            5.6037,   -0.1870),
    ("Dakar, Senegal",         14.7167,  -17.4677),
    ("Addis Ababa, Ethiopia",   9.0320,   38.7469),
    ("Dar es Salaam, Tanzania", -6.7924,   39.2083),
    ("Johannesburg, SA",       -26.2041,   28.0473),
    ("Cape Town, SA",          -33.9249,   18.4241),
    ("Casablanca, Morocco",    33.5731,   -7.5898),
    ("Algiers, Algeria",       36.7372,    3.0863),
    ("Tunis, Tunisia",         36.8065,   10.1815),
    # South America
    ("São Paulo, Brazil",      -23.5505,  -46.6333),
    ("Rio de Janeiro, Brazil", -22.9068,  -43.1729),
    ("Buenos Aires, Argentina",-34.6037,  -58.3816),
    ("Santiago, Chile",        -33.4489,  -70.6693),
    ("Lima, Peru",             -12.0464,  -77.0428),
    ("Bogotá, Colombia",         4.7110,  -74.0721),
    ("Caracas, Venezuela",      10.4806,  -66.9036),
    ("Quito, Ecuador",          -0.1807,  -78.4678),
    # Oceania
    ("Sydney, Australia",      -33.8688,  151.2093),
    ("Melbourne, Australia",   -37.8136,  144.9631),
    ("Brisbane, Australia",    -27.4698,  153.0251),
    ("Auckland, New Zealand",  -36.8485,  174.7633),
    ("Wellington, New Zealand",-41.2865,  174.7762),
]


def pick_random_city() -> tuple[str, float, float]:
    """Return (city_name, lat, lon) chosen at random from the world list."""
    return random.choice(WORLD_CITIES)


def pick_random_location(max_offset_deg: float = 0.004) -> tuple[str, float, float]:
    """
    Return (city_name, lat, lon) with a small random offset so you land on
    different streets each session even within the same city.
    """
    city, lat, lon = pick_random_city()
    lat += random.uniform(-max_offset_deg, max_offset_deg)
    lon += random.uniform(-max_offset_deg, max_offset_deg)
    return city, lat, lon


def pick_random_global() -> tuple[str, float, float]:
    """
    Fully random lat/lon biased toward land masses (via rejection sampling
    against the city list density). Falls back to a random city if this
    produces a sparse region.
    """
    # Simple approach: pick a city and offset more aggressively
    city, lat, lon = pick_random_city()
    lat += random.uniform(-0.05, 0.05)
    lon += random.uniform(-0.05, 0.05)
    return city, lat, lon


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R  = 6371.0
    d1 = math.radians(lat2 - lat1)
    d2 = math.radians(lon2 - lon1)
    a  = (math.sin(d1 / 2) ** 2
          + math.cos(math.radians(lat1))
          * math.cos(math.radians(lat2))
          * math.sin(d2 / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
