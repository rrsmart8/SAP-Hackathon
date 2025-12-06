"""
Main entry point for Rotables Optimization Bot

Follow the IMPLEMENTATION_GUIDE.md for detailed explanation of each step.
"""

import csv
import requests
from datetime import datetime
from typing import Dict, List, Tuple
from _utils.graph import TimeExpandedGraph
from _utils.solver import MinCostFlowSolver


class RotablesBot:
    """
    Main bot class that manages the optimization pipeline
    """
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        
        # Time tracking
        self.current_hour = 0
        self.current_day = 0
        
        # Static data (loaded from CSV)
        self.airports = {}
        self.aircraft_types = {}
        self.flight_schedule = []
        
        # State
        self.inventory = {}  # {(airport, kit_type): quantity}
        self.in_processing_kits = []  # Kits being processed
        self.purchasing_orders = []  # Pending purchases
        self.flights_info = {}  # {flight_id: flight_data}
        
        # Constants
        self.KIT_TYPES = ["FIRST", "BUSINESS", "PREMIUM_ECONOMY", "ECONOMY"]
        self.PLANNING_HORIZON = 48  # hours
        
        # Decisions for next API call
        self.pending_decisions = {'flightLoads': [], 'purchasingOrders': []}
        
        # Load static data
        self._load_data()
    
    # ========== STEP 1: Load Data ==========
    
    def _load_data(self):
        """Load CSV data files"""
        print("Loading data from CSV files...")
        
        # Load airports
        self.airports = self._load_airports()
        print(f"  Loaded {len(self.airports)} airports")
        
        # Load aircraft types
        self.aircraft_types = self._load_aircraft_types()
        print(f"  Loaded {len(self.aircraft_types)} aircraft types")
        
        # Load flight schedule
        self.flight_schedule = self._load_flight_schedule()
        print(f"  Loaded {len(self.flight_schedule)} scheduled flights")
        
        # Initialize inventory from airports
        self._initialize_inventory()
        print(f"  Initialized inventory at {len(self.inventory)} locations")
    
    def _load_airports(self) -> Dict:
        """Load airports from CSV"""
        airports = {}
        
        # TODO: Load from ../src/main/resources/liquibase/data/airports_with_stocks.csv
        # For now, return dummy data
        airports['HUB1'] = {
            'code': 'HUB1',
            'storage_capacity': {'FIRST': 100, 'BUSINESS': 200, 'PREMIUM_ECONOMY': 300, 'ECONOMY': 500},
            'processing_time': {'FIRST': 2, 'BUSINESS': 2, 'PREMIUM_ECONOMY': 2, 'ECONOMY': 2},
            'processing_cost': {'FIRST': 10, 'BUSINESS': 8, 'PREMIUM_ECONOMY': 6, 'ECONOMY': 4},
            'loading_cost': {'FIRST': 5, 'BUSINESS': 4, 'PREMIUM_ECONOMY': 3, 'ECONOMY': 2},
            'initial_stock': {'FIRST': 50, 'BUSINESS': 100, 'PREMIUM_ECONOMY': 150, 'ECONOMY': 250}
        }
        
        return airports
    
    def _load_aircraft_types(self) -> Dict:
        """Load aircraft types from CSV"""
        aircraft = {}
        
        # TODO: Load from ../src/main/resources/liquibase/data/aircraft_types.csv
        aircraft['B737'] = {
            'type': 'B737',
            'capacity': {'FIRST': 10, 'BUSINESS': 30, 'PREMIUM_ECONOMY': 40, 'ECONOMY': 100},
            'fuel_cost_per_km': 0.5
        }
        
        return aircraft
    
    def _load_flight_schedule(self) -> List:
        """Load flight schedule from CSV"""
        schedule = []
        
        # TODO: Load from ../src/main/resources/liquibase/data/flight_plan.csv
        
        return schedule
    
    def _initialize_inventory(self):
        """Initialize inventory from airport data"""
        for airport_code, airport_data in self.airports.items():
            for kit_type in self.KIT_TYPES:
                initial = airport_data.get('initial_stock', {}).get(kit_type, 0)
                self.inventory[(airport_code, kit_type)] = initial
    
    # ========== STEP 2: Process Flight Updates ==========
    
    def process_flight_updates(self, flight_updates: List[Dict]):
        """Process flight updates from API response"""
        for flight in flight_updates:
            flight_id = flight.get('flightId')
            update_type = flight.get('type')
            
            if update_type == 'SCHEDULED':
                # Flight announced 24h before departure
                self.flights_info[flight_id] = {
                    'id': flight_id,
                    'source': flight.get('departureAirport'),
                    'dest': flight.get('arrivalAirport'),
                    'departure_hour': self._parse_time(flight.get('departureTime')),
                    'arrival_hour': self._parse_time(flight.get('arrivalTime')),
                    'planned_passengers': flight.get('passengers', {}),
                    'planned_aircraft': flight.get('aircraftType'),
                    'distance': flight.get('distance', 1000),
                    'status': 'SCHEDULED'
                }
            
            elif update_type == 'CHECKED_IN':
                # Actual data 1h before departure
                if flight_id in self.flights_info:
                    self.flights_info[flight_id]['actual_passengers'] = flight.get('passengers', {})
                    self.flights_info[flight_id]['actual_aircraft'] = flight.get('aircraftType')
                    self.flights_info[flight_id]['status'] = 'CHECKED_IN'
            
            elif update_type == 'LANDED':
                # Flight arrived - move kits to processing
                if flight_id in self.flights_info:
                    self._process_landing(flight_id)
                    self.flights_info[flight_id]['status'] = 'LANDED'
    
    def _parse_time(self, time_str: str) -> int:
        """Convert time string to hour offset"""
        # TODO: Implement proper time parsing
        return 0
    
    def _process_landing(self, flight_id: str):
        """Move loaded kits to processing queue"""
        flight = self.flights_info[flight_id]
        destination = flight['dest']
        
        # Get kits that were loaded on this flight
        loaded_kits = self._get_loaded_kits(flight_id)
        
        for kit_type, quantity in loaded_kits.items():
            if quantity > 0:
                processing_time = self.airports[destination]['processing_time'][kit_type]
                available_at = self.current_hour + processing_time
                
                self.in_processing_kits.append({
                    'airport': destination,
                    'kit_type': kit_type,
                    'quantity': quantity,
                    'available_at': available_at
                })
    
    def _get_loaded_kits(self, flight_id: str) -> Dict[str, int]:
        """Get kits that were loaded on this flight"""
        # TODO: Track this when making loading decisions
        return {}
    
    # ========== STEP 3: Update Inventory ==========
    
    def update_inventory(self, current_hour: int):
        """Update inventory based on processing completions and purchases"""
        
        # 1. Process kits that finished processing
        newly_available = []
        still_processing = []
        
        for kit_batch in self.in_processing_kits:
            if kit_batch['available_at'] <= current_hour:
                # Kits are now available
                airport = kit_batch['airport']
                kit_type = kit_batch['kit_type']
                quantity = kit_batch['quantity']
                
                key = (airport, kit_type)
                self.inventory[key] = self.inventory.get(key, 0) + quantity
                newly_available.append(kit_batch)
            else:
                still_processing.append(kit_batch)
        
        self.in_processing_kits = still_processing
        
        # 2. Process arrived purchases
        arrived_purchases = [p for p in self.purchasing_orders 
                            if p['delivery_time'] <= current_hour]
        
        for purchase in arrived_purchases:
            kit_type = purchase['kit_type']
            quantity = purchase['quantity']
            self.inventory[('HUB1', kit_type)] = self.inventory.get(('HUB1', kit_type), 0) + quantity
        
        # Remove delivered purchases
        self.purchasing_orders = [p for p in self.purchasing_orders 
                                 if p['delivery_time'] > current_hour]
    
    # ========== STEP 4: Build Network ==========
    
    def build_network(self, current_hour: int) -> TimeExpandedGraph:
        """Build time-expanded network for optimization"""
        graph = TimeExpandedGraph(self.PLANNING_HORIZON)
        
        # A. Add initial inventory
        for (airport, kit_type), quantity in self.inventory.items():
            if quantity > 0:
                graph.add_initial_inventory_edge(airport, kit_type, quantity)
        
        # B. Add storage edges
        for t in range(self.PLANNING_HORIZON - 1):
            for airport_code in self.airports.keys():
                for kit_type in self.KIT_TYPES:
                    capacity = self.airports[airport_code]['storage_capacity'].get(kit_type, 1000)
                    graph.add_storage_edge(airport_code, t, kit_type, capacity, storage_cost=0)
        
        # C. Add flight edges
        upcoming_flights = self._get_flights_in_horizon(current_hour)
        
        for flight in upcoming_flights:
            self._add_flight_to_graph(graph, flight, current_hour)
        
        return graph
    
    def _get_flights_in_horizon(self, current_hour: int) -> List[Dict]:
        """Get flights within planning horizon"""
        upcoming = []
        
        for flight_id, flight in self.flights_info.items():
            if (flight['status'] in ['SCHEDULED', 'CHECKED_IN'] and 
                current_hour <= flight['departure_hour'] < current_hour + self.PLANNING_HORIZON):
                upcoming.append(flight)
        
        return upcoming
    
    def _add_flight_to_graph(self, graph: TimeExpandedGraph, flight: Dict, current_hour: int):
        """Add flight edges to graph"""
        dep_time = flight['departure_hour'] - current_hour
        arr_time = flight['arrival_hour'] - current_hour
        
        if dep_time < 0:
            return  # Already departed
        
        for kit_type in self.KIT_TYPES:
            # Calculate cost
            loading_cost = self.airports[flight['source']]['loading_cost'][kit_type]
            processing_cost = self.airports[flight['dest']]['processing_cost'][kit_type]
            weight = self._get_kit_weight(kit_type)
            fuel_cost = flight['distance'] * 0.5 * weight  # TODO: Use actual fuel cost
            
            total_cost = loading_cost + fuel_cost + processing_cost
            
            # Capacity
            aircraft = flight.get('actual_aircraft') or flight.get('planned_aircraft')
            capacity = self.aircraft_types.get(aircraft, {}).get('capacity', {}).get(kit_type, 100)
            
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
            
            # Add processing edge
            processing_time = self.airports[flight['dest']]['processing_time'][kit_type]
            graph.add_processing_edge(flight['dest'], arr_time, processing_time, kit_type)
            
            # Add demand edge
            passengers = flight.get('actual_passengers') or flight.get('planned_passengers')
            required = passengers.get(kit_type, 0)
            
            if required > 0:
                penalty = flight['distance'] * self._get_kit_cost(kit_type) * 10
                graph.add_demand_edge(flight['id'], flight['source'], dep_time, 
                                     kit_type, required, penalty)
    
    def _get_kit_weight(self, kit_type: str) -> float:
        """Get weight of kit type"""
        weights = {'FIRST': 5.0, 'BUSINESS': 3.0, 'PREMIUM_ECONOMY': 2.0, 'ECONOMY': 1.0}
        return weights.get(kit_type, 1.0)
    
    def _get_kit_cost(self, kit_type: str) -> float:
        """Get cost of kit type"""
        costs = {'FIRST': 500, 'BUSINESS': 200, 'PREMIUM_ECONOMY': 100, 'ECONOMY': 50}
        return costs.get(kit_type, 50)
    
    # ========== STEP 5: Solve Optimization ==========
    
    def solve_optimization(self, graph: TimeExpandedGraph):
        """Solve min-cost flow problem"""
        solver = MinCostFlowSolver(graph)
        solution = solver.solve(time_limit_seconds=30, verbose=False)
        return solution
    
    # ========== STEP 6: Extract Decisions ==========
    
    def extract_immediate_decisions(self, solution, current_hour: int) -> Dict:
        """Extract decisions for current hour only"""
        decisions = {'flight_loads': {}, 'purchases': {}}
        
        # Extract flight loads for departing flights
        if solution.kit_loads:
            for flight_id, kits in solution.kit_loads.items():
                if flight_id in self.flights_info:
                    flight = self.flights_info[flight_id]
                    if flight['departure_hour'] == current_hour:
                        decisions['flight_loads'][flight_id] = kits
        
        # Extract purchases (from purchase edges)
        for edge, flow_value in solution.flow:
            if edge.metadata.get('type') == 'purchase':
                kit_type = edge.metadata['kit']
                quantity = int(round(flow_value))
                if quantity > 0:
                    decisions['purchases'][kit_type] = decisions['purchases'].get(kit_type, 0) + quantity
        
        return decisions
    
    # ========== STEP 7: Format for API ==========
    
    def format_api_request(self, decisions: Dict) -> Dict:
        """Format decisions for API"""
        flight_loads = []
        
        for flight_id, kits in decisions['flight_loads'].items():
            flight_loads.append({
                'flightId': flight_id,
                'kits': {
                    'FIRST': kits.get('FIRST', 0),
                    'BUSINESS': kits.get('BUSINESS', 0),
                    'PREMIUM_ECONOMY': kits.get('PREMIUM_ECONOMY', 0),
                    'ECONOMY': kits.get('ECONOMY', 0)
                }
            })
        
        purchase_orders = []
        for kit_type, quantity in decisions['purchases'].items():
            if quantity > 0:
                purchase_orders.append({
                    'kitType': kit_type,
                    'quantity': quantity
                })
        
        return {
            'flightLoads': flight_loads,
            'purchasingOrders': purchase_orders
        }
    
    # ========== STEP 8: Main Game Loop ==========
    
    def run_game(self):
        """Main game loop"""
        print("Starting game...")
        
        # Start session
        session_id = self._start_session()
        print(f"Session started: {session_id}")
        
        while True:
            # Play round
            response = self._play_round(session_id)
            
            if response.get('status') == 'FINISHED':
                print(f"\nGame finished! Final cost: {response.get('totalCost', 0):,.2f}")
                break
            
            # Process updates
            self.process_flight_updates(response.get('flights', []))
            
            # Update inventory
            self.update_inventory(self.current_hour)
            
            # Build network and solve
            graph = self.build_network(self.current_hour)
            solution = self.solve_optimization(graph)
            
            # Extract decisions
            decisions = self.extract_immediate_decisions(solution, self.current_hour)
            
            # Format for next API call
            self.pending_decisions = self.format_api_request(decisions)
            
            # Advance time
            self._advance_time()
            
            # Log progress
            print(f"Day {self.current_day}, Hour {self.current_hour} - Cost: {response.get('totalCost', 0):,.2f}")
    
    def _start_session(self) -> str:
        """Start a new session"""
        response = requests.post(
            f"{self.api_url}/start-session",
            headers={'API-KEY': self.api_key}
        )
        return response.json()['sessionId']
    
    def _play_round(self, session_id: str) -> Dict:
        """Play one round"""
        payload = {
            'day': self.current_day,
            'hour': self.current_hour,
            'flightLoads': self.pending_decisions.get('flightLoads', []),
            'purchasingOrders': self.pending_decisions.get('purchasingOrders', [])
        }
        
        response = requests.post(
            f"{self.api_url}/play/{session_id}",
            json=payload,
            headers={'API-KEY': self.api_key}
        )
        
        return response.json()
    
    def _advance_time(self):
        """Advance to next hour"""
        self.current_hour += 1
        if self.current_hour >= 24:
            self.current_hour = 0
            self.current_day += 1


def main():
    """Main entry point"""
    API_URL = "http://localhost:8080"
    API_KEY = "YOUR_API_KEY_HERE"
    
    bot = RotablesBot(API_URL, API_KEY)
    bot.run_game()


if __name__ == "__main__":
    main()
