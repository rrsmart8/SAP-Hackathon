"""
Network Flow Strategy Service for Kit Optimization
Uses time-expanded network and min-cost flow solver
"""

import sys
import os

# Add scripts directory to path for _utils imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))

from _utils.graph import TimeExpandedGraph
from _utils.solver import MinCostFlowSolver, GreedySolver
from player.models import KitClasses, KitType


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
        
        # Initialize inventory from airport initial stocks
        self._initialize_inventory()
    
    def _initialize_inventory(self):
        """Initialize inventory from airport initial stocks"""
        for airport_code, airport in self.airports.items():
            for kit_type in KitType.ALL_TYPES:
                key = (airport_code, kit_type)
                self.inventory[key] = airport.initial_stock.get(kit_type, 0)
        
        self.logger.info(f"Initialized inventory: {len(self.inventory)} entries")
    
    def process_flight_updates(self, flight_events):
        """Process flight updates from API response"""
        for event in flight_events:
            self.flights_info[event.flight_id] = {
                'id': event.flight_id,
                'number': event.flight_number,
                'event_type': event.event_type,
                'source': event.source_airport,
                'dest': event.dest_airport,
                'aircraft': event.aircraft_type,
                'distance': event.distance,
                'departure_time': event.departure_time,
                'arrival_time': event.arrival_time,
                'passengers': {
                    'FIRST': event.passengers.first,
                    'BUSINESS': event.passengers.business,
                    'PREMIUM_ECONOMY': event.passengers.premiumEconomy,
                    'ECONOMY': event.passengers.economy
                }
            }
            
            # self.logger.info(f"Processed flight update: {event.flight_number} ({event.event_type})")
    
    def get_flights_in_horizon(self, current_hour, end_hour):
        """Get all flights scheduled within the planning horizon"""
        flights_in_horizon = []
        
        for flight_id, flight in self.flights_info.items():
            if flight['departure_time']:
                # Parse departure time to hour
                # Assuming format: "2024-01-01T10:00:00"
                try:
                    dep_hour = self._parse_hour(flight['departure_time'])
                    arr_hour = self._parse_hour(flight['arrival_time']) if flight['arrival_time'] else dep_hour + 2
                    
                    if current_hour <= dep_hour < end_hour:
                        flights_in_horizon.append({
                            **flight,
                            'departure_hour': dep_hour,
                            'arrival_hour': arr_hour,
                            'fuel_cost_per_km': 0.5  # Default value
                        })
                except Exception as e:
                    self.logger.info(f"Error parsing flight time: {e}")
        
        return flights_in_horizon
    
    def _parse_hour(self, time_str):
        """Parse time string to absolute hour"""
        # Simple parser - adjust based on actual format
        if not time_str:
            return 0
        
        # For now, use current day/hour offset
        # In production, parse ISO format properly
        return self.current_day * 24 + self.current_hour
    
    def build_network(self, current_hour):
        """Build time-expanded network for optimization"""
        from _utils.graph import TimeExpandedGraph
        
        graph = TimeExpandedGraph(self.planning_horizon)
        
        # A. Add initial inventory edges
        for (airport, kit_type), quantity in self.inventory.items():
            if quantity > 0:
                graph.add_initial_inventory_edge(airport, kit_type, quantity)
        
        # B. Add storage edges (kits staying at airport)
        for t in range(self.planning_horizon - 1):
            for airport_code, airport in self.airports.items():
                for kit_type in KitType.ALL_TYPES:
                    capacity = airport.storage_capacity.get(kit_type, 1000)
                    graph.add_storage_edge(airport_code, t, kit_type, capacity, storage_cost=0)
        
        # C. Add flight edges and processing edges
        upcoming_flights = self.get_flights_in_horizon(current_hour, current_hour + self.planning_horizon)
        
        for flight in upcoming_flights:
            dep_time = flight['departure_hour'] - current_hour
            arr_time = flight['arrival_hour'] - current_hour
            
            if dep_time < 0:
                continue  # Already departed
            
            for kit_type in KitType.ALL_TYPES:
                # Calculate cost
                source_airport = self.airports.get(flight['source'])
                dest_airport = self.airports.get(flight['dest'])
                
                if not source_airport or not dest_airport:
                    continue
                
                loading_cost = source_airport.loading_cost.get(kit_type, 5)
                processing_cost = dest_airport.processing_cost.get(kit_type, 10)
                weight = KitType.WEIGHTS[kit_type]
                fuel_cost = flight['distance'] * flight['fuel_cost_per_km'] * weight
                
                total_cost = loading_cost + fuel_cost + processing_cost
                
                # Capacity
                aircraft = self.aircraft_map.get(flight['aircraft'])
                if not aircraft:
                    continue
                
                capacity = getattr(aircraft, f"{kit_type.lower().replace('_', '_')}_capacity", 100)
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
                processing_time = dest_airport.processing_time.get(kit_type, 2)
                graph.add_processing_edge(
                    flight['dest'],
                    arr_time,
                    processing_time,
                    kit_type
                )
        
        # D. Add demand edges (penalty for not meeting requirements)
        for flight in upcoming_flights:
            dep_time = flight['departure_hour'] - current_hour
            
            if dep_time < 0:
                continue
            
            for kit_type in KitType.ALL_TYPES:
                required = flight['passengers'].get(kit_type, 0)
                
                if required > 0:
                    kit_cost = KitType.COSTS[kit_type]
                    penalty = flight['distance'] * kit_cost * 10  # UNFULFILLED_PASSENGERS_FACTOR
                    
                    graph.add_demand_edge(
                        flight['id'],
                        flight['source'],
                        dep_time,
                        kit_type,
                        required,
                        penalty
                    )
        
        # E. Add purchase edges
        for kit_type in KitType.ALL_TYPES:
            lead_time = KitType.LEAD_TIMES[kit_type]
            cost = KitType.COSTS[kit_type]
            
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
        
        # 1. Extract flight loads for flights departing THIS HOUR
        if solution.kit_loads:
            for flight_id, kits in solution.kit_loads.items():
                flight = self.flights_info.get(flight_id)
                if flight and flight.get('departure_hour') == current_hour:
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
        
        # Process flight updates
        self.process_flight_updates(flight_events)
        
        # Build network
        self.logger.info(f"Building network for day {current_day}, hour {current_hour}")
        graph = self.build_network(current_hour)
        
        stats = graph.get_stats()
        self.logger.info(f"Network built: {stats}")
        
        # Solve optimization
        self.logger.info("Solving optimization...")
        solution = self.solve_optimization(graph)
        
        self.logger.info(f"Solution status: {solution.status}, cost: {solution.total_cost}")
        
        # Extract immediate decisions
        decisions = self.extract_immediate_decisions(solution, current_hour)
        
        # Format for API
        self.pending_decisions = self.format_api_request(decisions)
        
        return self.pending_decisions
    
    def apply_decisions(self, round_request):
        """Apply pending decisions to round request"""
        round_request.flight_loads = self.pending_decisions.get('flightLoads', [])
        
        # Add purchasing orders
        for purchase in self.pending_decisions.get('purchasingOrders', []):
            round_request.add_purchase(purchase['kitType'], purchase['quantity'])
        
        self.logger.info(f"Applied {len(round_request.flight_loads)} flight loads, "
                        f"{len(self.pending_decisions.get('purchasingOrders', []))} purchases")
