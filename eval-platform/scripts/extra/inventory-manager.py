import numpy as np

class InventoryManager:
    def __init__(self):
        self.forecast = {}  # Demand forecasts
        self.safety_stock = {}  # Safety stock levels
        
    def calculate_safety_stock(self, airport, kit_type):
        """
        Calculate safety stock based on demand variability
        """
        demand_history = self.get_demand_history(airport, kit_type)
        lead_time = self.get_purchasing_lead_time(kit_type)
        
        # Simple safety stock calculation
        avg_demand = np.mean(demand_history)
        std_demand = np.std(demand_history)
        
        # Z-score for 95% service level
        z_score = 1.645
        
        safety_stock = z_score * std_demand * np.sqrt(lead_time)
        
        return max(0, int(safety_stock))
    
    def reorder_point_decision(self, current_hour):
        """
        Make purchasing decisions based on reorder point
        """
        purchases = {}
        
        for kit in self.kit_types:
            current_stock = self.stocks[('HUB1', kit)]
            safety_stock = self.calculate_safety_stock('HUB1', kit)
            lead_time = self.get_purchasing_lead_time(kit)
            
            # Forecast demand during lead time
            forecast_demand = self.forecast_demand('HUB1', kit, 
                                                  current_hour, 
                                                  current_hour + lead_time)
            
            reorder_point = forecast_demand + safety_stock
            
            if current_stock <= reorder_point:
                # Order up to target level
                target_level = safety_stock * 2  # Simple heuristic
                order_qty = max(0, target_level - current_stock)
                
                # Consider budget constraints
                budget_available = self.get_remaining_budget()
                max_affordable = budget_available // self.get_kit_cost(kit)
                
                order_qty = min(order_qty, max_affordable)
                
                if order_qty > 0:
                    purchases[kit] = order_qty
        
        return purchases