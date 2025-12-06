import json

class KitClasses:
    def __init__(self, first=0, business=0, premium=0, economy=0):
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

class Airport:
    def __init__(self, code, 
                 stock_f, stock_b, stock_p, stock_e,
                 cap_f, cap_b, cap_p, cap_e,
                 proc_f, proc_b, proc_p, proc_e):
        self.code = code
        
        # Stocks
        self.stock_first = stock_f
        self.stock_business = stock_b
        self.stock_premium = stock_p
        self.stock_economy = stock_e
        
        # Capacities
        self.capacity_first = cap_f
        self.capacity_business = cap_b
        self.capacity_premium = cap_p
        self.capacity_economy = cap_e
        
        # Processing Times
        self.proc_time_first = proc_f
        self.proc_time_business = proc_b
        self.proc_time_premium = proc_p
        self.proc_time_economy = proc_e

    def __str__(self):
        return f"{self.code} [Eco Stock: {self.stock_economy}/{self.capacity_economy}]"

class FlightInstance:
    def __init__(self, flight_id, flight_number, origin_id, dest_id, dep_day, dep_hour, arr_day, arr_hour):
        self.id = flight_id
        self.number = flight_number
        self.origin_id = origin_id
        self.destination_id = dest_id
        self.departure_day = dep_day
        self.departure_hour = dep_hour
        self.arrival_day = arr_day
        self.arrival_hour = arr_hour

class FlightSchedule:
    def __init__(self, origin, destination, hour, distance):
        self.origin = origin
        self.destination = destination
        self.hour = hour
        self.distance = distance

class FlightEvent:
    def __init__(self, data):
        self.event_type = data.get("eventType")
        self.flight_number = data.get("flightNumber")
        self.flight_id = data.get("flightId")
        self.aircraft_type = data.get("aircraftType")
        self.departure_time = data.get("departureTime")
        self.arrival_time = data.get("arrivalTime")
        self.distance = data.get("distance", 0)
        self.source_airport = data.get("sourceAirportCode")
        self.dest_airport = data.get("destinationAirportCode")
        
        pass_data = data.get("passengers", {})
        self.passengers = KitClasses(pass_data.get("first", 0), pass_data.get("business", 0), pass_data.get("premiumEconomy", 0), pass_data.get("economy", 0))

class RoundRequest:
    def __init__(self, day, hour):
        self.day = day
        self.hour = hour
        self.flight_loads = [] 
    def add_load(self, flight_id, kit_classes):
        self.flight_loads.append({"flightId": flight_id, "loadedKits": kit_classes.to_dict()})
    def to_dict(self):
        return {
            "day": self.day,
            "hour": self.hour,
            "flightLoads": self.flight_loads,
            "purchasingOrders": getattr(self, 'purchasing_orders', [])
        }
    
    def add_purchase(self, kit_type, quantity):
        """Add a purchasing order"""
        if not hasattr(self, 'purchasing_orders'):
            self.purchasing_orders = []
        self.purchasing_orders.append({
            "kitType": kit_type,
            "quantity": quantity
        })

class RoundResponse:
    def __init__(self, data):
        self.day = data.get("day")
        self.hour = data.get("hour")
        self.total_cost = data.get("totalCost", 0.0)
        self.flight_updates = [FlightEvent(e) for e in data.get("flightUpdates", [])]
        self.status = data.get("status", "RUNNING")


class Airport:
    """Represents an airport with kit storage and processing capabilities"""
    def __init__(self, code, name, hub=False):
        self.code = code
        self.name = name
        self.hub = hub
        self.storage_capacity = {}  # {kit_type: capacity}
        self.loading_cost = {}  # {kit_type: cost}
        self.processing_cost = {}  # {kit_type: cost}
        self.processing_time = {}  # {kit_type: hours}
        self.initial_stock = {}  # {kit_type: quantity}


class FlightSchedule:
    """Represents a scheduled flight route"""
    def __init__(self, flight_number, source, dest, frequency, departure_hour):
        self.flight_number = flight_number
        self.source = source
        self.dest = dest
        self.frequency = frequency  # Days of week: "1,2,3,4,5" etc
        self.departure_hour = departure_hour


class KitType:
    """Kit type constants and properties"""
    FIRST = "FIRST"
    BUSINESS = "BUSINESS"
    PREMIUM_ECONOMY = "PREMIUM_ECONOMY"
    ECONOMY = "ECONOMY"
    
    ALL_TYPES = [FIRST, BUSINESS, PREMIUM_ECONOMY, ECONOMY]
    
    # Kit properties (from problem description)
    COSTS = {
        FIRST: 50,
        BUSINESS: 30,
        PREMIUM_ECONOMY: 20,
        ECONOMY: 10
    }
    
    WEIGHTS = {
        FIRST: 2.0,
        BUSINESS: 1.5,
        PREMIUM_ECONOMY: 1.0,
        ECONOMY: 0.5
    }
    
    LEAD_TIMES = {
        FIRST: 48,
        BUSINESS: 48,
        PREMIUM_ECONOMY: 24,
        ECONOMY: 24
    }