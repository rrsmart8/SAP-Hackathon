"""
Min-Cost Flow Solver for Rotables Optimization

Implements linear programming-based min-cost flow solver using PuLP.
"""

from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
import pulp
from .graph import TimeExpandedGraph, Edge, Node


@dataclass
class FlowSolution:
    """
    Represents the solution to a min-cost flow problem.
    
    Attributes:
        flow: List of (edge, flow_value) tuples for edges with positive flow
        objective_value: Total cost of the solution
        status: Solver status (Optimal, Infeasible, etc.)
        kit_loads: Extracted kit loading decisions per flight
    """
    flow: List[Tuple[Edge, float]]
    objective_value: float
    status: str
    kit_loads: Dict[str, Dict[str, int]] = None  # {flight_id: {kit_type: quantity}}
    
    def get_flow(self, edge: Edge) -> float:
        """Get flow value for an edge (0 if not present)"""
        for e, flow_value in self.flow:
            if e is edge:
                return flow_value
        return 0.0


class MinCostFlowSolver:
    """
    Solves min-cost flow problems using linear programming.
    
    Formulation:
        minimize: Σ (cost_e × flow_e) for all edges e
        subject to:
            - Flow conservation at each node (except source/sink)
            - Capacity constraints: lower_bound_e ≤ flow_e ≤ capacity_e
            - Non-negativity: flow_e ≥ 0
    """
    
    def __init__(self, graph: TimeExpandedGraph, solver_name: str = "PULP_CBC_CMD"):
        """
        Initialize solver with a time-expanded graph.
        
        Args:
            graph: TimeExpandedGraph instance
            solver_name: PuLP solver name (default: CBC)
        """
        self.graph = graph
        self.solver_name = solver_name
        self.problem: Optional[pulp.LpProblem] = None
        self.flow_vars: Dict[int, pulp.LpVariable] = {}  # Maps edge index to flow variable
    
    def build_problem(self) -> pulp.LpProblem:
        """
        Build the LP formulation for min-cost flow.
        
        Returns:
            PuLP problem instance
        """
        # Create LP problem (minimization)
        prob = pulp.LpProblem("Rotables_MinCostFlow", pulp.LpMinimize)
        
        # Create flow variables for each edge
        flow_vars = {}
        for i, edge in enumerate(self.graph.edges):
            var_name = f"flow_{i}_{edge.metadata.get('type', 'unknown')}"
            flow_var = pulp.LpVariable(
                var_name,
                lowBound=edge.lower_bound,
                upBound=edge.capacity if edge.capacity != float('inf') else None,
                cat=pulp.LpContinuous
            )
            flow_vars[i] = flow_var
        
        self.flow_vars = flow_vars
        
        # Objective: minimize total cost
        prob += pulp.lpSum([self.graph.edges[i].cost * flow_vars[i] for i in range(len(self.graph.edges))])
        
        # Flow conservation constraints
        for node in self.graph.nodes:
            # Skip source and sink (they don't need conservation)
            if node == self.graph.source or node == self.graph.sink:
                continue
            
            # Incoming flow
            incoming_edges = self.graph.get_incoming_edges(node)
            inflow = pulp.lpSum([
                flow_vars[self.graph.edges.index(edge)] 
                for edge in incoming_edges
            ]) if incoming_edges else 0
            
            # Outgoing flow
            outgoing_edges = self.graph.get_outgoing_edges(node)
            outflow = pulp.lpSum([
                flow_vars[self.graph.edges.index(edge)] 
                for edge in outgoing_edges
            ]) if outgoing_edges else 0
            
            # Conservation: inflow = outflow
            constraint_name = f"conservation_{node.location}_{node.time}_{node.node_type.value}_{node.kit_type}"
            prob += (inflow == outflow, constraint_name)
        
        self.problem = prob
        return prob
    
    def solve(self, time_limit_seconds: Optional[int] = None, 
              verbose: bool = False) -> FlowSolution:
        """
        Solve the min-cost flow problem.
        
        Args:
            time_limit_seconds: Maximum solver time (None = unlimited)
            verbose: Whether to print solver output
        
        Returns:
            FlowSolution with optimal flows and cost
        """
        if self.problem is None:
            self.build_problem()
        
        # Configure solver
        if self.solver_name == "PULP_CBC_CMD":
            solver = pulp.PULP_CBC_CMD(
                msg=verbose,
                timeLimit=time_limit_seconds
            )
        elif self.solver_name == "GUROBI":
            solver = pulp.GUROBI(msg=verbose, timeLimit=time_limit_seconds)
        else:
            solver = pulp.getSolver(self.solver_name, msg=verbose)
        
        # Solve
        status = self.problem.solve(solver)
        
        # Extract solution
        flow = []
        for edge_idx, var in self.flow_vars.items():
            flow_value = var.varValue
            if flow_value is not None and flow_value > 1e-6:  # Tolerance for numerical errors
                edge = self.graph.edges[edge_idx]
                flow.append((edge, flow_value))
        
        solution = FlowSolution(
            flow=flow,
            objective_value=pulp.value(self.problem.objective),
            status=pulp.LpStatus[status]
        )
        
        # Extract kit loading decisions
        solution.kit_loads = self._extract_kit_loads(solution)
        
        return solution
    
    def _extract_kit_loads(self, solution: FlowSolution) -> Dict[str, Dict[str, int]]:
        """
        Extract kit loading decisions for each flight from the flow solution.
        
        Returns:
            {flight_id: {kit_type: quantity}}
        """
        kit_loads = {}
        
        for edge, flow_value in solution.flow:
            # Only consider flight edges (actual kit movements on flights)
            if edge.metadata.get("type") != "flight":
                continue
            
            flight_id = edge.metadata.get("flight_id")
            kit_type = edge.metadata.get("kit")
            
            if flight_id not in kit_loads:
                kit_loads[flight_id] = {}
            
            # Round to nearest integer (kits are discrete)
            kit_loads[flight_id][kit_type] = int(round(flow_value))
        
        return kit_loads
    
    def get_solution_summary(self, solution: FlowSolution) -> Dict:
        """
        Generate a human-readable summary of the solution.
        
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "status": solution.status,
            "objective_value": solution.objective_value,
            "total_edges": len(self.graph.edges),
            "active_flows": len(solution.flow),
            "flights_covered": len(solution.kit_loads) if solution.kit_loads else 0,
        }
        
        # Count flow by edge type
        flow_by_type = {}
        total_flow_by_type = {}
        
        for edge, flow_value in solution.flow:
            edge_type = edge.metadata.get("type", "unknown")
            flow_by_type[edge_type] = flow_by_type.get(edge_type, 0) + 1
            total_flow_by_type[edge_type] = total_flow_by_type.get(edge_type, 0) + flow_value
        
        summary["flow_counts_by_type"] = flow_by_type
        summary["total_flow_by_type"] = total_flow_by_type
        
        # Calculate total kits loaded
        if solution.kit_loads:
            total_kits = sum(
                sum(kits.values()) 
                for kits in solution.kit_loads.values()
            )
            summary["total_kits_loaded"] = total_kits
        
        return summary
    
    def export_solution_csv(self, solution: FlowSolution, filename: str):
        """Export solution to CSV for debugging"""
        import csv
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Edge_Type', 'Source', 'Target', 'Flow', 'Cost', 'Total_Cost', 'Metadata'])
            
            for edge, flow_value in solution.flow:
                writer.writerow([
                    edge.metadata.get('type', 'unknown'),
                    str(edge.source),
                    str(edge.target),
                    flow_value,
                    edge.cost,
                    flow_value * edge.cost,
                    str(edge.metadata)
                ])


class IterativeFlowSolver:
    """
    Solves the rotables problem iteratively, round by round.
    
    This is useful for:
    - Rolling horizon approach (solve only next N hours)
    - Incorporating real-time updates (actual flight data)
    - Reducing problem size for faster solving
    """
    
    def __init__(self, horizon_hours: int = 48):
        """
        Args:
            horizon_hours: How many hours ahead to plan
        """
        self.horizon = horizon_hours
        self.current_time = 0
    
    def solve_round(self, current_state: Dict, flights: list, 
                    airports: Dict) -> Dict[str, Dict[str, int]]:
        """
        Solve for the next round given current state.
        
        Args:
            current_state: Current inventory at each airport
            flights: List of upcoming flights
            airports: Airport configuration (capacities, costs)
        
        Returns:
            Kit loading decisions for departing flights
        """
        # Build graph for planning horizon
        graph = TimeExpandedGraph(self.horizon)
        
        # Add initial inventory
        for airport, inventory in current_state.items():
            for kit_type, quantity in inventory.items():
                graph.add_initial_inventory_edge(airport, kit_type, quantity)
        
        # Add flights within horizon
        for flight in flights:
            if flight['departure_time'] < self.current_time + self.horizon:
                # Add flight edges for each kit type
                # (This would be filled in with actual flight data)
                pass
        
        # Solve
        solver = MinCostFlowSolver(graph)
        solution = solver.solve()
        
        return solution.kit_loads
