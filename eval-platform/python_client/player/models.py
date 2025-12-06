import json

class KitClasses:
    def __init__(self, first=0, business=0, premium=0, economy=0):
        # We use the JSON names directly here to simplify serialization
        self.first = first
        self.business = business
        self.premiumEconomy = premium
        self.economy = economy

    def to_dict(self):
        return {
            "first": self.first,
            "business": self.business,
            "premiumEconomy": self.premiumEconomy,
            "economy": self.economy
        }

    def __str__(self):
        return f"[F:{self.first} B:{self.business} P:{self.premiumEconomy} E:{self.economy}]"

class AircraftType:
    def __init__(self, type_code, cap_f, cap_b, cap_p, cap_e):
        self.type_code = type_code
        self.first_capacity = cap_f
        self.business_capacity = cap_b
        self.premium_capacity = cap_p
        self.economy_capacity = cap_e

class FlightEvent:
    def __init__(self, data):
        self.event_type = data.get("eventType")
        self.flight_number = data.get("flightNumber")
        self.flight_id = data.get("flightId")
        self.aircraft_type = data.get("aircraftType")
        
        pass_data = data.get("passengers", {})
        self.passengers = KitClasses(
            pass_data.get("first", 0),
            pass_data.get("business", 0),
            pass_data.get("premiumEconomy", 0),
            pass_data.get("economy", 0)
        )

class RoundRequest:
    def __init__(self, day, hour):
        self.day = day
        self.hour = hour
        self.flight_loads = [] # List of dicts

    def add_load(self, flight_id, kit_classes):
        self.flight_loads.append({
            "flightId": flight_id,
            "loadedKits": kit_classes.to_dict()
        })

    def to_dict(self):
        return {
            "day": self.day,
            "hour": self.hour,
            "flightLoads": self.flight_loads
            # "kitPurchases": [] # Add later when needed
        }

class RoundResponse:
    def __init__(self, data):
        self.day = data.get("day")
        self.hour = data.get("hour")
        self.total_cost = data.get("totalCost", 0.0)
        self.flight_updates = [FlightEvent(e) for e in data.get("flightUpdates", [])]