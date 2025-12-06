"""
Time-Expanded Network Graph for Kit Optimization
"""

class Edge:
    """Represents an edge in the time-expanded network"""
    def __init__(self, source, target, capacity, cost, edge_type, metadata=None):
        self.source = source
        self.target = target
        self.capacity = capacity
        self.cost = cost
        self.edge_type = edge_type
        self.metadata = metadata or {}
    
    def __repr__(self):
        return f"Edge({self.source} -> {self.target}, cap={self.capacity}, cost={self.cost}, type={self.edge_type})"


class Node:
    """Represents a node in the time-expanded network"""
    def __init__(self, node_id, node_type, airport=None, time=None, kit_type=None):
        self.node_id = node_id
        self.node_type = node_type  # 'source', 'sink', 'airport', 'flight', 'processing'
        self.airport = airport
        self.time = time
        self.kit_type = kit_type
    
    def __repr__(self):
        return f"Node({self.node_id}, type={self.node_type}, airport={self.airport}, time={self.time}, kit={self.kit_type})"
    
    def __hash__(self):
        return hash(self.node_id)
    
    def __eq__(self, other):
        return self.node_id == other.node_id


class TimeExpandedGraph:
    """
    Time-Expanded Network for Kit Flow Optimization
    
    Nodes represent (airport, time, kit_type) states
    Edges represent kit movements:
    - Storage edges: kits staying at an airport
    - Flight edges: kits moving on a flight
    - Processing edges: kits being processed after arrival
    - Purchase edges: new kits arriving at hub
    - Demand edges: passenger requirements (with penalty if not met)
    """
    
    def __init__(self, planning_horizon):
        self.planning_horizon = planning_horizon
        self.nodes = {}
        self.edges = []
        self.source_node = None
        self.sink_node = None
        self.node_counter = 0
        
    def _get_or_create_node(self, airport, time, kit_type, node_type='airport'):
        """Get existing node or create new one"""
        node_id = f"{airport}_{time}_{kit_type}"
        
        if node_id not in self.nodes:
            self.nodes[node_id] = Node(
                node_id=node_id,
                node_type=node_type,
                airport=airport,
                time=time,
                kit_type=kit_type
            )
        
        return self.nodes[node_id]
    
    def _create_special_node(self, node_type):
        """Create source or sink node"""
        node_id = f"{node_type}_{self.node_counter}"
        self.node_counter += 1
        node = Node(node_id=node_id, node_type=node_type)
        self.nodes[node_id] = node
        return node
    
    def get_source(self):
        """Get or create source node"""
        if self.source_node is None:
            self.source_node = self._create_special_node('source')
        return self.source_node
    
    def get_sink(self):
        """Get or create sink node"""
        if self.sink_node is None:
            self.sink_node = self._create_special_node('sink')
        return self.sink_node
    
    def add_initial_inventory_edge(self, airport, kit_type, quantity):
        """
        Add edge from source to (airport, 0, kit_type) for initial inventory
        """
        source = self.get_source()
        target = self._get_or_create_node(airport, 0, kit_type)
        
        edge = Edge(
            source=source.node_id,
            target=target.node_id,
            capacity=quantity,
            cost=0,
            edge_type='initial_inventory',
            metadata={'airport': airport, 'kit': kit_type, 'quantity': quantity}
        )
        self.edges.append(edge)
        return edge
    
    def add_storage_edge(self, airport, time, kit_type, capacity, storage_cost=0):
        """
        Add edge from (airport, t, kit) to (airport, t+1, kit) for kits staying at airport
        """
        if time >= self.planning_horizon - 1:
            return None
        
        source = self._get_or_create_node(airport, time, kit_type)
        target = self._get_or_create_node(airport, time + 1, kit_type)
        
        edge = Edge(
            source=source.node_id,
            target=target.node_id,
            capacity=capacity,
            cost=storage_cost,
            edge_type='storage',
            metadata={'airport': airport, 'time': time, 'kit': kit_type}
        )
        self.edges.append(edge)
        return edge
    
    def add_flight_edge(self, flight_id, source_airport, dest_airport, 
                       dep_time, arr_time, kit_type, capacity, cost):
        """
        Add edge from (source, dep_time, kit) to (dest, arr_time, kit) for flight
        """
        if dep_time >= self.planning_horizon or arr_time >= self.planning_horizon:
            return None
        
        source = self._get_or_create_node(source_airport, dep_time, kit_type)
        target = self._get_or_create_node(dest_airport, arr_time, kit_type)
        
        edge = Edge(
            source=source.node_id,
            target=target.node_id,
            capacity=capacity,
            cost=cost,
            edge_type='flight',
            metadata={
                'flight_id': flight_id,
                'source_airport': source_airport,
                'dest_airport': dest_airport,
                'dep_time': dep_time,
                'arr_time': arr_time,
                'kit': kit_type
            }
        )
        self.edges.append(edge)
        return edge
    
    def add_processing_edge(self, airport, arrival_time, processing_time, kit_type):
        """
        Add edge representing kit processing after flight arrival
        From (airport, arrival_time, kit) to (airport, arrival_time + processing_time, kit)
        """
        ready_time = arrival_time + processing_time
        if ready_time >= self.planning_horizon:
            return None
        
        source = self._get_or_create_node(airport, arrival_time, kit_type)
        target = self._get_or_create_node(airport, ready_time, kit_type)
        
        edge = Edge(
            source=source.node_id,
            target=target.node_id,
            capacity=float('inf'),  # No capacity limit on processing
            cost=0,  # Processing cost already included in flight edge
            edge_type='processing',
            metadata={
                'airport': airport,
                'arrival_time': arrival_time,
                'ready_time': ready_time,
                'kit': kit_type
            }
        )
        self.edges.append(edge)
        return edge
    
    def add_demand_edge(self, flight_id, airport, dep_time, kit_type, 
                       required_quantity, penalty_cost):
        """
        Add edge from (airport, dep_time, kit) to sink representing passenger demand
        If demand not met, flow on this edge incurs penalty
        """
        source = self._get_or_create_node(airport, dep_time, kit_type)
        sink = self.get_sink()
        
        edge = Edge(
            source=source.node_id,
            target=sink.node_id,
            capacity=required_quantity,
            cost=penalty_cost,
            edge_type='demand',
            metadata={
                'flight_id': flight_id,
                'airport': airport,
                'time': dep_time,
                'kit': kit_type,
                'required': required_quantity
            }
        )
        self.edges.append(edge)
        return edge
    
    def add_purchase_edge(self, kit_type, order_time, delivery_time, 
                         quantity, cost):
        """
        Add edge representing purchasing new kits at HUB
        From source to (HUB1, delivery_time, kit)
        """
        if delivery_time >= self.planning_horizon:
            return None
        
        source = self.get_source()
        target = self._get_or_create_node('HUB1', delivery_time, kit_type)
        
        edge = Edge(
            source=source.node_id,
            target=target.node_id,
            capacity=quantity,
            cost=cost,
            edge_type='purchase',
            metadata={
                'kit': kit_type,
                'order_time': order_time,
                'delivery_time': delivery_time
            }
        )
        self.edges.append(edge)
        return edge
    
    def get_stats(self):
        """Return statistics about the graph"""
        return {
            'nodes': len(self.nodes),
            'edges': len(self.edges),
            'edge_types': {
                'initial_inventory': sum(1 for e in self.edges if e.edge_type == 'initial_inventory'),
                'storage': sum(1 for e in self.edges if e.edge_type == 'storage'),
                'flight': sum(1 for e in self.edges if e.edge_type == 'flight'),
                'processing': sum(1 for e in self.edges if e.edge_type == 'processing'),
                'demand': sum(1 for e in self.edges if e.edge_type == 'demand'),
                'purchase': sum(1 for e in self.edges if e.edge_type == 'purchase')
            }
        }
