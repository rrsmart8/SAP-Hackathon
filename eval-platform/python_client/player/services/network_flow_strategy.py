from player.models import KitClasses
from .graph import TimeExpandedGraph
from .solver import MinCostFlowSolver, GreedySolver

class NetworkFlowStrategy:
    """
    Time-expanded network flow optimization strategy
    """
    
    def __init__(self, aircraft_map, airports, flight_schedule, logger, planning_horizon=72):
        self.aircraft_map = aircraft_map
        self.airports = airports
        self.flight_schedule = flight_schedule
        self.logger = logger
        self.planning_horizon = planning_horizon
        
        # State tracking
        self.inventory = {}  # {(airport, kit_type): quantity}
        self.flights_info = {}  # {flight_id: flight_data}
        self.current_day = 0
        self.current_hour = 0
        self.pending_decisions = {'flightLoads': [], 'purchasingOrders': []}

        self.kit_types = ['FIRST', 'BUSINESS', 'PREMIUM_ECONOMY', 'ECONOMY']
        
        self.flight_events_map = {}  # {flight_id: FlightEvent}

        # Initialize inventory from airport initial stocks
        self._initialize_inventory()

       
    def _initialize_inventory(self):
        """Initialize inventory from airport initial stocks"""
        for airport_code, airport in self.airports.items():
            for kit_type in self.kit_types:

                if kit_type == 'FIRST':
                    key = (airport_code, kit_type)
                    self.inventory[key] = airport.stock_first
                if kit_type == 'BUSINESS':
                    key = (airport_code, kit_type)
                    self.inventory[key] = airport.stock_business
                if kit_type == 'PREMIUM_ECONOMY':
                    key = (airport_code, kit_type)
                    self.inventory[key] = airport.stock_premium
                if kit_type == 'ECONOMY':
                    key = (airport_code, kit_type)
                    self.inventory[key] = airport.stock_economy

    def apply_decisions(self, round_request):
        """Apply pending decisions to round request"""
        round_request.flight_loads = self.pending_decisions.get('flightLoads', [])
        
        # Add purchasing orders
        for purchase in self.pending_decisions.get('purchasingOrders', []):
            round_request.add_purchase(purchase['kitType'], purchase['quantity'])
        
        self.logger.info(f"Applied {len(round_request.flight_loads)} flight loads, "
                        f"{len(self.pending_decisions.get('purchasingOrders', []))} purchases")

    
    def get_flights_in_horizon(self, current_hour, end_hour):
        """Get all flights scheduled within the planning horizon"""
        flights_in_horizon = []
        
        for flight in self.flight_schedule:
            dep_hour = self._get_absolute_hour(flight.scheduled_depart_day, flight.scheduled_depart_hour)
            if current_hour <= dep_hour < end_hour:
                flights_in_horizon.append(flight)
        
        return flights_in_horizon
    
    def _get_absolute_hour(self, day, hour):
        """Convert day and hour to absolute hour"""
        return day * 24 + hour
    
    def process_flight_updates(self, flight_events):
        """Process flight events to update internal flight info"""
        for event in flight_events:
            # Store the event object directly
            self.flight_events_map[event.flight_id] = event

    def build_network(self, current_hour):
        """Build time-expanded network for optimization"""
        
        graph = TimeExpandedGraph(self.planning_horizon)
        
        # A. Add initial inventory edges
        for (airport, kit_type), quantity in self.inventory.items():
            if quantity > 0:
                graph.add_initial_inventory_edge(airport, kit_type, quantity)
        
        # B. Add storage edges (kits staying at airport)
        for t in range(self.planning_horizon - 1):
            for airport_code, airport in self.airports.items():
                for kit_type in self.kit_types:
                    if kit_type == 'FIRST':
                        capacity = airport.capacity_first
                        graph.add_storage_edge(airport_code, t, 'FIRST', capacity, storage_cost=0)
                    if kit_type == 'BUSINESS':
                        capacity = airport.capacity_business
                        graph.add_storage_edge(airport_code, t, 'BUSINESS', capacity, storage_cost=0)
                    if kit_type == 'PREMIUM_ECONOMY':
                        capacity = airport.capacity_premium
                        graph.add_storage_edge(airport_code, t, 'PREMIUM_ECONOMY', capacity, storage_cost=0)
                    if kit_type == 'ECONOMY':
                        capacity = airport.capacity_economy
                        graph.add_storage_edge(airport_code, t, 'ECONOMY', capacity, storage_cost=0)

        
        # C. Add flight edges and processing edges
        current_absolute_hour = self.current_day * 24 + self.current_hour
        upcoming_flights = self.get_flights_in_horizon(current_absolute_hour, current_absolute_hour + self.planning_horizon)
        
        for flight in upcoming_flights:
            
            # Calculate relative time from current hour
            dep_time = self._get_absolute_hour(flight.scheduled_depart_day, flight.scheduled_depart_hour)
            arr_time = self._get_absolute_hour(flight.scheduled_arrival_day, flight.scheduled_arrival_hour)
            
            for kit_type in self.kit_types:
                # Calculate cost
                source_airport = self.airports.get(flight.origin_airport_id)
                dest_airport = self.airports.get(flight.destination_airport_id)
                
                if not source_airport or not dest_airport:
                    # self.logger.info(f"Skipping flight {flight.id} due to missing airport data")
                    continue
                
                # --- MODIFICARE 1: Setare Greutate (Weight) Manual ---
                weight = 0
                if kit_type == 'FIRST': weight = 0.5  # Ajusteaza valorile daca e necesar
                elif kit_type == 'BUSINESS': weight = 0.4
                elif kit_type == 'PREMIUM_ECONOMY': weight = 0.3
                elif kit_type == 'ECONOMY': weight = 0.2

                # --- MODIFICARE 2: Costuri procesare ---
                # Aici folosim get() standard, e ok
                loading_cost = source_airport.loading_cost.get(kit_type, 5) if hasattr(source_airport, 'loading_cost') else 5
                processing_cost = dest_airport.processing_cost.get(kit_type, 10) if hasattr(dest_airport, 'processing_cost') else 10
                
                fuel_cost = flight['distance'] * flight['fuel_cost_per_km'] * weight
                
                total_cost = loading_cost + fuel_cost + processing_cost
                
                # Capacity
                aircraft = self.aircraft_map.get(flight['aircraft'])
                if not aircraft:
                    continue
                
                capacity = 0
                if kit_type == 'FIRST':
                    capacity = aircraft.first_capacity
                elif kit_type == 'BUSINESS':
                    capacity = aircraft.business_capacity
                elif kit_type == 'PREMIUM_ECONOMY':
                    capacity = aircraft.premium_capacity
                elif kit_type == 'ECONOMY':
                    capacity = aircraft.economy_capacity
                
                # Add flight edge
                graph.add_flight_edge(
                    flight['id'],
                    flight['source'],
                    flight['dest'],
                    dep_time,
                    arr_time,
                    kit_type,
                    capacity,
                    total_cost
                )
                
                # Add processing edge at destination
                # --- MODIFICARE: Verificare timp procesare ---
                processing_time = 2 # Default
                if hasattr(dest_airport, 'processing_time'):
                    processing_time = dest_airport.processing_time.get(kit_type, 2)
                
                graph.add_processing_edge(
                    flight['dest'],
                    arr_time,
                    processing_time,
                    kit_type
                )
        
        # D. Add demand edges (penalty for not meeting requirements)
        for flight in upcoming_flights:
            dep_time = self._get_absolute_hour(flight.scheduled_depart_day, flight.scheduled_depart_hour)
            
            if dep_time < 0:
                continue

            flight_event = self.flight_events_map.get(flight.id)
            if not flight_event:
                continue
            
            # --- MODIFICARE 3: Iteram prin self.kit_types in loc de KitType.ALL_TYPES ---
            for kit_type in self.kit_types:
                required = 0
                if kit_type == 'FIRST':
                    required = flight_event.passengers.first
                elif kit_type == 'BUSINESS':
                    required = flight_event.passengers.business
                elif kit_type == 'PREMIUM_ECONOMY':
                    required = flight_event.passengers.premiumEconomy
                elif kit_type == 'ECONOMY':
                    required = flight_event.passengers.economy
                
                if required > 0:
                    # --- MODIFICARE 4: Setare Cost Kit Manual ---
                    kit_cost = 0
                    if kit_type == 'FIRST': kit_cost = 80
                    elif kit_type == 'BUSINESS': kit_cost = 40
                    elif kit_type == 'PREMIUM_ECONOMY': kit_cost = 20
                    elif kit_type == 'ECONOMY': kit_cost = 10

                    distance = flight_event.distance if flight_event.distance else 1000
                    penalty = distance * kit_cost * 10  # UNFULFILLED_PASSENGERS_FACTOR
                    
                    graph.add_demand_edge(
                        flight.id,
                        flight.origin_airport_id,  # Use attribute not dict access
                        dep_time,
                        kit_type,
                        required,
                        penalty
                    )
        
        # E. Add purchase edges
        # --- MODIFICARE 5: Iteram prin self.kit_types si setam valorile manual ---
        for kit_type in self.kit_types:
            
            lead_time = 0
            cost = 0
            
            if kit_type == 'FIRST':
                lead_time = 48 # Exemplu: 2 zile
                cost = 80
            elif kit_type == 'BUSINESS':
                lead_time = 24 # Exemplu: 1 zi
                cost = 40
            elif kit_type == 'PREMIUM_ECONOMY':
                lead_time = 12
                cost = 20
            elif kit_type == 'ECONOMY':
                lead_time = 6
                cost = 10
            
            # Can order now, arrives at lead_time
            if lead_time < self.planning_horizon:
                graph.add_purchase_edge(
                    kit_type,
                    0,
                    lead_time,
                    quantity=1000,  # Max you can order
                    cost=cost
                )
        
        return graph
    
    def solve_optimization(self, graph):
        """Solve the min-cost flow problem"""
        try:
            # Try OR-Tools solver first
            solver = MinCostFlowSolver(graph)
            solution = solver.solve(time_limit_seconds=30, verbose=False)
        except ImportError:
            # Fallback to greedy solver
            self.logger.info("OR-Tools not available, using greedy solver")
            solver = GreedySolver(graph)
            solution = solver.solve(verbose=False)
        
        return solution
    
    def extract_immediate_decisions(self, solution, current_hour):
        """Extract only decisions that need to be made NOW"""
        loads = {}
        purchases = {}
        current_absolute_hour = self.current_day * 24 + self.current_hour
        
        # 1. Extract flight loads for flights departing THIS HOUR
        if solution.kit_loads:
            for flight_id, kits in solution.kit_loads.items():
                flight = self.flights_info.get(flight_id)
                if flight and (flight['scheduled_departure_day'] * 24 + flight['scheduled_departure_hour'] == current_absolute_hour):
                    loads[flight_id] = kits
                    loads[flight_id] = kits
        
        # 2. Extract purchases
        for edge, flow_value in solution.flow:
            if edge.edge_type == 'purchase':
                kit_type = edge.metadata['kit']
                quantity = int(round(flow_value))
                if quantity > 0:
                    purchases[kit_type] = purchases.get(kit_type, 0) + quantity
        
        return {
            'flight_loads': loads,
            'purchases': purchases
        }
    
    def format_api_request(self, decisions):
        """Format decisions for the /play endpoint"""
        flight_loads = []
        
        for flight_id, kits in decisions['flight_loads'].items():
            flight_loads.append({
                'flightId': flight_id,
                'loadedKits': {
                    'FIRST': int(kits.get('FIRST', 0)),
                    'BUSINESS': int(kits.get('BUSINESS', 0)),
                    'PREMIUM_ECONOMY': int(kits.get('PREMIUM_ECONOMY', 0)),
                    'ECONOMY': int(kits.get('ECONOMY', 0))
                }
            })
        
        purchase_orders = []
        for kit_type, quantity in decisions['purchases'].items():
            if quantity > 0:
                purchase_orders.append({
                    'kitType': kit_type,
                    'quantity': int(quantity)
                })
        
        return {
            'flightLoads': flight_loads,
            'purchasingOrders': purchase_orders
        }
    
    def analyze_and_plan(self, flight_events, current_day, current_hour):
        """
        Main optimization method
        Analyzes events, builds network, solves, and prepares decisions
        """
        self.current_day = current_day
        self.current_hour = current_hour
        current_absolute_hour = current_day * 24 + current_hour
        
        # Process flight updates
        self.process_flight_updates(flight_events)
        
        # Debug: Check what flights we have
        total_flights = len(self.flights_info)
        flights_with_departure = sum(1 for f in self.flights_info.values() if 'departure_hour' in f)
        
        # Build network
        self.logger.info(f"Building network for day {current_day}, hour {current_hour} (absolute: {current_absolute_hour})")
        self.logger.info(f"Total flights tracked: {total_flights}, with departure times: {flights_with_departure}")
        
        graph = self.build_network(current_hour)
        
        stats = graph.get_stats()
        self.logger.info(f"Network built: {stats}")
        
        # Debug: If no flights found, log details
        if stats['edge_types'].get('flight', 0) == 0:
            self.logger.info(f"Debugging: Looking for flights in horizon [{current_absolute_hour}, {current_absolute_hour + self.planning_horizon})")
            
            # Sample some flights to debug
            sample_size = min(5, len(self.flights_info))
            self.logger.info(f"Sample of tracked flights (first {sample_size}):")
            for i, (fid, f) in enumerate(list(self.flights_info.items())[:sample_size]):
                dep_hour = f.get('departure_hour', 'None')
                self.logger.info(f"  {f.get('number', fid)}: dep_hour={dep_hour}, source={f.get('source')}, dest={f.get('dest')}")
        
        # Solve optimization
        self.logger.info("Solving optimization...")
        solution = self.solve_optimization(graph)
        
        self.logger.info(f"Solution status: {solution.status}, cost: {solution.total_cost}")
        
        # Extract immediate decisions
        decisions = self.extract_immediate_decisions(solution, current_hour)
        
        # Format for API
        self.pending_decisions = self.format_api_request(decisions)
        
        return self.pending_decisions    