import sys
import json
import traceback

# Add current directory to path so imports work correctly
sys.path.append(".")

from player.services.csv_service import CsvService
from player.services.api_service import ApiService
from player.services.log_service import LogService
from player.services.strategy_service import StrategyService
from player.models import RoundRequest

def main():
    # 1. Initialize Loggers
    # main_logger: For readable game flow (Day/Hour/Cost)
    main_logger = LogService("bot_history.log")
    # json_logger: Specifically for dumping the huge JSON responses from the server
    json_logger = LogService("server_responses.json")
    
    csv_service = CsvService()
    api_service = ApiService()

    main_logger.info(">>> 1. Loading Data...")
    aircraft_map = csv_service.load_aircraft_types()
    
    # Initialize Strategy with the main logger (so we see "[ORDERING]" in the history log)
    strategy = StrategyService(aircraft_map, main_logger)

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

            # ------------------

            # E. Analyze Events (Planning for the next round)
            # This is where your strategy looks at 'CHECKED_IN' flights
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
        # Print full trace to console to help debug crashes
        traceback.print_exc()

if __name__ == "__main__":
    main()