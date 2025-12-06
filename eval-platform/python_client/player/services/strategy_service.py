from player.models import KitClasses, RoundRequest

class StrategyService:
    def __init__(self, aircraft_map, logger):
        self.aircraft_map = aircraft_map
        self.logger = logger
        self.pending_loads = []

    def analyze_events(self, events):
        for event in events:
            if event.event_type == "CHECKED_IN":
                self._calculate_load(event)

    def apply_decisions(self, round_request):
        for load in self.pending_loads:
            round_request.flight_loads.append(load)
        
        # Clear local memory
        self.pending_loads.clear()

    def _calculate_load(self, event):
        ac_type = self.aircraft_map.get(event.aircraft_type)

        # LOGIC: Survival Mode (Load exactly what is needed)
        load_e = min(event.passengers.economy, ac_type.economy_capacity)
        load_b = min(event.passengers.business, ac_type.business_capacity)
        load_f = min(event.passengers.first, ac_type.first_capacity)
        load_p = min(event.passengers.premiumEconomy, ac_type.premium_capacity)

        kits = KitClasses(load_f, load_b, load_p, load_e)
        
        self.logger.info(f"-> [ORDERING] Flight {event.flight_number}: {kits}")
        
        # Store as the dictionary structure expected by RoundRequest
        self.pending_loads.append({
            "flightId": event.flight_id,
            "loadedKits": kits.to_dict()
        })