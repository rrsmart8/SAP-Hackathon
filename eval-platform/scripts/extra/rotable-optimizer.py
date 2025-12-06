import networkx as nx


class RotableOptimizer:
    def __init__(self):
        # Current state
        self.stocks = {}  # {(airport, kit_type): quantity}
        self.in_process = {}  # {(airport, kit_type, arrival_time): quantity}
        self.purchasing_orders = []  # {(kit_type, quantity, delivery_time)}
        
        # Flight information
        self.flights = {}  # {flight_id: Flight object}
        
        # Configuration
        self.kit_types = ['FIRST', 'BUSINESS', 'PREMIUM_ECONOMY', 'ECONOMY']
        self.airports = []
        self.aircraft_types = {}
        
        # Planning horizon
        self.horizon = 168  # 7 days in hours
        
        # Decisions
        self.loading_decisions = {}  # {(flight_id, kit_type): quantity}
        self.purchasing_decisions = []  # Purchases for next hour}
    
    def decide_for_hour(self, current_hour, flight_updates):
        """
        Main decision function called each hour
        """
        # Step 1: Update state with new information
        self.process_flight_updates(flight_updates)
        
        # Step 2: Process arrivals and available kits
        self.update_available_stocks(current_hour)
        
        # Step 3: Build time-expanded planning model
        planning_model = self.build_planning_model(current_hour)
        
        # Step 4: Solve optimization for next 24-48 hours
        decisions = self.solve_optimization(planning_model, current_hour)
        
        # Step 5: Return decisions for current hour
        return {
            'flight_loads': decisions['immediate_loads'],
            'purchases': decisions['purchases']
        }
    
    def build_planning_model(self, current_hour):
        """
        Build min-cost flow model for horizon
        """
        G = nx.DiGraph()
        
        # Add source and sink
        G.add_node('source', demand=-total_demand)
        G.add_node('sink', demand=total_demand)
        
        # For each airport, kit type, and time slot
        for airport in self.airports:
            for kit in self.kit_types:
                for t in range(current_hour, current_hour + self.horizon):
                    # Available node
                    avail_node = f"{airport}_{kit}_{t}_avail"
                    G.add_node(avail_node)
                    
                    # Frozen/processing node
                    if t > 0:
                        proc_node = f"{airport}_{kit}_{t}_proc"
                        G.add_node(proc_node)
                        
                        # Processing edge (kits take time to become available)
                        processing_time = self.get_processing_time(airport, kit)
                        if t - processing_time >= current_hour:
                            from_node = f"{airport}_{kit}_{t-processing_time}_proc"
                            G.add_edge(from_node, avail_node, 
                                    capacity=float('inf'), 
                                    cost=0)
                    
                    # Storage edge (kits stay available)
                    if t < current_hour + self.horizon - 1:
                        G.add_edge(avail_node, f"{airport}_{kit}_{t+1}_avail",
                                capacity=self.get_storage_capacity(airport, kit),
                                cost=self.get_storage_cost(airport, kit))
        
        # Add flight edges
        for flight in self.get_flights_in_horizon(current_hour):
            if flight.departure_time >= current_hour:
                # For each kit type
                for kit in self.kit_types:
                    # Edge: kits loaded at source become processing at destination
                    src_node = f"{flight.source}_{kit}_{flight.departure_time}_avail"
                    dest_node = f"{flight.destination}_{kit}_{flight.arrival_time}_proc"
                    
                    # Flight capacity constraint
                    capacity = self.get_aircraft_capacity(flight.aircraft_type, kit)
                    cost = self.calculate_flight_cost(flight, kit)
                    
                    G.add_edge(src_node, dest_node, 
                            capacity=capacity, 
                            cost=cost)
        
        # Add purchasing edges (only at HUB1)
        for kit in self.kit_types:
            lead_time = self.get_purchasing_lead_time(kit)
            for t in range(current_hour, current_hour + self.horizon):
                if t + lead_time <= current_hour + self.horizon:
                    G.add_edge('source', f"HUB1_{kit}_{t+lead_time}_avail",
                            capacity=float('inf'),
                            cost=self.get_kit_cost(kit))
        
        # Add demand edges (passenger requirements)
        for flight in self.get_flights_in_horizon(current_hour):
            for kit in self.kit_types:
                passengers = flight.passengers_by_class[kit]
                node = f"{flight.destination}_{kit}_{flight.arrival_time}_avail"
                G.add_edge(node, 'sink',
                        capacity=passengers,
                        cost=-self.get_penalty_cost(kit, flight))
        
        return G
    
    def greedy_loading_decision(self, flight, available_kits):
        """
        Simple greedy algorithm for loading decisions
        Returns: {kit_type: quantity_to_load}
        """
        loads = {}
        
        # Sort kit types by penalty factor (highest first)
        kit_priority = sorted(self.kit_types, 
                            key=lambda k: self.get_penalty_factor(k), 
                            reverse=True)
        
        for kit in kit_priority:
            # Get requirements
            required = flight.passengers_by_class[kit]
            capacity = self.get_aircraft_capacity(flight.aircraft_type, kit)
            
            # How many can we load?
            can_load = min(
                required,
                capacity,
                available_kits[flight.source][kit],
                self.calculate_available_space(flight, loads)
            )
            
            loads[kit] = can_load
        
        return loads

    def adaptive_greedy(self, flights, current_hour):
        """
        Adaptive greedy that looks ahead
        """
        decisions = {}
        
        # Group flights by departure time
        flights_by_hour = self.group_flights_by_departure(flights)
        
        # Process flights in chronological order
        for hour in sorted(flights_by_hour.keys()):
            hour_flights = flights_by_hour[hour]
            
            # Sort flights by penalty potential
            hour_flights.sort(key=lambda f: self.flight_priority_score(f), 
                            reverse=True)
            
            # Allocate kits
            for flight in hour_flights:
                if hour == current_hour:
                    # Immediate decision
                    loads = self.greedy_loading_decision(
                        flight, 
                        self.get_current_stocks()
                    )
                    decisions[flight.id] = loads
                    
                    # Update available stocks (reserve them)
                    self.reserve_kits(flight.source, loads)
                else:
                    # Future flight - plan but don't reserve
                    self.plan_future_allocation(flight, hour)
        
        return decisions
    def hybrid_optimization(self, current_hour):
        """
        Combine multiple techniques:
        1. Greedy for immediate decisions
        2. Linear programming for medium-term
        3. Heuristics for edge cases
        """
        # Phase 1: Handle immediate flights (next 1-2 hours)
        immediate_decisions = self.handle_immediate_flights(current_hour)
        
        # Phase 2: Plan for next 24 hours with optimization
        if self.has_sufficient_time(current_hour):
            opt_decisions = self.solve_mip_optimization(current_hour, horizon=24)
            
            # Merge decisions, giving priority to immediate needs
            merged = self.merge_decisions(immediate_decisions, opt_decisions)
        else:
            merged = immediate_decisions
        
        # Phase 3: Adjust for constraints
        final_decisions = self.apply_constraints(merged, current_hour)
        
        # Phase 4: Purchasing decisions
        purchases = self.make_purchasing_decisions(current_hour)
        
        return {
            'loads': final_decisions,
            'purchases': purchases
        }
    