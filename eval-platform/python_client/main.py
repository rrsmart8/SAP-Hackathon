import sys
import json
import traceback
import os

# Add current directory to path so imports work correctly
sys.path.append(".")
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "scripts"))

from player.services.csv_service import CsvService
from player.services.api_service import ApiService
from player.services.log_service import LogService
from player.services.strategy_service import StrategyService
from player.services.network_flow_strategy import NetworkFlowStrategy
from player.models import RoundRequest

# Configuration: Choose strategy
USE_NETWORK_FLOW = True  # Set to False to use old simple strategy

def main():

    main_logger = LogService("bot_history.log")
    json_logger = LogService("server_responses.json")
    
    csv_service = CsvService()
    api_service = ApiService()

    main_logger.info(">>> 1. Loading Data...")
    aircraft_map = csv_service.load_aircraft_types()
    airport_map = csv_service.load_airports()
    all_flights = csv_service.load_all_flights()

    if not aircraft_map:
        main_logger.info("!!! FATAL: No aircraft types loaded! Exiting.")
        return
    
    # Choose strategy
    if USE_NETWORK_FLOW:
        main_logger.info(">>> Using Network Flow Strategy (Time-Expanded Network)")
        strategy = NetworkFlowStrategy(aircraft_map, airport_map, all_flights, main_logger)
    else:
        main_logger.info(">>> Using Simple Strategy")
        strategy = StrategyService(aircraft_map, main_logger)

    # # Strategy loads all data maps
    # strategy = StrategyService(aircraft_map, airport_map, all_flights, main_logger)    

    try:
        main_logger.info(">>> 2. Start Session...")
        api_service.start_session()
        main_logger.info(f">>> Session ID: {api_service.get_session_id()}")

        main_logger.info(">>> 3. Start Game...")
        current_day = 0
        current_hour = 0
        game_running = True

        while game_running:
            # A. Prepare Request for the current hour
            request = RoundRequest(current_day, current_hour)
            
            # Apply decisions made in the previous round (from pending_loads)
            strategy.apply_decisions(request)

            # B. Play Round
            # We expect a tuple: (RoundResponse object, Raw Dictionary)
            response_obj, raw_json = api_service.play_round(request)

            # C. Check Game Over (Session ended)
            if response_obj is None:
                main_logger.info(">>> 🏁 GAME FINISHED SUCCESSFULLY! (720 Hours)")
                break

            # --- D. LOGGING ---
            
            # 1. Log the Raw JSON to the separate file for debugging
            if raw_json:
                json_logger.log_raw(f"\n=== RESPONSE DAY {current_day} HOUR {current_hour} ===")
                json_logger.log_raw(json.dumps(raw_json, indent=4)) 

            # 2. Log the Summary to the main history file/console
            main_logger.info(f"--- Day {current_day} : Hour {current_hour} | Cost: {response_obj.total_cost:.2f} | Flights: {len(response_obj.flight_updates)}")

            # Print all response events summary
            if response_obj.penalties:
                main_logger.info(f"!!! WARNING: {len(response_obj.penalties)} Penalties received!")
                for p in response_obj.penalties:
                    main_logger.info(f"   -> {p}")
            # ------------------

            # E. Analyze Events (Planning for the next round)
            if USE_NETWORK_FLOW:
                # Network flow strategy analyzes and plans in one step
                strategy.analyze_and_plan(response_obj.flight_updates, current_day, current_hour)
            else:
                # Simple strategy
                strategy.analyze_events(response_obj.flight_updates)

            # F. Advance Time
            current_hour += 1
            if current_hour >= 24:
                current_hour = 0
                current_day += 1

        # End session cleanly
        api_service.end_session()

    except Exception as e:
        main_logger.info(f"!!! CRITICAL ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()