"""
Day 5 - Exercise 1: Weather Dashboard API Client
"""

from typing import Optional
from pydantic import BaseModel, ValidationError

# ---------------------------------------------------------------------------
# Mock API data (provided)
# ---------------------------------------------------------------------------

MOCK_API_RESPONSES = {
    "Mumbai": {
        "city": "Mumbai",
        "region": "Maharashtra",
        "current": {
            "temp_c": 32.5,
            "condition": "Partly Cloudy",
            "humidity_pct": 78,
            "wind_kph": 14.2,
            "air_quality": {"pm2_5": 45.3},
        },
        "forecast": {
            "tomorrow": {
                "max_c": 34.0,
                "min_c": 27.5,
                "outlook": "Sunny",
            }
        },
    },
    "Chennai": {
        "city": "Chennai",
        "region": "Tamil Nadu",
        "current": {
            "temp_c": 35.0,
            "condition": "Hot and Humid",
            "humidity_pct": 82,
            "wind_kph": 10.5,
            "air_quality": {"pm2_5": 38.7},
        },
        "forecast": {
            "tomorrow": {
                "max_c": 36.5,
                "min_c": 29.0,
                "outlook": "Partly Cloudy",
            }
        },
    },
    "Bengaluru": {
        "city": "Bengaluru",
        "region": "Karnataka",
        "current": {
            "temp_c": 24.5,
            "condition": "Pleasant",
            "humidity_pct": 65,
            "wind_kph": 8.0,
            "air_quality": {"pm2_5": 22.1},
        },
        "forecast": {
            "tomorrow": {
                "max_c": 26.0,
                "min_c": 19.0,
                "outlook": "Mostly Sunny",
            }
        },
    },
    "Delhi": {
        "city": "Delhi",
        "region": "Delhi NCR",
        "current": {
            "temp_c": 38.0,
            "condition": "Hot",
            "humidity_pct": 40,
            "wind_kph": 12.0,
            "air_quality": {"pm2_5": 95.6},
        },
        "forecast": {
            "tomorrow": {
                "max_c": 40.0,
                "min_c": 30.0,
                "outlook": "Sunny and Hot",
            }
        },
    },
    "Hyderabad": {
        "city": "Hyderabad",
        "region": "Telangana",
        "current": {
            "temp_c": 30.0,
            "condition": "Clear",
            "humidity_pct": 55,
            "wind_kph": 11.5,
            "air_quality": {"pm2_5": 30.0},
        },
        "forecast": {
            "tomorrow": {
                "max_c": 32.0,
                "min_c": 24.0,
                "outlook": "Clear",
            }
        },
    },
}


def mock_get_weather(city: str) -> dict:
    """Simulates an API call; raises KeyError for unknown cities."""
    if city not in MOCK_API_RESPONSES:
        raise KeyError(f"City '{city}' not found in weather API")
    return MOCK_API_RESPONSES[city]


# ---------------------------------------------------------------------------
# Pydantic model
# ---------------------------------------------------------------------------


class DashboardWeatherRecord(BaseModel):
    city: str
    region: Optional[str] = None
    temp_c: float
    condition: str
    humidity_pct: int
    wind_kph: float
    pm2_5: Optional[float] = None
    tomorrow_max_c: Optional[float] = None
    tomorrow_min_c: Optional[float] = None
    tomorrow_outlook: Optional[str] = None


# ---------------------------------------------------------------------------
# Transform functions
# ---------------------------------------------------------------------------


def transform_weather_to_dashboard(raw: dict) -> DashboardWeatherRecord:
    """Flatten nested API response into a DashboardWeatherRecord."""
    current = raw.get("current", {})
    air_quality = current.get("air_quality", {})
    forecast = raw.get("forecast", {}).get("tomorrow", {})

    return DashboardWeatherRecord(
        city=raw["city"],
        region=raw.get("region"),
        temp_c=current["temp_c"],
        condition=current["condition"],
        humidity_pct=current["humidity_pct"],
        wind_kph=current["wind_kph"],
        pm2_5=air_quality.get("pm2_5"),
        tomorrow_max_c=forecast.get("max_c"),
        tomorrow_min_c=forecast.get("min_c"),
        tomorrow_outlook=forecast.get("outlook"),
    )


def build_dashboard_panel(cities: list[str]) -> list[DashboardWeatherRecord]:
    """Fetch and transform weather for each city; skip cities that fail."""
    records = []
    for city in cities:
        try:
            raw = mock_get_weather(city)
            record = transform_weather_to_dashboard(raw)
            records.append(record)
        except KeyError as exc:
            print(f"[WARNING] Could not fetch weather for {city}: {exc}")
        except ValidationError as exc:
            print(f"[WARNING] Data validation failed for {city}: {exc}")
    return records


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cities = ["Mumbai", "Chennai", "Bengaluru", "Delhi", "Hyderabad", "Pune"]
    panel = build_dashboard_panel(cities)

    print(f"\n{'='*55}")
    print(f"  WEATHER DASHBOARD  ({len(panel)} cities loaded)")
    print(f"{'='*55}")
    for rec in panel:
        print(f"\nCity       : {rec.city} ({rec.region})")
        print(f"Temp       : {rec.temp_c}°C  |  Condition: {rec.condition}")
        print(f"Humidity   : {rec.humidity_pct}%  |  Wind: {rec.wind_kph} kph")
        if rec.pm2_5 is not None:
            print(f"PM2.5      : {rec.pm2_5}")
        if rec.tomorrow_outlook:
            print(
                f"Tomorrow   : {rec.tomorrow_outlook} "
                f"({rec.tomorrow_min_c}°C – {rec.tomorrow_max_c}°C)"
            )
    print(f"\n{'='*55}\n")
