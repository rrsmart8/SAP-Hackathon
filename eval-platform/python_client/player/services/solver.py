"""
Min-Cost Flow Solver using OR-Tools
"""


from ortools.graph.python import min_cost_flow
from .graph import Edge


class Solution:
    """Container for optimization solution"""
    def __init__(self):
        self.status = None
        self.total_cost = 0
        self.kit_loads = {}  # {flight_id: {kit_type: quantity}}
        self.purchases = {}  # {kit_type: quantity}
        self.flow = []  # List of (edge, flow_value) tuples
        

class MinCostFlowSolver:
    """
    Solves min-cost flow problem on time-expanded network
    Uses Google OR-Tools
    """
    
    def __init__(self, graph):
        self.graph = graph
        self.smcf = min_cost_flow.SimpleMinCostFlow()
        self.node_to_index = {}
        self.index_to_node = {}
        self.edge_list = []
        
    def _build_node_mapping(self):
        """Create mapping between node IDs and integer indices"""
        # Ensure source and sink nodes are created
        self.graph.get_source()
        self.graph.get_sink()
        
        idx = 0
        for node_id in self.graph.nodes:
            self.node_to_index[node_id] = idx
            self.index_to_node[idx] = node_id
            idx += 1
    
    def _add_edges_to_solver(self):
        """Add all edges from graph to OR-Tools solver"""
        for edge in self.graph.edges:
            source_idx = self.node_to_index[edge.source]
            target_idx = self.node_to_index[edge.target]
            
            # OR-Tools requires integer capacity and cost
            # We'll scale costs by 1000 to preserve precision
            capacity = int(edge.capacity) if edge.capacity != float('inf') else 999999
            cost = int(edge.cost * 1000)
            
            self.smcf.add_arc_with_capacity_and_unit_cost(
                source_idx,
                target_idx,
                capacity,
                cost
            )
            
            # Store edge for later retrieval
            self.edge_list.append(edge)
    
    def _set_supplies(self):
        """Set supply/demand for source and sink nodes"""
        # Calculate total demand from all demand edges
        total_demand = 0
        for edge in self.graph.edges:
            if edge.edge_type == 'demand':
                total_demand += edge.capacity
        
        # Add buffer for purchases and initial inventory
        total_supply = 0
        for edge in self.graph.edges:
            if edge.edge_type in ['initial_inventory', 'purchase']:
                total_supply += edge.capacity
        
        # If no demand, we need to balance supply and demand
        # For min-cost flow, total supply must equal total demand
        # If no demand edges exist, we can either:
        # 1. Set demand = supply (balance)
        # 2. Add a dummy edge from source to sink
        # We'll balance by setting demand = supply
        if total_demand == 0 and total_supply > 0:
            # No demand edges - balance by making sink consume all supply
            total_demand = total_supply
        
        # Source supplies everything
        source_idx = self.node_to_index[self.graph.get_source().node_id]
        self.smcf.set_node_supply(source_idx, int(total_supply))
        
        # Sink demands everything
        sink_idx = self.node_to_index[self.graph.get_sink().node_id]
        self.smcf.set_node_supply(sink_idx, -int(total_demand))
    
    def solve(self, time_limit_seconds=30, verbose=False):
        """
        Solve the min-cost flow problem
        
        Returns:
            Solution object containing flow values and decisions
        """
        solution = Solution()
        
        # Build the problem
        self._build_node_mapping()
        
        # Check if we need to add a dummy edge from source to sink
        # (if no demand edges exist, we need a path for flow)
        has_demand_edges = any(e.edge_type == 'demand' for e in self.graph.edges)
        if not has_demand_edges:
            # Add a high-capacity, low-cost edge from source to sink
            # This allows flow to reach sink when no demand edges exist
            source = self.graph.get_source()
            sink = self.graph.get_sink()
            dummy_edge = Edge(
                source=source.node_id,
                target=sink.node_id,
                capacity=999999,
                cost=0,
                edge_type='dummy',
                metadata={'reason': 'no_demand_edges'}
            )
            self.graph.edges.append(dummy_edge)
        
        self._add_edges_to_solver()
        self._set_supplies()
        
        if verbose:
            print(f"Solving min-cost flow with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges")
        
        # Solve
        try:
            status = self.smcf.solve()
        except Exception as e:
            if verbose:
                print(f"Solver exception: {e}")
            solution.status = 'ERROR'
            solution.total_cost = 0
            return solution
        
        # Check status codes from OR-Tools
        # Status can be: OPTIMAL, FEASIBLE, INFEASIBLE, UNBALANCED, BAD_RESULT, BAD_COST_RANGE
        if status == self.smcf.OPTIMAL:
            solution.status = 'OPTIMAL'
            solution.total_cost = self.smcf.optimal_cost() / 1000.0  # Unscale cost
            
            # Extract flows
            for i, edge in enumerate(self.edge_list):
                flow_value = self.smcf.flow(i)
                if flow_value > 0:
                    solution.flow.append((edge, flow_value))
                    
                    # Extract flight loads
                    if edge.edge_type == 'flight':
                        flight_id = edge.metadata['flight_id']
                        kit_type = edge.metadata['kit']
                        
                        if flight_id not in solution.kit_loads:
                            solution.kit_loads[flight_id] = {}
                        solution.kit_loads[flight_id][kit_type] = flow_value
                    
                    # Extract purchases
                    elif edge.edge_type == 'purchase':
                        kit_type = edge.metadata['kit']
                        solution.purchases[kit_type] = solution.purchases.get(kit_type, 0) + flow_value
            
            if verbose:
                print(f"Optimal solution found with cost: {solution.total_cost}")
                print(f"Flight loads: {len(solution.kit_loads)} flights")
                print(f"Purchases: {solution.purchases}")
        
        elif status == self.smcf.FEASIBLE:
            # Feasible but not optimal (shouldn't happen with SimpleMinCostFlow, but handle it)
            solution.status = 'FEASIBLE'
            solution.total_cost = self.smcf.optimal_cost() / 1000.0
            
            # Extract flows same as optimal
            for i, edge in enumerate(self.edge_list):
                flow_value = self.smcf.flow(i)
                if flow_value > 0:
                    solution.flow.append((edge, flow_value))
                    
                    if edge.edge_type == 'flight':
                        flight_id = edge.metadata['flight_id']
                        kit_type = edge.metadata['kit']
                        if flight_id not in solution.kit_loads:
                            solution.kit_loads[flight_id] = {}
                        solution.kit_loads[flight_id][kit_type] = flow_value
                    elif edge.edge_type == 'purchase':
                        kit_type = edge.metadata['kit']
                        solution.purchases[kit_type] = solution.purchases.get(kit_type, 0) + flow_value
            
            if verbose:
                print(f"Feasible solution found with cost: {solution.total_cost}")
        
        elif status == self.smcf.INFEASIBLE:
            solution.status = 'INFEASIBLE'
            if verbose:
                print("Problem is infeasible!")
        
        elif status == self.smcf.UNBALANCED:
            solution.status = 'UNBALANCED'
            if verbose:
                print("Problem is unbalanced (supply != demand)")
        
        else:
            solution.status = 'ERROR'
            # Log the actual status code for debugging
            status_name = "UNKNOWN"
            if hasattr(self.smcf, 'BAD_RESULT') and status == self.smcf.BAD_RESULT:
                status_name = "BAD_RESULT"
            elif hasattr(self.smcf, 'BAD_COST_RANGE') and status == self.smcf.BAD_COST_RANGE:
                status_name = "BAD_COST_RANGE"
            
            if verbose:
                print(f"Solver returned status: {status} ({status_name})")
        
        return solution


class GreedySolver:
    """
    Fallback greedy solver if OR-Tools is not available
    Simple heuristic that prioritizes low-cost paths
    """
    
    def __init__(self, graph):
        self.graph = graph
    
    def solve(self, time_limit_seconds=30, verbose=False):
        """
        Simple greedy heuristic:
        1. Sort edges by cost per unit
        2. Flow as much as possible through cheapest edges first
        """
        solution = Solution()
        solution.status = 'GREEDY'
        
        # Track available flow at each node
        node_supply = {}
        for node_id in self.graph.nodes:
            node_supply[node_id] = 0
        
        # Add initial supply from source
        if self.graph.source_node:
            source_id = self.graph.source_node.node_id
            for edge in self.graph.edges:
                if edge.source == source_id:
                    node_supply[source_id] += edge.capacity
        
        # Sort edges by cost per unit (ascending)
        sorted_edges = sorted(self.graph.edges, key=lambda e: e.cost if e.capacity > 0 else float('inf'))
        
        flow_dict = {}
        
        # Greedy flow assignment
        for edge in sorted_edges:
            available_at_source = node_supply.get(edge.source, 0)
            can_flow = min(edge.capacity, available_at_source)
            
            if can_flow > 0:
                flow_dict[id(edge)] = can_flow
                solution.flow.append((edge, can_flow))
                node_supply[edge.source] -= can_flow
                node_supply[edge.target] = node_supply.get(edge.target, 0) + can_flow
                solution.total_cost += edge.cost * can_flow
                
                # Extract decisions
                if edge.edge_type == 'flight':
                    flight_id = edge.metadata['flight_id']
                    kit_type = edge.metadata['kit']
                    if flight_id not in solution.kit_loads:
                        solution.kit_loads[flight_id] = {}
                    solution.kit_loads[flight_id][kit_type] = can_flow
                
                elif edge.edge_type == 'purchase':
                    kit_type = edge.metadata['kit']
                    solution.purchases[kit_type] = solution.purchases.get(kit_type, 0) + can_flow
        
        if verbose:
            print(f"Greedy solution with cost: {solution.total_cost}")
        
        return solution
