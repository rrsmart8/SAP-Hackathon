import os
import csv
from player.models import AircraftType, Airport, FlightSchedule, FlightInstance

class CsvService:
    DATA_FOLDER = "../src/main/resources/liquibase/data/"

    def load_aircraft_types(self):
        aircraft_map = {}
        file_path = os.path.join(self.DATA_FOLDER, "aircraft_types.csv")
        if not os.path.exists(file_path): return {}

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    type_code = row['type_code'].strip()
                    try:
                        aircraft_map[type_code] = AircraftType(
                            type_code,
                            int(row['first_class_seats']),    # Atentie: seats vs kits capacity? De obicei e kits capacity
                            int(row['business_seats']),       # Verifica daca folosesti seats sau capacity
                            int(row['premium_economy_seats']),
                            int(row['economy_seats']) 
                            # NOTA: Daca vrei capacity, schimba cheile cu 'economy_kits_capacity' etc.
                            # Verificand scriptul anterior, foloseam indexii 7,8,9,10 care erau Capacities.
                            # Corectie mai jos pentru siguranta:
                        )
                        # Re-scriere pentru Capacitati (Correct mapping based on previous logs)
                        aircraft_map[type_code] = AircraftType(
                            type_code,
                            int(row['first_class_kits_capacity']),
                            int(row['business_kits_capacity']),
                            int(row['premium_economy_kits_capacity']),
                            int(row['economy_kits_capacity'])
                        )
                    except ValueError: pass
            print(f"   -> [CSV] Loaded {len(aircraft_map)} aircraft types.")
            return aircraft_map
        except Exception as e:
            print(f"Error reading Aircraft CSV: {e}")
            return {}

    def load_airports(self):
        """Loads FULL airport data (all classes)."""
        airport_map = {}
        file_path = os.path.join(self.DATA_FOLDER, "airports_with_stocks.csv")
        if not os.path.exists(file_path): return {}

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    code = row['code'].strip()
                    try:
                        airport_map[code] = Airport(
                            code,
                            # Stocks
                            int(row['initial_fc_stock']),
                            int(row['initial_bc_stock']),
                            int(row['initial_pe_stock']),
                            int(row['initial_ec_stock']),
                            # Capacities
                            int(row['capacity_fc']),
                            int(row['capacity_bc']),
                            int(row['capacity_pe']),
                            int(row['capacity_ec']),
                            # Processing Times
                            int(row['first_processing_time']),
                            int(row['business_processing_time']),
                            int(row['premium_economy_processing_time']),
                            int(row['economy_processing_time'])
                        )
                    except ValueError: pass
            print(f"   -> [CSV] Loaded {len(airport_map)} airports.")
            return airport_map
        except Exception as e:
            print(f"Error reading Airport CSV: {e}")
            return {}

    def load_flight_schedule(self):
        """Loads static flight plan."""
        schedule_list = []
        file_path = os.path.join(self.DATA_FOLDER, "flight_plan.csv")
        if not os.path.exists(file_path): return []

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    try:
                        schedule_list.append(FlightSchedule(
                            row['depart_code'].strip(),
                            row['arrival_code'].strip(),
                            int(row['scheduled_hour']),
                            int(row['distance_km'])
                        ))
                    except ValueError: pass
            print(f"   -> [CSV] Loaded {len(schedule_list)} schedule routes.")
            return schedule_list
        except Exception as e:
            print(f"Error reading Flight Plan CSV: {e}")
            return []

    def load_all_flights(self):
        """Loads the massive flights.csv file."""
        flights_list = []
        file_path = os.path.join(self.DATA_FOLDER, "flights.csv")
        if not os.path.exists(file_path): 
            print("Warning: flights.csv not found.")
            return []

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    try:
                        flights_list.append(FlightInstance(
                            row['id'],
                            row['flight_number'],
                            row['origin_airport_id'], # Atentie: Aici e ID, in airports e CODE. Trebuie mapate.
                            row['destination_airport_id'],
                            int(row['scheduled_depart_day']),
                            int(row['scheduled_depart_hour']),
                            int(row['scheduled_arrival_day']),
                            int(row['scheduled_arrival_hour'])
                        ))
                    except ValueError: pass
            print(f"   -> [CSV] Loaded {len(flights_list)} historical flights.")
            return flights_list
        except Exception as e:
            print(f"Error reading Flights CSV: {e}")
            return []
