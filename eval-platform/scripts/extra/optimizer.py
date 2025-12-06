class FlightRotablesOptimizer:
    def run_optimization_cycle(self, current_hour, flight_updates):
        """
        Complete optimization cycle for one hour
        """
        # 1. Update knowledge base
        self.update_knowledge_base(flight_updates)
        
        # 2. Process arrivals and inventory
        self.process_arrivals(current_hour)
        self.update_inventory_levels()
        
        # 3. Check constraints and thresholds
        alerts = self.check_constraints()
        
        # 4. Run optimization based on time available
        if self.optimization_time_available():
            # Use full optimization
            decisions = self.solve_comprehensive_optimization(current_hour)
        else:
            # Use fast heuristic
            decisions = self.fast_heuristic_solution(current_hour)
        
        # 5. Validate decisions
        validated = self.validate_decisions(decisions)
        
        # 6. Format output for API
        api_output = self.format_for_api(validated)
        
        return api_output
    
    def solve_comprehensive_optimization(self, current_hour):
        """
        Comprehensive optimization using multiple techniques
        """
        # Step 1: Create simplified network
        network = self.build_simplified_network(current_hour, horizon=48)
        
        # Step 2: Solve as min-cost flow
        flow_solution = self.solve_min_cost_flow(network)
        
        # Step 3: Extract base plan
        base_plan = self.extract_plan_from_flow(flow_solution)
        
        # Step 4: Refine with local search
        refined = self.local_search_refinement(base_plan, iterations=100)
        
        # Step 5: Add robustness
        robust = self.add_robustness(refined)
        
        return robust