import heapq
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass, field
from enum import Enum


class NodeType(Enum):
    SOURCE = "source"
    SINK = "sink"
    AVAILABLE = "available"  # Kits ready to be loaded on flights
    FROZEN = "frozen"  # Kits in processing, not yet available
    IN_TRANSIT = "in_transit"  # Kits on a flight


@dataclass(frozen=True)
class Node:
    """
    Represents a node in the time-expanded graph.
    
    Format: (location, time, type, kit_type)
    - location: airport code (e.g., "HUB1", "A1")
    - time: hour in simulation (0 to MAX_HOURS)
    - type: NodeType enum
    - kit_type: class type ("FIRST", "BUSINESS", "PREMIUM_ECONOMY", "ECONOMY")
    """
    location: str
    time: int
    node_type: NodeType
    kit_type: str
    
    def __str__(self):
        if self.node_type in [NodeType.SOURCE, NodeType.SINK]:
            return f"{self.node_type.value}"
        return f"({self.location},{self.time},{self.node_type.value},{self.kit_type})"


@dataclass
class Edge:
    """
    Represents a directed edge in the flow network.
    
    Attributes:
        source: source node
        target: target node
        capacity: maximum flow allowed (upper bound)
        cost: cost per unit of flow
        lower_bound: minimum flow required (default 0)
        metadata: optional dict for tracking edge purpose
    """
    source: Node
    target: Node
    capacity: float
    cost: float
    lower_bound: float = 0.0
    metadata: Dict = field(default_factory=dict)
    
    def __str__(self):
        return f"{self.source} -> {self.target} [cap={self.capacity}, cost={self.cost}]"


class TimeExpandedGraph:
    """
    Time-expanded directed graph for rotables flow optimization.
    
    This graph models:
    - Initial inventory at each airport
    - Kit movements on flights
    - Kit processing (freeze) periods
    - Storage over time
    - Demand satisfaction (flight requirements)
    - Penalties for unmet demand
    """
    
    def __init__(self, max_time_hours: int):
        self.max_time = max_time_hours
        self.edges: List[Edge] = []
        self.nodes: Set[Node] = set()
        
        # Special nodes
        self.source = Node("", 0, NodeType.SOURCE, "")
        self.sink = Node("", max_time_hours, NodeType.SINK, "")
        self.nodes.add(self.source)
        self.nodes.add(self.sink)
        
        # Index for fast lookup
        self.edges_from: Dict[Node, List[Edge]] = {}
        self.edges_to: Dict[Node, List[Edge]] = {}
    
    def add_node(self, location: str, time: int, node_type: NodeType, kit_type: str) -> Node:
        """Create and register a node in the graph"""
        node = Node(location, time, node_type, kit_type)
        self.nodes.add(node)
        return node
    
    def add_edge(self, source: Node, target: Node, capacity: float, cost: float, 
                 lower_bound: float = 0.0, metadata: Optional[Dict] = None) -> Edge:
        """Add a directed edge to the graph"""
        edge = Edge(source, target, capacity, cost, lower_bound, metadata or {})
        self.edges.append(edge)
        
        # Update indices
        if source not in self.edges_from:
            self.edges_from[source] = []
        self.edges_from[source].append(edge)
        
        if target not in self.edges_to:
            self.edges_to[target] = []
        self.edges_to[target].append(edge)
        
        return edge
    
    # ==================== Edge Creation Methods ====================
    
    def add_initial_inventory_edge(self, airport: str, kit_type: str, 
                                   initial_stock: int) -> Edge:
        """
        Create edge from source to initial available stock.
        
        source -> (airport, t=0, available, kit_type)
        """
        if initial_stock <= 0:
            return None
            
        target = self.add_node(airport, 0, NodeType.AVAILABLE, kit_type)
        return self.add_edge(
            self.source, 
            target,
            capacity=initial_stock,
            cost=0.0,
            metadata={"type": "initial_inventory", "airport": airport, "kit": kit_type}
        )
    
    def add_flight_edge(self, flight_id: str, source_airport: str, dest_airport: str,
                       departure_time: int, arrival_time: int, kit_type: str,
                       flight_capacity: float, transport_cost: float) -> Edge:
        """
        Create edge representing kit movement on a flight.
        
        (source_airport, departure_time, available, kit_type) 
            -> (dest_airport, arrival_time, frozen, kit_type)
        """
        source_node = self.add_node(source_airport, departure_time, NodeType.AVAILABLE, kit_type)
        target_node = self.add_node(dest_airport, arrival_time, NodeType.FROZEN, kit_type)
        
        return self.add_edge(
            source_node,
            target_node,
            capacity=flight_capacity,
            cost=transport_cost,
            metadata={
                "type": "flight",
                "flight_id": flight_id,
                "source": source_airport,
                "dest": dest_airport,
                "kit": kit_type
            }
        )
    
    def add_processing_edge(self, airport: str, arrival_time: int, 
                           processing_time_hours: int, kit_type: str) -> Edge:
        """
        Create edge representing kit processing (freeze period).
        
        (airport, arrival_time, frozen, kit_type)
            -> (airport, arrival_time + processing_time, available, kit_type)
        """
        available_time = arrival_time + processing_time_hours
        if available_time > self.max_time:
            # Kit won't be available before end of simulation
            return None
            
        source_node = self.add_node(airport, arrival_time, NodeType.FROZEN, kit_type)
        target_node = self.add_node(airport, available_time, NodeType.AVAILABLE, kit_type)
        
        return self.add_edge(
            source_node,
            target_node,
            capacity=float('inf'),
            cost=0.0,  # Processing cost is paid at arrival via flight edge
            metadata={"type": "processing", "airport": airport, "kit": kit_type}
        )
    
    def add_storage_edge(self, airport: str, time: int, kit_type: str,
                        storage_capacity: float, storage_cost: float = 0.0) -> Edge:
        """
        Create edge representing kits stored at airport over one time unit.
        
        (airport, time, available, kit_type)
            -> (airport, time+1, available, kit_type)
        """
        if time + 1 > self.max_time:
            return None
            
        source_node = self.add_node(airport, time, NodeType.AVAILABLE, kit_type)
        target_node = self.add_node(airport, time + 1, NodeType.AVAILABLE, kit_type)
        
        return self.add_edge(
            source_node,
            target_node,
            capacity=storage_capacity,
            cost=storage_cost,
            metadata={"type": "storage", "airport": airport, "kit": kit_type}
        )
    
    def add_demand_edge(self, flight_id: str, airport: str, departure_time: int,
                       kit_type: str, required_kits: int, penalty_cost: float) -> Edge:
        """
        Create edge representing flight demand satisfaction.
        
        (airport, departure_time, available, kit_type) -> sink
        
        Cost is negative penalty to encourage satisfaction.
        """
        source_node = self.add_node(airport, departure_time, NodeType.AVAILABLE, kit_type)
        
        return self.add_edge(
            source_node,
            self.sink,
            capacity=required_kits,
            cost=-penalty_cost,  # Negative to encourage flow
            metadata={
                "type": "demand",
                "flight_id": flight_id,
                "airport": airport,
                "kit": kit_type,
                "required": required_kits
            }
        )
    
    def add_purchase_edge(self, kit_type: str, purchase_time: int, 
                         delivery_time: int, quantity: int, 
                         purchase_cost: float) -> Edge:
        """
        Create edge representing kit purchase at HUB with delivery delay.
        
        source -> (HUB1, delivery_time, available, kit_type)
        """
        target_node = self.add_node("HUB1", delivery_time, NodeType.AVAILABLE, kit_type)
        
        return self.add_edge(
            self.source,
            target_node,
            capacity=quantity,
            cost=purchase_cost,
            metadata={
                "type": "purchase",
                "kit": kit_type,
                "order_time": purchase_time,
                "delivery_time": delivery_time
            }
        )
    
    def add_discard_edge(self, airport: str, time: int, kit_type: str,
                        discard_cost: float = 0.1) -> Edge:
        """
        Create edge for discarding excess kits (overflow).
        
        (airport, time, available, kit_type) -> sink
        """
        source_node = self.add_node(airport, time, NodeType.AVAILABLE, kit_type)
        
        return self.add_edge(
            source_node,
            self.sink,
            capacity=float('inf'),
            cost=discard_cost,
            metadata={"type": "discard", "airport": airport, "kit": kit_type}
        )
    
    # ==================== Graph Query Methods ====================
    
    def get_outgoing_edges(self, node: Node) -> List[Edge]:
        """Get all edges leaving a node"""
        return self.edges_from.get(node, [])
    
    def get_incoming_edges(self, node: Node) -> List[Edge]:
        """Get all edges entering a node"""
        return self.edges_to.get(node, [])
    
    def get_flight_edges(self) -> List[Edge]:
        """Get all edges representing flights"""
        return [e for e in self.edges if e.metadata.get("type") == "flight"]
    
    def get_demand_edges(self) -> List[Edge]:
        """Get all edges representing flight demands"""
        return [e for e in self.edges if e.metadata.get("type") == "demand"]
    
    def to_dict(self) -> Dict:
        """Export graph structure for debugging/visualization"""
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "max_time": self.max_time,
            "edge_details": [
                {
                    "from": str(e.source),
                    "to": str(e.target),
                    "capacity": e.capacity,
                    "cost": e.cost,
                    "metadata": e.metadata
                }
                for e in self.edges
            ]
        }
    
    def __str__(self):
        return f"TimeExpandedGraph(nodes={len(self.nodes)}, edges={len(self.edges)}, time_horizon={self.max_time})"
