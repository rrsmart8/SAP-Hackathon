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
    """Represents an airport with kit storage and processing capabilities"""
    def __init__(self, code, name=None, hub=False, 
                 stock_f=None, stock_b=None, stock_p=None, stock_e=None,
                 cap_f=None, cap_b=None, cap_p=None, cap_e=None,
                 proc_f=None, proc_b=None, proc_p=None, proc_e=None):
        self.code = code
        self.name = name or code
        self.hub = hub
        
        # Initialize dictionaries for network flow strategy
        self.storage_capacity = {}
        self.loading_cost = {}
        self.processing_cost = {}
        self.processing_time = {}
        self.initial_stock = {}
        
        # If CSV data provided, populate dictionaries
        if stock_f is not None:
            # CSV format: populate from individual values
            # Use string literals since KitType is defined later
            self.initial_stock = {
                "FIRST": stock_f or 0,
                "BUSINESS": stock_b or 0,
                "PREMIUM_ECONOMY": stock_p or 0,
                "ECONOMY": stock_e or 0
            }
            self.storage_capacity = {
                "FIRST": cap_f or 1000,
                "BUSINESS": cap_b or 1000,
                "PREMIUM_ECONOMY": cap_p or 1000,
                "ECONOMY": cap_e or 1000
            }
            self.processing_time = {
                "FIRST": proc_f or 2,
                "BUSINESS": proc_b or 2,
                "PREMIUM_ECONOMY": proc_p or 2,
                "ECONOMY": proc_e or 2
            }
            # Default costs
            self.loading_cost = {
                "FIRST": 5,
                "BUSINESS": 5,
                "PREMIUM_ECONOMY": 5,
                "ECONOMY": 5
            }
            self.processing_cost = {
                "FIRST": 10,
                "BUSINESS": 10,
                "PREMIUM_ECONOMY": 10,
                "ECONOMY": 10
            }
        
        # Legacy attributes for backward compatibility
        self.stock_first = self.initial_stock.get("FIRST", 0)
        self.stock_business = self.initial_stock.get("BUSINESS", 0)
        self.stock_premium = self.initial_stock.get("PREMIUM_ECONOMY", 0)
        self.stock_economy = self.initial_stock.get("ECONOMY", 0)
        self.capacity_first = self.storage_capacity.get("FIRST", 1000)
        self.capacity_business = self.storage_capacity.get("BUSINESS", 1000)
        self.capacity_premium = self.storage_capacity.get("PREMIUM_ECONOMY", 1000)
        self.capacity_economy = self.storage_capacity.get("ECONOMY", 1000)
        self.proc_time_first = self.processing_time.get("FIRST", 2)
        self.proc_time_business = self.processing_time.get("BUSINESS", 2)
        self.proc_time_premium = self.processing_time.get("PREMIUM_ECONOMY", 2)
        self.proc_time_economy = self.processing_time.get("ECONOMY", 2)

    def __str__(self):
        return f"{self.code} [Eco Stock: {self.stock_economy}/{self.capacity_economy}]"

class FlightInstance:
    def __init__(self, id, flight_number, origin_airport_id, destination_airport_id,
                 scheduled_depart_day, scheduled_depart_hour,
                 scheduled_arrival_day, scheduled_arrival_hour):
        self.id = id
        self.flight_number = flight_number
        self.origin_airport_id = origin_airport_id
        self.destination_airport_id = destination_airport_id
        self.scheduled_depart_day = int(scheduled_depart_day)
        self.scheduled_depart_hour = int(scheduled_depart_hour)
        self.scheduled_arrival_day = int(scheduled_arrival_day)
        self.scheduled_arrival_hour = int(scheduled_arrival_hour)

class Penalty:
    def __init__(self, data):
        self.code = data.get("code")
        self.flight_id = data.get("flightId")
        self.flight_number = data.get("flightNumber")
        self.issued_day = data.get("issuedDay")
        self.issued_hour = data.get("issuedHour")
        self.amount = data.get("penalty", 0.0) # Suma banilor pierduți
        self.reason = data.get("reason")

    def __str__(self):
        # Formatare frumoasă pentru loguri
        return f"[PENALTY] {self.code} (-{self.amount:.2f}): {self.reason} (Flight: {self.flight_number})"

class FlightEvent:
    def __init__(self, data):
        self.event_type = data.get("eventType")
        self.flight_number = data.get("flightNumber")
        self.flight_id = data.get("flightId")
        self.aircraft_type = data.get("aircraftType")
        self.distance = data.get("distance", 0)
        self.source_airport = data.get("originAirport")
        self.dest_airport = data.get("destinationAirport")
        
        # Parse departure time (object with day and hour fields)
        dep_data = data.get("departure", {})
        self.departure_day = dep_data.get("day")
        self.departure_hour = dep_data.get("hour")
        self.departure_absolute_hour = None
        if self.departure_day is not None and self.departure_hour is not None:
            self.departure_absolute_hour = self.departure_day * 24 + self.departure_hour
        
        # Parse arrival time (object with day and hour fields)
        arr_data = data.get("arrival", {})
        self.arrival_day = arr_data.get("day")
        self.arrival_hour = arr_data.get("hour")
        self.arrival_absolute_hour = None
        if self.arrival_day is not None and self.arrival_hour is not None:
            self.arrival_absolute_hour = self.arrival_day * 24 + self.arrival_hour
        
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
        self.penalties = [Penalty(p) for p in data.get("penalties", [])]


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