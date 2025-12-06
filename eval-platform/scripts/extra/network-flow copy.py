"""
Network Flow Optimization for Rotables Management

This script demonstrates how to use the time-expanded graph and min-cost flow
solver to optimize rotables (kit) allocation across flights.

Usage:
    python network-flow.py [--horizon HOURS] [--verbose]
"""

import sys
import argparse
from typing import Dict, List
from _utils.graph import TimeExpandedGraph, NodeType
from _utils.solver import MinCostFlowSolver, FlowSolution


# Kit type definitions (from problem specification)
KIT_TYPES = {
    "FIRST": {"cost": 500, "weight": 5.0},
    "BUSINESS": {"cost": 200, "weight": 3.0},
    "PREMIUM_ECONOMY": {"cost": 100, "weight": 2.0},
    "ECONOMY": {"cost": 50, "weight": 1.0}
}


class RotablesOptimizer:
    """
    Main optimizer for rotables management using network flow.
    """
    
    def __init__(self, time_horizon_hours: int = 168):  # 1 week default
        """
        Args:
            time_horizon_hours: Planning horizon in hours
        """
        self.time_horizon = time_horizon_hours
        self.graph = TimeExpandedGraph(time_horizon_hours)
        self.airports: Dict[str, Dict] = {}
        self.flights: List[Dict] = []
    
    def add_airport(self, code: str, storage_capacity: Dict[str, int],
                   processing_time: Dict[str, int], processing_cost: Dict[str, float],
                   loading_cost: Dict[str, float], initial_stock: Dict[str, int]):
        """
        Add an airport to the network.
        
        Args:
            code: Airport code (e.g., "HUB1", "A1")
            storage_capacity: Max storage per kit type
            processing_time: Processing time in hours per kit type
            processing_cost: Cost to process one kit per type
            loading_cost: Cost to load one kit per type
            initial_stock: Initial inventory per kit type
        """
        self.airports[code] = {
            "storage_capacity": storage_capacity,
            "processing_time": processing_time,
            "processing_cost": processing_cost,
            "loading_cost": loading_cost,
            "initial_stock": initial_stock
        }
        
        # Add initial inventory edges to graph
        for kit_type, stock in initial_stock.items():
            if stock > 0:
                self.graph.add_initial_inventory_edge(code, kit_type, stock)
        
        # Add storage edges for all time periods
        for t in range(self.time_horizon):
            for kit_type in KIT_TYPES.keys():
                capacity = storage_capacity.get(kit_type, float('inf'))
                self.graph.add_storage_edge(code, t, kit_type, capacity, storage_cost=0.0)
    
    def add_flight(self, flight_id: str, source: str, destination: str,
                  departure_time: int, arrival_time: int, distance: float,
                  passengers: Dict[str, int], aircraft_capacity: Dict[str, int],
                  fuel_cost_per_km: float):
        """
        Add a flight to the network.
        
        Args:
            flight_id: Unique flight identifier
            source: Departure airport code
            destination: Arrival airport code
            departure_time: Departure time in hours from start
            arrival_time: Arrival time in hours
            distance: Flight distance in km
            passengers: Expected passengers per kit type
            aircraft_capacity: Max kits per type aircraft can carry
            fuel_cost_per_km: Cost per km per kg
        """
        flight = {
            "id": flight_id,
            "source": source,
            "destination": destination,
            "departure_time": departure_time,
            "arrival_time": arrival_time,
            "distance": distance,
            "passengers": passengers,
            "capacity": aircraft_capacity,
            "fuel_cost_per_km": fuel_cost_per_km
        }
        self.flights.append(flight)
        
        # Add flight edges to graph for each kit type
        for kit_type in KIT_TYPES.keys():
            # Calculate transport cost: loading + movement + processing
            loading_cost = self.airports[source]["loading_cost"].get(kit_type, 0)
            processing_cost = self.airports[destination]["processing_cost"].get(kit_type, 0)
            weight = KIT_TYPES[kit_type]["weight"]
            movement_cost = distance * fuel_cost_per_km * weight
            
            total_transport_cost = loading_cost + movement_cost + processing_cost
            
            # Add flight edge
            capacity = aircraft_capacity.get(kit_type, float('inf'))
            self.graph.add_flight_edge(
                flight_id, source, destination,
                departure_time, arrival_time, kit_type,
                capacity, total_transport_cost
            )
            
            # Add processing edge at destination
            processing_time = self.airports[destination]["processing_time"].get(kit_type, 2)
            self.graph.add_processing_edge(
                destination, arrival_time, processing_time, kit_type
            )
            
            # Add demand edge (penalty for not meeting passenger needs)
            required = passengers.get(kit_type, 0)
            if required > 0:
                # Penalty: very high cost to discourage unmet demand
                kit_cost = KIT_TYPES[kit_type]["cost"]
                penalty = distance * kit_cost * 10  # 10x multiplier for penalty
                
                self.graph.add_demand_edge(
                    flight_id, source, departure_time,
                    kit_type, required, penalty
                )
    
    def optimize(self, time_limit: int = 300, verbose: bool = False) -> FlowSolution:
        """
        Solve the optimization problem.
        
        Args:
            time_limit: Solver time limit in seconds
            verbose: Print solver output
        
        Returns:
            FlowSolution with optimal kit loads
        """
        solver = MinCostFlowSolver(self.graph)
        solution = solver.solve(time_limit_seconds=time_limit, verbose=verbose)
        return solution
    
    def print_solution(self, solution: FlowSolution):
        """Print human-readable solution"""
        print(f"\n{'='*60}")
        print(f"SOLUTION SUMMARY")
        print(f"{'='*60}")
        print(f"Status: {solution.status}")
        print(f"Total Cost: ${solution.objective_value:,.2f}")
        print(f"\nKIT LOADING DECISIONS:")
        print(f"{'-'*60}")
        
        if solution.kit_loads:
            for flight_id, kits in sorted(solution.kit_loads.items()):
                print(f"\nFlight {flight_id}:")
                for kit_type, quantity in sorted(kits.items()):
                    print(f"  {kit_type:20s}: {quantity:4d} kits")
        else:
            print("No kit loads required")
        
        print(f"\n{'='*60}\n")


def example_simple_network():
    """
    Example: Simple hub-and-spoke network with 3 airports.
    """
    print("Building simple hub-and-spoke network...")
    
    optimizer = RotablesOptimizer(time_horizon_hours=72)  # 3 days
    
    # Add HUB
    optimizer.add_airport(
        code="HUB1",
        storage_capacity={"FIRST": 100, "BUSINESS": 200, "PREMIUM_ECONOMY": 300, "ECONOMY": 500},
        processing_time={"FIRST": 2, "BUSINESS": 2, "PREMIUM_ECONOMY": 2, "ECONOMY": 2},
        processing_cost={"FIRST": 10, "BUSINESS": 8, "PREMIUM_ECONOMY": 6, "ECONOMY": 4},
        loading_cost={"FIRST": 5, "BUSINESS": 4, "PREMIUM_ECONOMY": 3, "ECONOMY": 2},
        initial_stock={"FIRST": 50, "BUSINESS": 100, "PREMIUM_ECONOMY": 150, "ECONOMY": 250}
    )
    
    # Add outstation A1
    optimizer.add_airport(
        code="A1",
        storage_capacity={"FIRST": 20, "BUSINESS": 40, "PREMIUM_ECONOMY": 60, "ECONOMY": 100},
        processing_time={"FIRST": 4, "BUSINESS": 4, "PREMIUM_ECONOMY": 4, "ECONOMY": 4},
        processing_cost={"FIRST": 15, "BUSINESS": 12, "PREMIUM_ECONOMY": 10, "ECONOMY": 8},
        loading_cost={"FIRST": 8, "BUSINESS": 6, "PREMIUM_ECONOMY": 5, "ECONOMY": 4},
        initial_stock={"FIRST": 10, "BUSINESS": 20, "PREMIUM_ECONOMY": 30, "ECONOMY": 50}
    )
    
    # Add outstation A2
    optimizer.add_airport(
        code="A2",
        storage_capacity={"FIRST": 15, "BUSINESS": 30, "PREMIUM_ECONOMY": 50, "ECONOMY": 80},
        processing_time={"FIRST": 4, "BUSINESS": 4, "PREMIUM_ECONOMY": 4, "ECONOMY": 4},
        processing_cost={"FIRST": 15, "BUSINESS": 12, "PREMIUM_ECONOMY": 10, "ECONOMY": 8},
        loading_cost={"FIRST": 8, "BUSINESS": 6, "PREMIUM_ECONOMY": 5, "ECONOMY": 4},
        initial_stock={"FIRST": 8, "BUSINESS": 15, "PREMIUM_ECONOMY": 25, "ECONOMY": 40}
    )
    
    # Add flights (hub to A1 and return)
    optimizer.add_flight(
        flight_id="F001_HUB_A1",
        source="HUB1",
        destination="A1",
        departure_time=2,
        arrival_time=4,
        distance=1000,
        passengers={"FIRST": 5, "BUSINESS": 15, "PREMIUM_ECONOMY": 20, "ECONOMY": 60},
        aircraft_capacity={"FIRST": 10, "BUSINESS": 30, "PREMIUM_ECONOMY": 40, "ECONOMY": 100},
        fuel_cost_per_km=0.5
    )
    
    optimizer.add_flight(
        flight_id="F001_A1_HUB",
        source="A1",
        destination="HUB1",
        departure_time=8,
        arrival_time=10,
        distance=1000,
        passengers={"FIRST": 4, "BUSINESS": 12, "PREMIUM_ECONOMY": 18, "ECONOMY": 55},
        aircraft_capacity={"FIRST": 10, "BUSINESS": 30, "PREMIUM_ECONOMY": 40, "ECONOMY": 100},
        fuel_cost_per_km=0.5
    )
    
    # Add flights (hub to A2 and return)
    optimizer.add_flight(
        flight_id="F002_HUB_A2",
        source="HUB1",
        destination="A2",
        departure_time=6,
        arrival_time=8,
        distance=800,
        passengers={"FIRST": 3, "BUSINESS": 10, "PREMIUM_ECONOMY": 15, "ECONOMY": 45},
        aircraft_capacity={"FIRST": 8, "BUSINESS": 25, "PREMIUM_ECONOMY": 35, "ECONOMY": 80},
        fuel_cost_per_km=0.5
    )
    
    optimizer.add_flight(
        flight_id="F002_A2_HUB",
        source="A2",
        destination="HUB1",
        departure_time=12,
        arrival_time=14,
        distance=800,
        passengers={"FIRST": 2, "BUSINESS": 8, "PREMIUM_ECONOMY": 12, "ECONOMY": 40},
        aircraft_capacity={"FIRST": 8, "BUSINESS": 25, "PREMIUM_ECONOMY": 35, "ECONOMY": 80},
        fuel_cost_per_km=0.5
    )
    
    print(f"Graph: {optimizer.graph}")
    print(f"Airports: {len(optimizer.airports)}")
    print(f"Flights: {len(optimizer.flights)}")
    
    # Optimize
    print("\nSolving optimization problem...")
    solution = optimizer.optimize(verbose=True)
    
    # Display results
    optimizer.print_solution(solution)
    
    # Show detailed summary
    solver = MinCostFlowSolver(optimizer.graph)
    solver.flow_vars = {}  # Reset if needed
    summary = solver.get_solution_summary(solution)
    print("\nDETAILED STATISTICS:")
    for key, value in summary.items():
        print(f"  {key}: {value}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Network Flow Optimization for Rotables Management"
    )
    parser.add_argument(
        "--example",
        choices=["simple"],
        default="simple",
        help="Which example to run"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose solver output")
    
    args = parser.parse_args()
    
    if args.example == "simple":
        example_simple_network()


if __name__ == "__main__":
    main()
